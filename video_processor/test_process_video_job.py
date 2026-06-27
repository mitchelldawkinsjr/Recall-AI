from unittest.mock import MagicMock, patch

from django.contrib.auth.models import User
from django.test import TestCase

from .models import JobStatus, VideoJob


class ProcessVideoJobTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="worker-user", password="testpass123"
        )
        self.job = VideoJob.objects.create(
            user=self.user,
            video_path="/tmp/test.mp4",
            video_name="test.mp4",
            status=JobStatus.PENDING,
        )

    @patch("video_processor.views.video_processor")
    def test_marks_job_completed_on_success(self, mock_processor):
        from . import views

        mock_processor.create_comprehensive_video_summary.return_value = {
            "metadata": {"duration": 10},
            "transcription": {"text": "hello"},
            "processing_errors": [],
        }

        views.process_video_job(str(self.job.job_id))

        self.job.refresh_from_db()
        self.assertEqual(self.job.status, JobStatus.COMPLETED)
        self.assertIsNotNone(self.job.completed_at)

    @patch("video_processor.views.video_processor")
    def test_marks_job_failed_on_processor_errors(self, mock_processor):
        from . import views

        mock_processor.create_comprehensive_video_summary.return_value = {
            "metadata": {},
            "transcription": {},
            "processing_errors": ["ffmpeg failed"],
        }

        views.process_video_job(str(self.job.job_id))

        self.job.refresh_from_db()
        self.assertEqual(self.job.status, JobStatus.FAILED)
        self.assertIn("ffmpeg failed", self.job.error_message)
