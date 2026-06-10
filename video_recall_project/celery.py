"""
Celery configuration for AskMyVideo Django project
"""

import os
import logging
from celery import Celery

logger = logging.getLogger(__name__)

# Set the default Django settings module for the 'celery' program.
# This respects DJANGO_SETTINGS_MODULE environment variable if set
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "video_recall_project.settings")

app = Celery("video_recall_project")

# Using a string here means the worker doesn't have to serialize
# the configuration object to child processes.
app.config_from_object("django.conf:settings", namespace="CELERY")

# Load task modules from all registered Django apps.
app.autodiscover_tasks()

# Check if Celery is properly configured
try:
    from django.conf import settings
    if not hasattr(settings, 'CELERY_BROKER_URL') or not settings.CELERY_BROKER_URL:
        logger.warning("Celery broker URL not configured. Celery tasks will not work.")
    else:
        logger.info(f"Celery configured with broker: {settings.CELERY_BROKER_URL}")
except Exception as e:
    logger.warning(f"Could not verify Celery configuration: {e}")


@app.task(bind=True, ignore_result=True)
def debug_task(self):
    print(f"Request: {self.request!r}")
 