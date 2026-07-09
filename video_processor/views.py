import asyncio
import json
import logging
import mimetypes
import os
import re
import threading
import time
from datetime import datetime
from pathlib import Path

import yt_dlp
from django.conf import settings
from django.contrib import messages
from django.contrib.auth import authenticate, login
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.models import User
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from django.db.models import Q
from django.http import FileResponse, Http404, HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse_lazy
from django.utils import timezone
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.views.generic import ListView
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import OpenApiExample, OpenApiParameter, extend_schema

from core_video_processor import CoreVideoProcessor, VideoFileValidator

from .models import JobStatus, VideoJob, VideoSearchQuery
from .youtube_utils import (
    MAX_PLAYLIST_VIDEOS,
    build_ytdlp_opts,
    download_youtube_video,
    is_youtube_playlist_url,
    is_youtube_video_url,
)

_JOB_SEMAPHORE = threading.Semaphore(2)
from .search_helpers import (
    convert_enhanced_results_to_api_format,
    convert_keyword_results_to_api_format,
    convert_semantic_results_to_api_format,
    convert_semantic_results_to_display_format,
    ensure_search_engine_initialized,
    filter_api_results_by_user,
    get_video_segments_for_search,
    perform_keyword_search,
    rebuild_semantic_search_index,
    resolve_target_user,
    run_advanced_api_search,
    run_enhanced_api_search,
    run_legacy_api_search,
)

# from .tasks import process_youtube_playlist, process_single_video, is_youtube_playlist_url

# Configure logging first (before any imports that use logger)
logger = logging.getLogger(__name__)

# Import semantic search engine (the initialized instance)
try:
    from semantic_search import SemanticSearchEngine, search_engine

    logger.info("Semantic search engine imported successfully")
except ImportError as e:
    logger.warning(f"Semantic search engine not available: {e}")
    search_engine = None
    SemanticSearchEngine = None

# Phase 2: enhanced search (core path uses core_video_processor for transcription)
try:
    from enhanced_semantic_search import get_enhanced_search_engine

    enhanced_search = get_enhanced_search_engine()
    PHASE2_AI_AVAILABLE = True
    logger.info("Phase 2 enhanced search loaded successfully")

except ImportError as e:
    logger.warning(f"Phase 2 enhanced search not available: {e}")
    enhanced_search = None
    PHASE2_AI_AVAILABLE = False

# Initialize the video processor
video_processor = CoreVideoProcessor()

ALLOWED_UPLOAD_EXTENSIONS = VideoFileValidator.SUPPORTED_MEDIA_FORMATS

AUDIO_CONTENT_TYPES = {
    ".mp3": "audio/mpeg",
    ".wav": "audio/wav",
    ".m4a": "audio/mp4",
    ".aac": "audio/aac",
}


def get_media_content_type(file_path: str) -> str:
    """Return the HTTP content type for a media file path."""
    extension = Path(file_path).suffix.lower()
    if extension in AUDIO_CONTENT_TYPES:
        return AUDIO_CONTENT_TYPES[extension]
    guessed_type, _ = mimetypes.guess_type(file_path)
    return guessed_type or "video/mp4"


# Check if search engine is available (may be stale until index is loaded/rebuilt)
search_available = (
    search_engine is not None
    and hasattr(search_engine, "is_initialized")
    and search_engine.is_initialized
)


def is_search_engine_available() -> bool:
    """Return whether the semantic search index is ready for queries."""
    return bool(search_engine and ensure_search_engine_initialized(search_engine))


def create_error_response(error_code, message, details=None, status_code=400):
    """Create standardized error responses"""
    response = {
        "success": False,
        "error": {
            "code": error_code,
            "message": message,
            "timestamp": timezone.now().isoformat(),
        },
    }
    if details:
        response["error"]["details"] = details
    return JsonResponse(response, status=status_code)


def create_success_response(data, message="Operation completed successfully"):
    """Create standardized success responses"""
    return JsonResponse(
        {
            "success": True,
            "data": data,
            "message": message,
            "timestamp": timezone.now().isoformat(),
        }
    )


def start_video_job_thread(job_id):
    """Start background processing with bounded concurrency."""
    threading.Thread(target=process_video_job, args=(str(job_id),)).start()


def extract_playlist_videos(playlist_url):
    """Extract video URLs from a YouTube playlist."""
    try:
        ydl_opts = build_ytdlp_opts(
            extract_flat=True,
            extractor_args={"youtube": {"skip": ["dash", "hls"]}},
        )

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            logger.info(f"Extracting playlist: {playlist_url}")
            playlist_info = ydl.extract_info(playlist_url, download=False)

            if not playlist_info:
                logger.error("No playlist info returned")
                return [], None

            if "entries" not in playlist_info:
                logger.error("No entries found in playlist")
                return [], None

            video_urls = []
            for entry in playlist_info["entries"]:
                if entry and entry.get("id"):
                    # Use the video ID to construct the URL
                    video_url = f"https://www.youtube.com/watch?v={entry['id']}"
                    video_urls.append(video_url)
                elif entry and entry.get("url"):
                    # Fallback to URL if available
                    video_urls.append(entry["url"])

            playlist_title = playlist_info.get("title", "Unknown Playlist")
            logger.info(
                f"Extracted {len(video_urls)} videos from playlist: {playlist_title}"
            )
            return video_urls, playlist_title

    except Exception as e:
        logger.error(f"Error extracting playlist videos: {e}")
        import traceback

        logger.error(f"Traceback: {traceback.format_exc()}")

        # If network error, provide helpful fallback message
        if "Incomplete data received" in str(e) or "network" in str(e).lower():
            logger.error("Network connectivity issue detected. This may be due to:")
            logger.error("1. Container network restrictions")
            logger.error("2. YouTube rate limiting")
            logger.error("3. DNS resolution issues")
            logger.error(
                "Consider running the container with --dns 8.8.8.8 or checking network policies"
            )

        return [], None

    return [], None


# User Authentication Views
def register_view(request):
    if request.method == "POST":
        form = UserCreationForm(request.POST)
        if form.is_valid():
            form.save()
            username = form.cleaned_data.get("username")
            messages.success(request, f"Account created for {username}! Please log in.")
            return redirect("login")
    else:
        form = UserCreationForm()
    return render(request, "registration/register.html", {"form": form})


# Multi-tenant Video Library View
@method_decorator(login_required, name="dispatch")
class VideoLibraryView(LoginRequiredMixin, ListView):
    model = VideoJob
    template_name = "video_processor/library.html"
    context_object_name = "videos"
    login_url = reverse_lazy("login")

    def get_queryset(self):
        # Filter videos by current user
        return VideoJob.objects.filter(user=self.request.user)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Add user-specific statistics
        user_videos = self.get_queryset()

        # Calculate stats based on user's videos (not all videos)
        completed_videos = user_videos.filter(status=JobStatus.COMPLETED)
        total_videos = completed_videos.count()
        total_processing_time = sum(
            job.processing_time or 0 for job in completed_videos if job.processing_time
        )
        total_words = sum(
            job.word_count or 0 for job in completed_videos if job.word_count
        )
        pending_jobs = user_videos.filter(status=JobStatus.PENDING).count()

        context.update(
            {
                "video_count": user_videos.count(),
                "completed_count": user_videos.filter(status="completed").count(),
                "processing_count": user_videos.filter(status="processing").count(),
                "failed_count": user_videos.filter(status="failed").count(),
                # User-specific stats for dashboard
                "stats": {
                    "total_videos": total_videos,
                    "total_processing_time": total_processing_time,
                    "total_words": total_words,
                    "pending_jobs": pending_jobs,
                },
            }
        )
        return context


def home_view(request):
    """Marketing landing for guests; search hub for authenticated users."""
    if request.user.is_authenticated:
        return render(request, "video_processor/search_interface.html")
    return render(request, "video_processor/landing.html")


def search_interface_view(request):
    """Search hub interface."""
    return render(request, "video_processor/search_interface.html")


# Function removed - using the more comprehensive upload_video function below


def search_videos(request):
    """Enhanced search through video transcriptions with semantic capabilities."""
    if request.method != "POST":
        return redirect("video_library")

    query = request.POST.get("query", "").strip()
    search_mode = request.POST.get("search_mode", "hybrid")  # keyword, semantic, hybrid

    if not query:
        return redirect("video_library")

    # Track search query
    VideoSearchQuery.objects.create(query=query, results_count=0)

    # Perform search based on selected mode
    search_results = []
    search_user = request.user if request.user.is_authenticated else None
    engine_ready = is_search_engine_available()

    try:
        if search_mode == "keyword":
            search_results = perform_keyword_search(query, user=search_user)

        elif search_mode == "semantic" and engine_ready:
            semantic_results = search_engine.semantic_search(query, top_k=50)
            if semantic_results:
                search_results = convert_semantic_results_to_display_format(
                    semantic_results
                )
            else:
                search_results = perform_keyword_search(query, user=search_user)
                search_mode = "keyword_fallback"

        elif search_mode == "hybrid" and engine_ready:
            video_segments_data = get_video_segments_for_search()
            hybrid_results = search_engine.hybrid_search(
                query, video_segments_data, top_k=50
            )
            search_results = convert_semantic_results_to_display_format(hybrid_results)

        else:
            search_results = perform_keyword_search(query, user=search_user)
            if search_mode in {"semantic", "hybrid"}:
                search_mode = "keyword_fallback"

    except Exception as e:
        logger.error(f"Search error: {e}")
        search_results = perform_keyword_search(query, user=search_user)
        search_mode = "keyword_fallback"

    # Update search query results count
    VideoSearchQuery.objects.filter(query=query).update(
        results_count=len(search_results)
    )

    # Calculate statistics (same as library view)
    total_videos = VideoJob.objects.filter(status=JobStatus.COMPLETED).count()
    total_processing_time = sum(
        job.processing_time or 0
        for job in VideoJob.objects.filter(status=JobStatus.COMPLETED)
    )
    total_words = sum(
        job.word_count or 0
        for job in VideoJob.objects.filter(status=JobStatus.COMPLETED)
    )
    pending_jobs = VideoJob.objects.filter(status=JobStatus.PENDING).count()

    stats = {
        "total_videos": total_videos,
        "total_processing_time": total_processing_time,
        "total_words": total_words,
        "pending_jobs": pending_jobs,
    }

    # Check search engine status for template
    search_available = is_search_engine_available()
    try:
        if search_engine and not search_available:
            search_engine._load_index()
            search_available = is_search_engine_available()
    except Exception as e:
        logger.warning(f"Could not check search engine status: {e}")

    return render(
        request,
        "video_processor/library.html",
        {
            "videos": VideoJob.objects.filter(status=JobStatus.COMPLETED).order_by(
                "-created_at"
            ),
            "search_results": search_results,
            "query": query,
            "search_mode": search_mode,
            "semantic_available": search_available,
            "stats": stats,
        },
    )


@login_required
def upload_video(request):
    """Handle video upload and processing (files, YouTube URLs, or YouTube playlists)."""
    if request.method == "GET":
        return render(
            request,
            "video_processor/upload.html",
            {
                "recent_videos": VideoJob.objects.filter(user=request.user).order_by(
                    "-created_at"
                )[:10],
            },
        )

    if request.method != "POST":
        return redirect("video_library")

    # Check if it's a YouTube URL submission
    youtube_url = request.POST.get("youtube_url", "").strip()
    playlist_url = request.POST.get("playlist_url", "").strip()

    if youtube_url:
        # Check if it's a playlist URL
        if is_youtube_playlist_url(youtube_url):
            return handle_youtube_playlist_simple(request, youtube_url)
        else:
            return handle_youtube_upload(request, youtube_url)

    if playlist_url:
        return handle_youtube_playlist_simple(request, playlist_url)

    # Handle file upload (existing code)
    if "video" not in request.FILES:
        messages.error(request, "No media file provided")
        return redirect("video_library")

    video_file = request.FILES["video"]
    if not video_file.name:
        messages.error(request, "Invalid media file")
        return redirect("video_library")

    file_extension = Path(video_file.name).suffix.lower()
    if file_extension not in ALLOWED_UPLOAD_EXTENSIONS:
        supported = ", ".join(sorted(ALLOWED_UPLOAD_EXTENSIONS))
        messages.error(
            request,
            f"Unsupported file type '{file_extension}'. Supported formats: {supported}",
        )
        return redirect("video_library")

    try:
        # Save video file to media directory
        media_videos_dir = Path(settings.MEDIA_ROOT) / "videos"
        media_videos_dir.mkdir(parents=True, exist_ok=True)

        # Create unique filename to avoid conflicts
        import uuid

        unique_id = uuid.uuid4()
        safe_filename = f"{unique_id}_{video_file.name}"
        file_path = media_videos_dir / safe_filename

        # Save the file
        with open(file_path, "wb+") as destination:
            for chunk in video_file.chunks():
                destination.write(chunk)

        # Create video job
        job = VideoJob.objects.create(
            job_id=unique_id,  # Use the same UUID for consistency
            user=request.user,
            video_path=str(file_path),
            video_name=video_file.name,
            file_size_bytes=video_file.size,
            status=JobStatus.PENDING,
        )

        # Process video in background
        start_video_job_thread(job.job_id)

        messages.success(
            request, f'"{video_file.name}" uploaded and queued for processing'
        )

    except Exception as e:
        logger.error(f"Error uploading media file: {e}")
        messages.error(request, f"Error uploading file: {e}")

    return redirect("video_library")


def handle_youtube_upload(request, youtube_url):
    """Handle single YouTube URL submission."""
    if not is_youtube_video_url(youtube_url):
        messages.error(request, "Invalid YouTube video URL.")
        return redirect("video_library")

    try:
        # Create video job for YouTube URL
        job = VideoJob.objects.create(
            user=request.user,
            video_path="",
            video_name="YouTube Video (downloading...)",
            youtube_url=youtube_url,
            status=JobStatus.PENDING,
        )

        # Process video in background
        start_video_job_thread(job.job_id)

        messages.success(
            request,
            f"YouTube video queued for download and processing.",
        )
        messages.info(
            request,
            "Video will appear in your library as it is processed. This may take several minutes.",
        )

    except Exception as e:
        logger.error(f"Error processing YouTube video: {e}")
        messages.error(request, f"Error processing YouTube video: {e}")

    return redirect("video_library")


def handle_youtube_playlist_simple(request, playlist_url):
    """Handle YouTube playlist URL submission with simple approach."""
    try:
        # Validate playlist URL
        if not is_youtube_playlist_url(playlist_url):
            messages.error(
                request,
                "Invalid YouTube playlist URL. Please provide a valid playlist link.",
            )
            return redirect("video_library")

        # Extract video URLs from playlist
        video_urls, playlist_title = extract_playlist_videos(playlist_url)

        if not video_urls:
            messages.error(
                request, "Could not extract videos from playlist. Please check the URL."
            )
            return redirect("video_library")

        # Create individual video jobs for each video in the playlist
        jobs_created = 0
        for video_url in video_urls[:MAX_PLAYLIST_VIDEOS]:
            try:
                job = VideoJob.objects.create(
                    user=request.user,
                    video_path="",
                    video_name="Playlist Video (downloading...)",
                    youtube_url=video_url,
                    status=JobStatus.PENDING,
                )

                # Process video in background
                start_video_job_thread(job.job_id)
                jobs_created += 1

            except Exception as e:
                logger.error(f"Error creating job for video {video_url}: {e}")
                continue

        if jobs_created > 0:
            messages.success(
                request,
                f'YouTube playlist "{playlist_title or "Unknown"}" processed. {jobs_created} videos queued for download and processing.',
            )
            messages.info(
                request,
                "Videos will appear in your library as they are processed. This may take several minutes.",
            )
        else:
            messages.error(request, "No videos could be processed from the playlist.")

    except Exception as e:
        logger.error(f"Error processing YouTube playlist: {e}")
        messages.error(request, f"Error processing YouTube playlist: {e}")

    return redirect("video_library")


# Enhanced Search Interfaces
@login_required
def enhanced_search_interface(request):
    """Enhanced search interface for authenticated users."""
    return render(
        request,
        "video_processor/enhanced_search.html",
        {
            "semantic_available": search_available,
            "enhanced_available": enhanced_search is not None,
        },
    )


def public_enhanced_search_interface(request):
    """Public enhanced search interface - no authentication required."""
    return render(
        request,
        "video_processor/public_enhanced_search.html",
        {
            "semantic_available": search_available,
            "enhanced_available": enhanced_search is not None,
        },
    )


def public_user_search_interface(request, username):
    """Public search interface for a specific user's videos."""
    try:
        target_user = User.objects.get(username=username)
    except User.DoesNotExist:
        return render(
            request, "video_processor/user_not_found.html", {"username": username}
        )

    return render(
        request,
        "video_processor/public_user_search.html",
        {
            "target_user": target_user,
            "username": username,
            "semantic_available": search_available,
        },
    )


def public_user_enhanced_search_interface(request, username):
    """Public enhanced search interface for a specific user's videos."""
    try:
        target_user = User.objects.get(username=username)
    except User.DoesNotExist:
        return render(
            request, "video_processor/user_not_found.html", {"username": username}
        )

    return render(
        request,
        "video_processor/public_user_enhanced_search.html",
        {
            "target_user": target_user,
            "username": username,
            "semantic_available": search_available,
            "enhanced_available": enhanced_search is not None,
        },
    )


@login_required
def transcript_editor(request, job_id):
    """Transcript editor for a specific video."""
    try:
        video = VideoJob.objects.get(job_id=job_id, user=request.user)
    except VideoJob.DoesNotExist:
        if (
            request.method != "GET"
            or request.headers.get("Content-Type") == "application/json"
        ):
            return JsonResponse(
                {"status": "error", "message": "Video not found or access denied."},
                status=404,
            )
        messages.error(request, "Video not found or access denied.")
        return redirect("video_library")

    if video.status != JobStatus.COMPLETED:
        if (
            request.method != "GET"
            or request.headers.get("Content-Type") == "application/json"
        ):
            return JsonResponse(
                {"status": "error", "message": "Video processing not completed yet."},
                status=400,
            )
        messages.error(request, "Video processing not completed yet.")
        return redirect("video_library")

    if request.method == "GET" and request.GET.get("format") == "json":
        return JsonResponse(
            {"status": "success", "transcript": video.transcription_text}
        )

    if request.method == "POST":
        try:
            data = json.loads(request.body)
            transcript = data.get("transcript", "")
            if video.transcription:
                video.transcription = {
                    **video.transcription,
                    "text": transcript,
                    "word_count": len(transcript.split()),
                }
            else:
                video.transcription = {
                    "text": transcript,
                    "word_count": len(transcript.split()),
                }
            video.save()
            return JsonResponse({"status": "success"})
        except (json.JSONDecodeError, TypeError) as e:
            return JsonResponse({"status": "error", "message": str(e)}, status=400)

    return render(
        request,
        "video_processor/transcript_editor.html",
        {
            "video": video,
        },
    )


@login_required
def delete_video(request, job_id):
    """Delete a video and its associated files."""
    if request.method != "POST":
        messages.error(request, "Invalid request method.")
        return redirect("video_library")

    try:
        video = VideoJob.objects.get(job_id=job_id, user=request.user)
    except VideoJob.DoesNotExist:
        messages.error(request, "Video not found or access denied.")
        return redirect("video_library")

    try:
        # Store video name for success message
        video_name = video.video_name

        # Delete video file if it exists
        if video.video_path and os.path.exists(video.video_path):
            os.remove(video.video_path)

        # Delete the video job from database
        video.delete()

        messages.success(
            request, f'Video "{video_name}" has been successfully deleted.'
        )

    except Exception as e:
        logger.error(f"Error deleting video {job_id}: {e}")
        messages.error(request, f"Error deleting video: {e}")

    return redirect("video_library")


# API Endpoints for Admin Functionality


@extend_schema(
    tags=["Admin"],
    summary="Get search engine status",
    description="Returns the current status of the search engine including initialization state and indexed segments count.",
    responses={200: {"description": "Search engine status"}},
)
@csrf_exempt
def api_search_status(request):
    """API endpoint to get search engine status."""
    try:
        engine_ready = is_search_engine_available()
        status = {
            "available": search_engine is not None,
            "initialized": engine_ready,
            "model_name": "all-MiniLM-L6-v2",
            "indexed_segments": 0,
        }

        if search_engine:
            try:
                stats = search_engine.get_stats()
                status["initialized"] = stats.get("is_initialized", engine_ready)
                status["indexed_segments"] = stats.get("total_segments", 0)
                status["model_name"] = stats.get("model_name", status["model_name"])
            except Exception as e:
                logger.error(f"Error getting search engine stats: {e}")

        return JsonResponse(status)
    except Exception as e:
        logger.error(f"Error in api_search_status: {e}")
        return JsonResponse({"error": str(e)}, status=500)


def rebuild_search_index():
    """Rebuild semantic search index (CLI helper)."""
    if not search_engine:
        return 0
    return rebuild_semantic_search_index(search_engine)


@login_required
@require_http_methods(["POST"])
def api_rebuild_search_index(request):
    """API endpoint to rebuild the search index."""
    try:
        if not search_engine:
            return JsonResponse(
                {"success": False, "error": "Search engine not available"}
            )

        completed_videos = VideoJob.objects.filter(status=JobStatus.COMPLETED)

        if not completed_videos.exists():
            return JsonResponse(
                {"success": False, "error": "No completed videos to index"}
            )

        try:
            segments_indexed = rebuild_semantic_search_index(search_engine)
        except Exception as e:
            logger.error(f"Error rebuilding search index: {e}")
            return JsonResponse(
                {"success": False, "error": f"Failed to rebuild index: {str(e)}"}
            )

        global search_available
        search_available = is_search_engine_available()

        return JsonResponse(
            {
                "success": True,
                "message": f"Search index rebuilt successfully with {segments_indexed} segments",
                "segments_indexed": segments_indexed,
                "initialized": search_available,
            }
        )

    except Exception as e:
        logger.error(f"Error in api_rebuild_search_index: {e}")
        return JsonResponse({"success": False, "error": str(e)}, status=500)


@csrf_exempt
@require_http_methods(["POST"])
def api_rebuild_enhanced_search_index(request):
    """API endpoint to rebuild the enhanced search index."""
    try:
        if not enhanced_search or not PHASE2_AI_AVAILABLE:
            return JsonResponse(
                {"success": False, "error": "Enhanced search engine not available"}
            )

        # Get video segments from the regular search engine
        from semantic_search import search_engine

        if not is_search_engine_available():
            try:
                rebuild_semantic_search_index(search_engine)
            except Exception as e:
                return JsonResponse(
                    {
                        "success": False,
                        "error": f"Failed to build base search index: {str(e)}",
                    }
                )

        video_segments_data = []

        for segment in search_engine.segments_metadata:
            video_segments_data.append(
                {
                    "text": segment.get("text", ""),
                    "video_id": segment.get("job_id", ""),
                    "video_title": segment.get("video_name", ""),
                    "start_time": segment.get("start_time", 0),
                    "end_time": segment.get("end_time", 0),
                }
            )

        if not video_segments_data:
            return JsonResponse(
                {"success": False, "error": "No video segments found for indexing"}
            )

        # Build enhanced search index
        try:
            enhanced_search.build_enhanced_index(video_segments_data)
            total_segments = len(video_segments_data)

            return JsonResponse(
                {
                    "success": True,
                    "message": f"Enhanced search index built successfully with {total_segments} segments from {len(set(seg['video_id'] for seg in video_segments_data))} videos",
                }
            )

        except Exception as e:
            logger.error(f"Error building enhanced search index: {e}")
            return JsonResponse(
                {"success": False, "error": f"Failed to build enhanced index: {str(e)}"}
            )

    except Exception as e:
        logger.error(f"Error in api_rebuild_enhanced_search_index: {e}")
        return JsonResponse({"success": False, "error": str(e)}, status=500)


@login_required
@require_http_methods(["POST"])
def api_cleanup_youtube(request):
    """API endpoint to cleanup YouTube video files."""
    try:
        dry_run = request.POST.get("dry_run", "false").lower() == "true"

        # Find YouTube videos that have been processed
        youtube_videos = VideoJob.objects.filter(
            status=JobStatus.COMPLETED, video_path__isnull=False
        ).exclude(video_path="")

        files_processed = 0
        space_freed_mb = 0
        files_info = []

        for video in youtube_videos:
            if video.video_path and os.path.exists(video.video_path):
                # Check if it's a YouTube video (has youtube_url or video_path contains youtube indicators)
                if (
                    hasattr(video, "youtube_url") and video.youtube_url
                ) or "youtube" in video.video_path.lower():
                    file_size = os.path.getsize(video.video_path)
                    file_size_mb = round(file_size / (1024 * 1024), 2)

                    files_info.append(
                        {
                            "name": os.path.basename(video.video_path),
                            "size_mb": file_size_mb,
                        }
                    )

                    if not dry_run:
                        # Actually delete the file and mark as cleaned up
                        os.remove(video.video_path)
                        video.video_path = f"{video.video_path} [CLEANED_UP]"
                        video.save()

                    files_processed += 1
                    space_freed_mb += file_size_mb

        return JsonResponse(
            {
                "success": True,
                "files_processed": files_processed,
                "space_freed_mb": round(space_freed_mb, 2),
                "files": files_info[:10],  # Limit to first 10 files for display
            }
        )

    except Exception as e:
        logger.error(f"Error in api_cleanup_youtube: {e}")
        return JsonResponse({"success": False, "error": str(e)}, status=500)


@extend_schema(
    tags=["Admin"],
    summary="Get pending jobs",
    description="Retrieve a list of pending video processing jobs.",
    responses={200: {"description": "List of pending jobs"}},
)
@csrf_exempt
def api_pending_jobs(request):
    """API endpoint to get pending jobs."""
    try:
        pending_jobs = VideoJob.objects.filter(status=JobStatus.PENDING).order_by(
            "-created_at"
        )

        jobs_data = []
        for job in pending_jobs[:20]:  # Limit to 20 most recent
            file_size_mb = 0
            if job.file_size_bytes:
                file_size_mb = round(job.file_size_bytes / (1024 * 1024), 2)

            jobs_data.append(
                {
                    "job_id": str(job.job_id),
                    "video_name": job.video_name,
                    "file_size_mb": file_size_mb,
                    "created_at": job.created_at.isoformat(),
                }
            )

        return JsonResponse({"count": len(jobs_data), "pending_jobs": jobs_data})

    except Exception as e:
        logger.error(f"Error in api_pending_jobs: {e}")
        return JsonResponse({"error": str(e)}, status=500)


@login_required
@require_http_methods(["POST"])
def api_process_job(request):
    """API endpoint to manually process a job."""
    try:
        job_id = request.POST.get("job_id")
        if not job_id:
            return JsonResponse({"success": False, "error": "Job ID required"})

        try:
            job = VideoJob.objects.get(job_id=job_id, user=request.user)
        except VideoJob.DoesNotExist:
            return JsonResponse(
                {"success": False, "error": "Job not found or access denied"}
            )

        if job.status != JobStatus.PENDING:
            return JsonResponse(
                {
                    "success": False,
                    "error": f"Job is not pending (current status: {job.status})",
                }
            )

        # Start processing in background
        start_video_job_thread(job_id)

        return JsonResponse(
            {
                "success": True,
                "message": f"Processing started for '{job.video_name}'",
                "job_id": job_id,
            }
        )

    except Exception as e:
        logger.error(f"Error in api_process_job: {e}")
        return JsonResponse({"success": False, "error": str(e)}, status=500)


@extend_schema(
    tags=["Videos"],
    summary="Get video details",
    description="Retrieve detailed information about a specific video by job ID.",
    parameters=[
        OpenApiParameter(
            "job_id",
            OpenApiTypes.UUID,
            location=OpenApiParameter.PATH,
            description="Video job ID",
        )
    ],
    responses={
        200: {"description": "Video details"},
        404: {"description": "Video not found"},
    },
)
@csrf_exempt
def api_video_details(request, job_id):
    """API endpoint to get video details."""
    try:
        # Try to get video without user restriction for public access
        video = VideoJob.objects.get(job_id=job_id)

        video_data = {
            "job_id": str(video.job_id),
            "video_name": video.video_name,
            "status": video.status,
            "media_type": "audio" if video.is_audio_file else "video",
            "content_type": (
                get_media_content_type(video.video_path) if video.video_path else None
            ),
            "is_youtube": hasattr(video, "youtube_url") and bool(video.youtube_url),
            "youtube_video_id": None,
            "duration_seconds": video.duration_seconds,
            "video_path": video.video_path,
            "youtube_url": getattr(video, "youtube_url", None),
        }

        # Extract YouTube video ID from URL if available
        if video_data["is_youtube"] and hasattr(video, "youtube_url"):
            import re

            # Enhanced YouTube regex patterns
            youtube_patterns = [
                r"(?:youtube\.com/watch\?v=|youtu\.be/|youtube\.com/embed/)([a-zA-Z0-9_-]{11})",
                r"youtube\.com/watch\?.*v=([a-zA-Z0-9_-]{11})",
                r"youtu\.be/([a-zA-Z0-9_-]{11})",
                r"youtube\.com/embed/([a-zA-Z0-9_-]{11})",
            ]

            for pattern in youtube_patterns:
                match = re.search(pattern, video.youtube_url)
                if match:
                    video_data["youtube_video_id"] = match.group(1)
                    break

        # If no YouTube URL but filename contains YouTube video ID, extract it
        if not video_data["youtube_video_id"] and video.video_path:
            import re

            # Extract YouTube video ID from filename (common pattern: ID_title.mp4)
            # Look for 11-character YouTube video ID at the beginning of the filename
            filename_pattern = r"^([a-zA-Z0-9_-]{11})_"
            match = re.search(filename_pattern, os.path.basename(video.video_path))
            if match:
                video_data["youtube_video_id"] = match.group(1)
                video_data["is_youtube"] = True
                # Construct the YouTube URL from the video ID
                video_data["youtube_url"] = (
                    f"https://www.youtube.com/watch?v={video_data['youtube_video_id']}"
                )

        # If we found a video ID, construct proper YouTube URLs
        if video_data["youtube_video_id"]:
            video_data["youtube_watch_url"] = (
                f"https://www.youtube.com/watch?v={video_data['youtube_video_id']}"
            )
            video_data["youtube_embed_url"] = (
                f"https://www.youtube.com/embed/{video_data['youtube_video_id']}"
            )

        return JsonResponse(video_data)

    except VideoJob.DoesNotExist:
        return JsonResponse({"error": "Video not found"}, status=404)
    except Exception as e:
        logger.error(f"Error in api_video_details: {e}")
        return JsonResponse({"error": str(e)}, status=500)


@extend_schema(
    tags=["Admin"],
    summary="Get detailed statistics",
    description="Retrieve comprehensive dashboard statistics including video counts, processing times, content stats, and search engine status.",
    responses={200: {"description": "Detailed statistics"}},
)
@csrf_exempt
def api_detailed_stats(request):
    """API endpoint to get comprehensive dashboard statistics."""
    try:
        # Video statistics
        all_videos = VideoJob.objects.all()
        completed_videos = all_videos.filter(status=JobStatus.COMPLETED)
        total_videos = completed_videos.count()
        pending_jobs = all_videos.filter(status=JobStatus.PENDING).count()
        processing_jobs = all_videos.filter(status=JobStatus.PROCESSING).count()
        failed_jobs = all_videos.filter(status=JobStatus.FAILED).count()

        # Recent jobs (last 7 days)
        from datetime import datetime, timedelta

        seven_days_ago = datetime.now() - timedelta(days=7)
        recent_jobs_7_days = all_videos.filter(created_at__gte=seven_days_ago).count()

        # Processing statistics
        processing_times = [
            job.processing_time for job in completed_videos if job.processing_time
        ]
        total_processing_time = sum(processing_times) if processing_times else 0
        average_processing_time = (
            sum(processing_times) / len(processing_times) if processing_times else 0
        )

        # Content duration in hours
        content_durations = [
            job.duration_seconds for job in completed_videos if job.duration_seconds
        ]
        total_duration_seconds = sum(content_durations) if content_durations else 0
        total_duration_hours = (
            round(total_duration_seconds / 3600, 1) if total_duration_seconds else 0
        )

        # Content statistics
        word_counts = [job.word_count for job in completed_videos if job.word_count]
        total_words = sum(word_counts) if word_counts else 0

        # Language distribution (mock data - can be enhanced later)
        language_distribution = {"en": total_videos} if total_videos > 0 else {}

        # Storage statistics
        file_sizes = [job.file_size_bytes for job in all_videos if job.file_size_bytes]
        total_file_size_bytes = sum(file_sizes) if file_sizes else 0
        total_file_size_gb = round(total_file_size_bytes / (1024**3), 2)

        # Search engine stats
        search_stats = {}
        try:
            if search_engine and hasattr(search_engine, "is_initialized"):
                search_stats = {
                    "indexed_segments": (
                        search_engine.index.ntotal
                        if hasattr(search_engine, "index") and search_engine.index
                        else 0
                    ),
                    "is_initialized": search_engine.is_initialized,
                    "model_name": "all-MiniLM-L6-v2",
                }
            else:
                search_stats = {
                    "indexed_segments": 0,
                    "is_initialized": False,
                    "error": "Search engine not available",
                }
        except Exception as e:
            search_stats = {
                "indexed_segments": 0,
                "is_initialized": False,
                "error": str(e),
            }

        return JsonResponse(
            {
                "video_stats": {
                    "total_videos": total_videos,
                    "pending_jobs": pending_jobs,
                    "processing_jobs": processing_jobs,
                    "failed_jobs": failed_jobs,
                    "recent_jobs_7_days": recent_jobs_7_days,
                },
                "processing_stats": {
                    "total_processing_time": round(total_processing_time, 1),
                    "average_processing_time": round(average_processing_time, 1),
                    "total_duration_hours": total_duration_hours,
                },
                "content_stats": {
                    "total_words": total_words,
                    "language_distribution": language_distribution,
                },
                "storage_stats": {"total_file_size_gb": total_file_size_gb},
                "search_stats": search_stats,
            }
        )

    except Exception as e:
        logger.error(f"Error getting detailed stats: {e}")
        return JsonResponse({"error": str(e)}, status=500)


def process_video_job(job_id):
    """Process a video job - wrapper function for background processing."""
    from django.db import close_old_connections

    close_old_connections()
    with _JOB_SEMAPHORE:
        try:
            job = VideoJob.objects.get(job_id=job_id)
            logger.info(f"🚀 Processing video: {job.video_name}")

            job.status = JobStatus.PROCESSING
            job.started_at = timezone.now()
            job.save()

            if job.youtube_url and not job.video_path:
                logger.info(f"Downloading YouTube video: {job.youtube_url}")
                media_videos_dir = Path(settings.MEDIA_ROOT) / "videos"
                success, video_path, video_info, error_msg = download_youtube_video(
                    job.youtube_url, media_videos_dir
                )
                if not success:
                    job.status = JobStatus.FAILED
                    job.error_message = f"Failed to download YouTube video: {error_msg}"
                    job.completed_at = timezone.now()
                    job.save()
                    logger.error(f"❌ YouTube download failed: {error_msg}")
                    return

                job.video_path = video_path
                job.video_name = video_info.get("title", job.video_name)
                job.file_size_bytes = Path(video_path).stat().st_size
                job.save()

            if not job.video_path:
                job.status = JobStatus.FAILED
                job.error_message = "No video file available for processing"
                job.completed_at = timezone.now()
                job.save()
                return

            start_time = time.time()

            # Process video using core processor
            result = video_processor.create_comprehensive_media_summary(job.video_path)

            processing_time = time.time() - start_time

            # Update job with results
            job.metadata = result.get("metadata")
            job.transcription = result.get("transcription")
            job.processing_errors = result.get("processing_errors", [])
            job.processing_time = processing_time
            job.completed_at = timezone.now()

            if result.get("processing_errors"):
                job.status = JobStatus.FAILED
                job.error_message = "; ".join(result["processing_errors"])
                logger.error(f"❌ Processing failed: {job.error_message}")
            else:
                job.status = JobStatus.COMPLETED
                logger.info(f"✅ Processing completed in {processing_time:.2f}s")
                logger.info(f"   📝 Transcribed {job.word_count} words")
                logger.info(f"   🗣️ Language: {job.language}")

            job.save()

            if job.status == JobStatus.COMPLETED and search_engine:
                try:
                    segments_indexed = rebuild_semantic_search_index(search_engine)
                    global search_available
                    search_available = is_search_engine_available()
                    logger.info(
                        f"Search index rebuilt with {segments_indexed} segments"
                    )
                except Exception as index_error:
                    logger.warning(
                        f"Failed to rebuild search index after processing: {index_error}"
                    )

        except Exception as e:
            logger.error(f"❌ Error processing job {job_id}: {e}")
            try:
                job = VideoJob.objects.get(job_id=job_id)
                job.status = JobStatus.FAILED
                job.error_message = str(e)
                job.completed_at = timezone.now()
                job.save()
            except Exception:
                pass
        finally:
            close_old_connections()


@extend_schema(
    tags=["Search"],
    summary="Search videos",
    description="Search through video transcriptions using keyword, semantic, or hybrid search modes.",
    request={
        "application/json": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Search query text"},
                "search_mode": {
                    "type": "string",
                    "enum": ["keyword", "semantic", "hybrid"],
                    "default": "hybrid",
                    "description": "Search mode to use",
                },
            },
            "required": ["query"],
        }
    },
    responses={
        200: {
            "description": "Search results",
            "content": {
                "application/json": {
                    "example": {
                        "success": True,
                        "results": [],
                        "query": "example query",
                        "search_mode": "hybrid",
                        "total_results": 0,
                    }
                }
            },
        }
    },
)
@csrf_exempt
def api_search(request):
    """API endpoint for video search that returns JSON."""
    if request.method != "POST":
        return JsonResponse({"error": "Method not allowed"}, status=405)

    try:
        data = json.loads(request.body)
        query = data.get("query", "").strip()
        search_mode = data.get("search_mode", data.get("mode", "hybrid"))
        username = data.get("username", "").strip()

        if not query:
            return JsonResponse({"error": "Query is required"}, status=400)

        target_user = resolve_target_user(username)
        if target_user is False:
            return JsonResponse({"error": "User not found"}, status=404)

        # Track search query
        VideoSearchQuery.objects.create(query=query, results_count=0)

        search_results, search_mode = run_legacy_api_search(
            query, search_mode, search_engine, k=50
        )

        search_results = filter_api_results_by_user(search_results, target_user)

        # Update search query results count
        VideoSearchQuery.objects.filter(query=query).update(
            results_count=len(search_results)
        )

        return JsonResponse(
            {
                "success": True,
                "results": search_results,
                "query": query,
                "search_mode": search_mode,
                "mode": search_mode,
                "total_results": len(search_results),
                "count": len(search_results),
            }
        )

    except json.JSONDecodeError:
        return JsonResponse({"error": "Invalid JSON"}, status=400)
    except Exception as e:
        logger.error(f"API search error: {e}")
        return JsonResponse({"error": str(e)}, status=500)


@csrf_exempt
def health_check(request):
    """Health check endpoint for load balancers and monitoring"""
    try:
        # Basic health checks
        from django.db import connection

        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")

        return JsonResponse(
            {
                "status": "healthy",
                "timestamp": timezone.now().isoformat(),
                "version": "1.0.0",
            }
        )
    except Exception as e:
        return JsonResponse(
            {
                "status": "unhealthy",
                "error": str(e),
                "timestamp": timezone.now().isoformat(),
            },
            status=503,
        )


@extend_schema(
    tags=["Health"],
    summary="Health check",
    description="Health check endpoint for load balancers and monitoring. Returns system status and component availability.",
    responses={
        200: {"description": "System is healthy"},
        503: {"description": "System is unhealthy"},
    },
)
@csrf_exempt
def api_health_check(request):
    """API health check endpoint for load balancers and monitoring"""
    health_status = {
        "status": "healthy",
        "timestamp": timezone.now().isoformat(),
        "version": "1.0.0",
        "components": {},
    }
    overall_healthy = True

    try:
        # Database connectivity check
        from django.db import connection

        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
        health_status["components"]["database"] = "available"
    except Exception as e:
        health_status["components"]["database"] = f"unavailable: {str(e)}"
        overall_healthy = False

    # Check search engine availability
    try:
        if search_available and search_engine:
            if (
                hasattr(search_engine, "is_initialized")
                and search_engine.is_initialized
            ):
                health_status["components"]["search_engine"] = "available_initialized"
            else:
                health_status["components"][
                    "search_engine"
                ] = "available_not_initialized"
        else:
            health_status["components"]["search_engine"] = "unavailable"
    except Exception as e:
        health_status["components"]["search_engine"] = f"unavailable: {str(e)}"

    # Check enhanced search
    try:
        if PHASE2_AI_AVAILABLE and enhanced_search:
            health_status["components"]["enhanced_search"] = "available"
        else:
            health_status["components"]["enhanced_search"] = "unavailable"
    except Exception as e:
        health_status["components"]["enhanced_search"] = f"unavailable: {str(e)}"

    # Check Celery if configured
    try:
        from django.conf import settings

        if hasattr(settings, "CELERY_BROKER_URL") and settings.CELERY_BROKER_URL:
            health_status["components"]["celery"] = "configured"
        else:
            health_status["components"]["celery"] = "not_configured"
    except Exception:
        health_status["components"]["celery"] = "unknown"

    if not overall_healthy:
        health_status["status"] = "unhealthy"
        return JsonResponse(health_status, status=503)

    return JsonResponse(health_status)


@csrf_exempt
def video_file_serve(request, job_id):
    """Serve video files for playback with smart handling of cleaned up files"""
    try:
        # Get the video job without user restriction for public access
        video_job = get_object_or_404(VideoJob, job_id=job_id)

        # Check if video file exists and is not cleaned up
        video_path = video_job.video_path
        if not video_path or "[CLEANED_UP]" in str(video_path):
            # File has been cleaned up - return info about this
            response_data = {
                "error": "Video file has been cleaned up to save storage",
                "video_name": video_job.video_name,
                "is_youtube": hasattr(video_job, "youtube_url")
                and bool(video_job.youtube_url),
                "youtube_url": getattr(video_job, "youtube_url", None),
                "duration_seconds": video_job.duration_seconds,
                "cleaned_up": True,
            }

            # If it's a YouTube video, try to extract video ID and provide proper URLs
            if response_data["is_youtube"] and response_data["youtube_url"]:
                import re

                youtube_patterns = [
                    r"(?:youtube\.com/watch\?v=|youtu\.be/|youtube\.com/embed/)([a-zA-Z0-9_-]{11})",
                    r"youtube\.com/watch\?.*v=([a-zA-Z0-9_-]{11})",
                    r"youtu\.be/([a-zA-Z0-9_-]{11})",
                    r"youtube\.com/embed/([a-zA-Z0-9_-]{11})",
                ]

                for pattern in youtube_patterns:
                    match = re.search(pattern, response_data["youtube_url"])
                    if match:
                        video_id = match.group(1)
                        response_data["youtube_video_id"] = video_id
                        response_data["youtube_watch_url"] = (
                            f"https://www.youtube.com/watch?v={video_id}"
                        )
                        response_data["youtube_embed_url"] = (
                            f"https://www.youtube.com/embed/{video_id}"
                        )
                        break

            # If no YouTube URL but filename contains YouTube video ID, extract it
            if not response_data.get("youtube_video_id") and video_path:
                import re

                # Extract YouTube video ID from filename (common pattern: ID_title.mp4)
                # Look for 11-character YouTube video ID at the beginning of the filename
                filename_pattern = r"^([a-zA-Z0-9_-]{11})_"
                match = re.search(filename_pattern, os.path.basename(video_path))
                if match:
                    video_id = match.group(1)
                    response_data["youtube_video_id"] = video_id
                    response_data["is_youtube"] = True
                    response_data["youtube_url"] = (
                        f"https://www.youtube.com/watch?v={video_id}"
                    )
                    response_data["youtube_watch_url"] = (
                        f"https://www.youtube.com/watch?v={video_id}"
                    )
                    response_data["youtube_embed_url"] = (
                        f"https://www.youtube.com/embed/{video_id}"
                    )

            return JsonResponse(response_data, status=404)

        if not os.path.exists(video_path):
            return JsonResponse(
                {
                    "error": "Video file not found",
                    "video_name": video_job.video_name,
                    "cleaned_up": True,
                },
                status=404,
            )

        # Serve the media file
        file_size = os.path.getsize(video_path)

        response = FileResponse(
            open(video_path, "rb"),
            content_type=get_media_content_type(video_path),
        )
        response["Accept-Ranges"] = "bytes"
        response["Content-Length"] = file_size

        return response

    except VideoJob.DoesNotExist:
        return JsonResponse({"error": "Video not found"}, status=404)
    except Exception as e:
        logger.error(f"Error serving video file: {e}")
        return JsonResponse({"error": "Internal server error"}, status=500)


@extend_schema(
    tags=["Search"],
    summary="Advanced search",
    description="Advanced search API with comprehensive controls including search type selection, similarity thresholds, diversification, and result filtering.",
    request={
        "application/json": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Search query text"},
                "k": {
                    "type": "integer",
                    "default": 25,
                    "description": "Number of results",
                },
                "min_similarity": {
                    "type": "number",
                    "default": 0.25,
                    "description": "Minimum similarity score",
                },
                "diversify": {
                    "type": "boolean",
                    "default": True,
                    "description": "Enable diversification",
                },
                "max_per_video": {
                    "type": "integer",
                    "default": 2,
                    "description": "Max results per video",
                },
                "filter_topics": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Topic filters",
                },
                "search_type": {
                    "type": "string",
                    "enum": ["enhanced", "semantic", "keyword", "hybrid"],
                    "default": "enhanced",
                },
                "include_context": {
                    "type": "boolean",
                    "default": True,
                    "description": "Include context window",
                },
                "include_sentiment": {
                    "type": "boolean",
                    "default": False,
                    "description": "Include sentiment scores",
                },
            },
            "required": ["query"],
        }
    },
    responses={200: {"description": "Advanced search results"}},
)
@csrf_exempt
def api_advanced_search(request):
    """Advanced search API with more controls and features."""
    if request.method != "POST":
        return JsonResponse({"error": "Method not allowed"}, status=405)

    try:
        data = json.loads(request.body)
        query = data.get("query", "").strip()
        username = data.get("username", "").strip()

        target_user = resolve_target_user(username)
        if target_user is False:
            return JsonResponse({"error": "User not found"}, status=404)

        # Advanced search parameters
        k = data.get("k", 25)
        min_similarity = data.get("min_similarity", 0.25)
        diversify = data.get("diversify", True)
        max_per_video = data.get("max_per_video", 2)
        filter_topics = data.get("filter_topics", None)
        search_type = data.get(
            "search_type", "enhanced"
        )  # enhanced, semantic, keyword, hybrid
        include_context = data.get("include_context", True)
        include_sentiment = data.get("include_sentiment", False)

        if not query:
            return JsonResponse({"error": "Query is required"}, status=400)

        search_results, search_mode = run_advanced_api_search(
            query,
            search_engine,
            enhanced_search,
            PHASE2_AI_AVAILABLE,
            search_type,
            k,
            min_similarity,
            diversify,
            max_per_video,
            filter_topics,
        )

        search_results = filter_api_results_by_user(search_results, target_user)

        # Calculate statistics
        video_count = len(set(result.get("video_id") for result in search_results))
        avg_confidence = (
            sum(result.get("relevance_score", 0) for result in search_results)
            / len(search_results)
            if search_results
            else 0
        )

        # Filter results based on include_context and include_sentiment
        if not include_context:
            for result in search_results:
                result.pop("context_window", None)

        if not include_sentiment:
            for result in search_results:
                result.pop("sentiment_score", None)

        return JsonResponse(
            {
                "success": True,
                "results": search_results,
                "query": query,
                "search_mode": search_mode,
                "total_results": len(search_results),
                "unique_videos": video_count,
                "average_confidence": round(avg_confidence, 3),
                "search_params": {
                    "k": k,
                    "min_similarity": min_similarity,
                    "diversify": diversify,
                    "max_per_video": max_per_video,
                    "filter_topics": filter_topics,
                    "search_type": search_type,
                    "include_context": include_context,
                    "include_sentiment": include_sentiment,
                },
            }
        )

    except json.JSONDecodeError:
        return JsonResponse({"error": "Invalid JSON"}, status=400)
    except Exception as e:
        logger.error(f"API advanced search error: {e}")
        return JsonResponse({"error": str(e)}, status=500)


@csrf_exempt
def api_update_video_metadata(request, job_id):
    """Update video metadata (title, YouTube URL) for a given job_id."""
    if request.method != "POST":
        return JsonResponse({"error": "Method not allowed"}, status=405)
    try:
        data = json.loads(request.body)
        title = data.get("title", "").strip()
        youtube_url = data.get("youtube_url", "").strip()
        video = VideoJob.objects.get(job_id=job_id)
        if title:
            video.video_name = title
            video.title = title
        video.youtube_url = youtube_url or None
        video.save()
        return JsonResponse({"success": True})
    except VideoJob.DoesNotExist:
        return JsonResponse({"error": "Video not found"}, status=404)
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)
