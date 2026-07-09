"""Search result formatting and shared API search execution."""

from __future__ import annotations

import logging
import re
from typing import Any

from django.contrib.auth.models import User

from .models import JobStatus, VideoJob

logger = logging.getLogger(__name__)


def clean_video_name(video_name: str | None) -> str:
    if not video_name:
        return "Unknown Video"
    name_without_ext = video_name.rsplit(".", 1)[0] if "." in video_name else video_name
    cleaned_name = re.sub(r"_[a-zA-Z0-9_-]{11}$", "", name_without_ext)
    return cleaned_name.strip() or "Video"


def perform_keyword_search(query: str, user=None) -> list[dict[str, Any]]:
    search_results = []
    filters: dict[str, Any] = {
        "status": JobStatus.COMPLETED,
        "transcription__isnull": False,
    }
    if user is not None:
        filters["user"] = user
    videos = VideoJob.objects.filter(**filters)
    for video in videos:
        matching_segments = video.search_segments(query)
        if matching_segments:
            search_results.append({"video": video, "segments": matching_segments})
    return search_results


def flatten_keyword_results(
    keyword_results: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    flat = []
    for item in keyword_results:
        video = item.get("video")
        if not video:
            continue
        for seg in item.get("segments", []):
            flat.append(
                {
                    "job_id": str(video.job_id),
                    "video_name": video.video_name,
                    "start_time": seg["start_time"],
                    "end_time": seg["end_time"],
                    "text": seg["text"],
                    "score": seg.get("relevance_score", 1.0),
                }
            )
    return flat


def convert_semantic_results_to_display_format(semantic_results):
    video_groups = {}
    for result in semantic_results:
        job_id = result.job_id
        if job_id not in video_groups:
            try:
                video = VideoJob.objects.get(job_id=job_id)
                video_groups[job_id] = {"video": video, "segments": []}
            except VideoJob.DoesNotExist:
                continue
        video_groups[job_id]["segments"].append(
            {
                "start_time": result.start_time,
                "end_time": result.end_time,
                "text": result.text,
                "relevance_score": result.score,
                "search_type": result.search_type,
            }
        )
    return list(video_groups.values())


def convert_semantic_results_to_api_format(semantic_results):
    return [
        {
            "video_id": result.job_id,
            "video_name": clean_video_name(result.video_name),
            "start_time": result.start_time,
            "end_time": result.end_time,
            "text": result.text,
            "relevance_score": result.score,
            "search_type": result.search_type,
            "timestamp_formatted": f"{int(result.start_time // 60)}:{int(result.start_time % 60):02d}",
        }
        for result in semantic_results
    ]


def convert_keyword_results_to_api_format(keyword_results):
    return [
        {
            "video_id": result["job_id"],
            "video_name": clean_video_name(result["video_name"]),
            "start_time": result["start_time"],
            "end_time": result["end_time"],
            "text": result["text"],
            "relevance_score": result["score"],
            "search_type": "keyword",
            "timestamp_formatted": f"{int(result['start_time'] // 60)}:{int(result['start_time'] % 60):02d}",
        }
        for result in flatten_keyword_results(keyword_results)
    ]


def convert_enhanced_results_to_api_format(enhanced_results):
    api_results = []
    for result in enhanced_results:
        context = result.context_window
        if len(context) > 200:
            context = context[:200] + "..."
        api_results.append(
            {
                "video_id": result.video_id,
                "video_name": clean_video_name(result.video_title),
                "start_time": result.start_time,
                "end_time": result.end_time,
                "text": result.segment_text,
                "relevance_score": result.confidence_score,
                "semantic_similarity": result.semantic_similarity,
                "search_type": "enhanced",
                "topic_tags": result.topic_tags,
                "context_window": context,
                "sentiment_score": result.sentiment_score,
            }
        )
    return api_results


def resolve_target_user(username: str | None):
    if not username:
        return None
    try:
        return User.objects.get(username=username)
    except User.DoesNotExist:
        return False


def filter_api_results_by_user(results, user):
    if not user:
        return results
    user_job_ids = {
        str(job_id)
        for job_id in VideoJob.objects.filter(user=user).values_list(
            "job_id", flat=True
        )
    }
    return [r for r in results if str(r.get("video_id")) in user_job_ids]


def _keyword_fallback(query: str) -> tuple[list[dict], str]:
    return (
        convert_keyword_results_to_api_format(perform_keyword_search(query)),
        "keyword_fallback",
    )


def get_video_segments_for_search():
    """Get video segments data formatted for semantic search."""
    videos = VideoJob.objects.filter(
        status=JobStatus.COMPLETED, transcription__isnull=False
    )
    video_segments_data = []
    for video in videos:
        segments = video.text_segments
        if segments:
            video_segments_data.append(
                {
                    "job_id": str(video.job_id),
                    "video_name": video.video_name,
                    "segments": segments,
                }
            )
    return video_segments_data


def ensure_search_engine_initialized(search_engine) -> bool:
    if not search_engine:
        return False
    if search_engine.is_initialized:
        return True
    if hasattr(search_engine, "_load_index"):
        search_engine._load_index()
    return search_engine.is_initialized


def rebuild_semantic_search_index(search_engine) -> int:
    segments = get_video_segments_for_search()
    if hasattr(search_engine, "rebuild_index"):
        return search_engine.rebuild_index(segments)
    search_engine.build_index(segments)
    return len(search_engine.segments_metadata)


def run_legacy_api_search(query, search_mode, search_engine, k=50):
    """api/search — keyword, semantic, or search_engine hybrid."""
    try:
        engine_ready = ensure_search_engine_initialized(search_engine)

        if search_mode == "keyword":
            return (
                convert_keyword_results_to_api_format(perform_keyword_search(query)),
                "keyword",
            )

        if search_mode == "semantic":
            if engine_ready:
                results = search_engine.semantic_search(query, top_k=k)
                if results:
                    return convert_semantic_results_to_api_format(results), "semantic"
            return (
                convert_keyword_results_to_api_format(perform_keyword_search(query)),
                "keyword_fallback",
            )

        if search_mode == "hybrid" and engine_ready:
            segments_data = get_video_segments_for_search()
            results = search_engine.hybrid_search(query, segments_data, top_k=k)
            return convert_semantic_results_to_api_format(results), "hybrid"

        return (
            convert_keyword_results_to_api_format(perform_keyword_search(query)),
            "keyword",
        )
    except Exception as exc:
        logger.error("Legacy search error: %s", exc)
        return _keyword_fallback(query)


def run_enhanced_api_search(
    query,
    search_engine,
    enhanced_search,
    phase2_available,
    k,
    min_similarity,
    diversify,
    max_per_video,
    filter_topics,
):
    """api/enhanced-search — enhanced with semantic/keyword fallbacks."""
    try:
        if enhanced_search and phase2_available:
            try:
                enhanced_results = enhanced_search.search(
                    query=query,
                    k=k,
                    min_similarity=min_similarity,
                    filter_topics=filter_topics,
                    diversify_results=diversify,
                    max_results_per_video=max_per_video,
                )
                mode = "enhanced_diversified" if diversify else "enhanced"
                return convert_enhanced_results_to_api_format(enhanced_results), mode
            except Exception as exc:
                logger.warning("Enhanced search failed, falling back: %s", exc)
        if search_engine and ensure_search_engine_initialized(search_engine):
            results = search_engine.semantic_search(query, top_k=k)
            if results:
                return convert_semantic_results_to_api_format(results), "semantic"
        return (
            convert_keyword_results_to_api_format(perform_keyword_search(query)),
            "keyword",
        )
    except Exception as exc:
        logger.error("Enhanced search error: %s", exc)
        return _keyword_fallback(query)


def run_advanced_api_search(
    query,
    search_engine,
    enhanced_search,
    phase2_available,
    search_type,
    k,
    min_similarity,
    diversify,
    max_per_video,
    filter_topics,
):
    """api/advanced-search — enhanced, semantic, keyword, or combined hybrid."""
    try:
        if search_type == "enhanced" and enhanced_search and phase2_available:
            enhanced_results = enhanced_search.search(
                query=query,
                k=k,
                min_similarity=min_similarity,
                filter_topics=filter_topics,
                diversify_results=diversify,
                max_results_per_video=max_per_video,
            )
            return (
                convert_enhanced_results_to_api_format(enhanced_results),
                "enhanced_advanced",
            )

        if (
            search_type == "semantic"
            and search_engine
            and ensure_search_engine_initialized(search_engine)
        ):
            results = search_engine.semantic_search(query, top_k=k)
            if results:
                return convert_semantic_results_to_api_format(results), "semantic"
            return (
                convert_keyword_results_to_api_format(perform_keyword_search(query)),
                "keyword_fallback",
            )

        if search_type == "keyword":
            return (
                convert_keyword_results_to_api_format(perform_keyword_search(query)),
                "keyword",
            )

        if search_type == "hybrid":
            hybrid_results = []
            if enhanced_search and phase2_available:
                try:
                    enhanced_results = enhanced_search.search(
                        query=query,
                        k=k // 2,
                        min_similarity=min_similarity,
                        diversify_results=diversify,
                        max_results_per_video=max_per_video,
                    )
                    hybrid_results.extend(
                        convert_enhanced_results_to_api_format(enhanced_results)
                    )
                except Exception as exc:
                    logger.warning("Enhanced search in hybrid failed: %s", exc)
            if search_engine and ensure_search_engine_initialized(search_engine):
                try:
                    semantic_results = search_engine.semantic_search(
                        query, top_k=k // 2
                    )
                    semantic_api = convert_semantic_results_to_api_format(
                        semantic_results
                    )
                    existing = {
                        (r["video_id"], r["start_time"]) for r in hybrid_results
                    }
                    for result in semantic_api:
                        key = (result["video_id"], result["start_time"])
                        if key not in existing:
                            hybrid_results.append(result)
                except Exception as exc:
                    logger.warning("Semantic search in hybrid failed: %s", exc)
            if hybrid_results:
                return hybrid_results, "hybrid"
            return (
                convert_keyword_results_to_api_format(perform_keyword_search(query)),
                "hybrid",
            )

        if enhanced_search and phase2_available:
            enhanced_results = enhanced_search.search(query, k=k)
            return (
                convert_enhanced_results_to_api_format(enhanced_results),
                "enhanced_fallback",
            )
        if search_engine and ensure_search_engine_initialized(search_engine):
            results = search_engine.semantic_search(query, top_k=k)
            if results:
                return (
                    convert_semantic_results_to_api_format(results),
                    "semantic_fallback",
                )
        return (
            convert_keyword_results_to_api_format(perform_keyword_search(query)),
            "keyword_fallback",
        )

    except Exception as exc:
        logger.error("Advanced search error: %s", exc)
        return _keyword_fallback(query)
