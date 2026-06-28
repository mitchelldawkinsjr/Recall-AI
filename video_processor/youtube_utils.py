"""YouTube URL validation and download helpers."""

import logging
import os
from pathlib import Path
from urllib.parse import urlparse

import yt_dlp

logger = logging.getLogger(__name__)

MAX_PLAYLIST_VIDEOS = 10
MAX_CONCURRENT_JOBS = 2
MAX_VIDEO_DURATION_SECONDS = 3600

VIDEO_EXTENSIONS = {".mp4", ".webm", ".mkv", ".mov", ".m4v", ".avi"}

DEFAULT_YT_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/131.0.0.0 Safari/537.36"
)

YOUTUBE_HOSTS = frozenset(
    {
        "youtube.com",
        "www.youtube.com",
        "m.youtube.com",
        "music.youtube.com",
        "youtu.be",
        "www.youtu.be",
    }
)


def build_ytdlp_opts(**overrides):
    """Shared yt-dlp options for prod VPS downloads (bot checks, retries, cookies)."""
    opts = {
        "quiet": True,
        "no_warnings": True,
        "socket_timeout": 30,
        "retries": 5,
        "fragment_retries": 5,
        "http_headers": {"User-Agent": DEFAULT_YT_USER_AGENT},
        # android/web clients reduce bot-check failures on server IPs
        "extractor_args": {"youtube": {"player_client": ["android", "web"]}},
    }

    cookies_file = os.environ.get("YOUTUBE_COOKIES_FILE", "").strip()
    if cookies_file:
        cookie_path = Path(cookies_file)
        if cookie_path.is_file():
            opts["cookiefile"] = str(cookie_path)
            logger.info("Using YouTube cookies from %s", cookie_path)
        else:
            logger.warning("YOUTUBE_COOKIES_FILE set but not found: %s", cookies_file)

    extra_extractor = overrides.pop("extractor_args", None)
    if extra_extractor:
        youtube_args = opts.setdefault("extractor_args", {}).setdefault("youtube", {})
        youtube_args.update(extra_extractor.get("youtube", {}))

    opts.update(overrides)
    return opts


def normalize_duration(raw):
    """Return a numeric duration in seconds; missing/invalid values become 0."""
    if raw is None:
        return 0
    try:
        duration = float(raw)
    except (TypeError, ValueError):
        return 0
    return max(duration, 0)


def _parsed_host(url):
    try:
        parsed = urlparse(url.strip())
    except Exception:
        return None
    if parsed.scheme not in ("http", "https"):
        return None
    return (parsed.netloc or "").lower()


def is_youtube_host(url):
    host = _parsed_host(url)
    return host in YOUTUBE_HOSTS if host else False


def is_youtube_playlist_url(url):
    """Detect YouTube playlist URLs."""
    if not is_youtube_host(url):
        return False
    return "list=" in url


def is_youtube_video_url(url):
    """Allow single YouTube video URLs only (not playlists)."""
    if not url or not isinstance(url, str):
        return False
    if not is_youtube_host(url):
        return False
    if is_youtube_playlist_url(url):
        return False
    lowered = url.lower()
    if "/playlist" in lowered:
        return False
    return "watch?v=" in lowered or "youtu.be/" in lowered or "/shorts/" in lowered


def pick_downloaded_video_file(output_dir, video_id):
    """Pick the most likely video file for a yt-dlp download."""
    output_path = Path(output_dir)
    candidates = list(output_path.glob(f"{video_id}_*"))
    if not candidates:
        return None

    video_candidates = [
        path
        for path in candidates
        if path.is_file() and path.suffix.lower() in VIDEO_EXTENSIONS
    ]
    if not video_candidates:
        return None

    video_candidates.sort(key=lambda path: path.stat().st_mtime, reverse=True)
    return video_candidates[0]


def download_youtube_video(url, output_path):
    """Download a YouTube video using yt-dlp."""
    if not is_youtube_video_url(url):
        return False, None, None, "Invalid YouTube video URL"

    try:
        output_path = Path(output_path)
        output_path.mkdir(parents=True, exist_ok=True)

        ydl_opts = build_ytdlp_opts(
            format="best[ext=mp4]/best",
            outtmpl=str(output_path / "%(id)s_%(title)s.%(ext)s"),
            restrictfilenames=True,
            noplaylist=True,
        )

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            if not info:
                return False, None, None, "Could not extract video information"

            duration = normalize_duration(info.get("duration"))
            if duration > MAX_VIDEO_DURATION_SECONDS:
                return (
                    False,
                    None,
                    None,
                    f"Video too long: {duration // 60:.1f} minutes (max 60 minutes)",
                )

            ydl.download([url])

            video_id = info.get("id", "unknown")
            video_path = pick_downloaded_video_file(output_path, video_id)
            if not video_path:
                return False, None, None, "Downloaded video file not found"

            return (
                True,
                str(video_path),
                {
                    "title": info.get("title", "Unknown"),
                    "duration": duration,
                    "video_id": video_id,
                },
                None,
            )

    except Exception as exc:
        logger.error("Error downloading YouTube video: %s", exc)
        return False, None, None, str(exc)
