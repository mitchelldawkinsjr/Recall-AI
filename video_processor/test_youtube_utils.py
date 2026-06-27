from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import MagicMock, patch

from django.contrib.auth.models import User
from django.test import RequestFactory, SimpleTestCase, TestCase

from .youtube_utils import (
    MAX_PLAYLIST_VIDEOS,
    download_youtube_video,
    is_youtube_playlist_url,
    is_youtube_video_url,
    normalize_duration,
    pick_downloaded_video_file,
)


class YouTubeUrlValidationTests(SimpleTestCase):
    def test_accepts_standard_watch_url(self):
        self.assertTrue(
            is_youtube_video_url("https://www.youtube.com/watch?v=dQw4w9WgXcQ")
        )

    def test_accepts_short_url(self):
        self.assertTrue(is_youtube_video_url("https://youtu.be/dQw4w9WgXcQ"))

    def test_rejects_playlist_url(self):
        url = "https://www.youtube.com/watch?v=dQw4w9WgXcQ&list=PLtest"
        self.assertTrue(is_youtube_playlist_url(url))
        self.assertFalse(is_youtube_video_url(url))

    def test_rejects_non_youtube_url(self):
        self.assertFalse(is_youtube_video_url("https://example.com/video.mp4"))
        self.assertFalse(is_youtube_video_url("file:///etc/passwd"))

    def test_rejects_non_http_scheme(self):
        self.assertFalse(is_youtube_video_url("ftp://youtube.com/watch?v=abc"))


class DurationNormalizationTests(SimpleTestCase):
    def test_none_becomes_zero(self):
        self.assertEqual(normalize_duration(None), 0)

    def test_invalid_becomes_zero(self):
        self.assertEqual(normalize_duration("not-a-number"), 0)


class PickDownloadedVideoFileTests(SimpleTestCase):
    def test_picks_video_extension_and_ignores_sidecar(self):
        with TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            sidecar = root / "abc123_info.json"
            video = root / "abc123_title.mp4"
            sidecar.write_text("{}")
            video.write_bytes(b"video")

            picked = pick_downloaded_video_file(root, "abc123")
            self.assertEqual(picked, video)


class DownloadYouTubeVideoTests(SimpleTestCase):
    def test_rejects_invalid_url_before_yt_dlp(self):
        success, path, info, error = download_youtube_video(
            "https://example.com/evil", "/tmp"
        )
        self.assertFalse(success)
        self.assertIn("Invalid", error)


class PlaylistHandlerTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="playlist-user", password="testpass123"
        )
        self.factory = RequestFactory()

    @patch("video_processor.views.start_video_job_thread")
    @patch("video_processor.views.extract_playlist_videos")
    def test_playlist_handler_respects_video_limit(self, mock_extract, mock_start):
        from . import views

        urls = [f"https://youtu.be/id{i}" for i in range(15)]
        mock_extract.return_value = (urls, "Test Playlist")

        request = self.factory.post("/upload/")
        request.user = self.user

        with patch("video_processor.views.messages"):
            response = views.handle_youtube_playlist_simple(
                request, "https://www.youtube.com/playlist?list=PLtest"
            )

        self.assertEqual(response.status_code, 302)
        self.assertEqual(mock_start.call_count, MAX_PLAYLIST_VIDEOS)


class YouTubeUploadValidationTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="youtube-user", password="testpass123"
        )
        self.factory = RequestFactory()

    @patch("video_processor.views.start_video_job_thread")
    def test_rejects_invalid_youtube_url(self, mock_start):
        from . import views

        request = self.factory.post("/upload/")
        request.user = self.user

        with patch("video_processor.views.messages") as mock_messages:
            response = views.handle_youtube_upload(
                request, "https://example.com/not-youtube"
            )

        self.assertEqual(response.status_code, 302)
        mock_start.assert_not_called()
        mock_messages.error.assert_called_once()
