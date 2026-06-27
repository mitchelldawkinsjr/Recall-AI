"""
Custom middleware for production deployment
Handles ALB health checks and other production-specific requirements
"""

import logging
import re

logger = logging.getLogger(__name__)

# Private IP ranges used by AWS ALB for health checks
PRIVATE_IP_PATTERNS = [
    re.compile(r"^172\.(1[6-9]|2[0-9]|3[0-1])\..*"),  # 172.16.0.0/12
    re.compile(r"^10\..*"),  # 10.0.0.0/8
    re.compile(r"^192\.168\..*"),  # 192.168.0.0/16
]


class AllowPrivateIPsMiddleware:
    """
    Middleware to allow private IP addresses in Host header for ALB health checks.
    This is safe because ALB validates requests before forwarding them.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Check if Host header is a private IP (used by ALB health checks)
        host = request.get_host().split(":")[0]  # Remove port if present

        # If it's a private IP, temporarily add it to ALLOWED_HOSTS
        if any(pattern.match(host) for pattern in PRIVATE_IP_PATTERNS):
            from django.conf import settings

            # Temporarily allow this host
            if host not in settings.ALLOWED_HOSTS:
                settings.ALLOWED_HOSTS.append(host)
                logger.debug(
                    f"Temporarily allowing private IP for ALB health check: {host}"
                )

        response = self.get_response(request)
        return response
