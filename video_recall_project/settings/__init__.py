# Settings package - import base settings for development
import os

from .base import *

# Development settings - Override base settings for development
# Only set DEBUG=True if explicitly enabled (safer default)
DEBUG = os.environ.get("DEBUG", "True").lower() in ("true", "1", "yes", "on")
SECRET_KEY = os.environ.get(
    "SECRET_KEY", "django-insecure-dev-key-change-in-production"
)
# Allow all hosts in development, but warn if DEBUG=True with wildcard
ALLOWED_HOSTS = os.environ.get("ALLOWED_HOSTS", "localhost,127.0.0.1,*").split(",")

# Override CORS for development - more permissive
CORS_ALLOW_ALL_ORIGINS = os.environ.get("CORS_ALLOW_ALL_ORIGINS", "True").lower() in (
    "true",
    "1",
    "yes",
    "on",
)

# Warn if insecure configuration detected
if DEBUG and "*" in ALLOWED_HOSTS:
    import logging

    logger = logging.getLogger(__name__)
    logger.warning(
        'DEBUG=True with ALLOWED_HOSTS=["*"] is insecure. Use only in development.'
    )

# Login/Logout redirects - Development specific
LOGIN_REDIRECT_URL = "/library/"
LOGOUT_REDIRECT_URL = "/"
