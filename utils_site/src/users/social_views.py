# pylint: skip-file
import logging

from django.http import JsonResponse
from django.shortcuts import redirect

logger = logging.getLogger(__name__)


def google_direct_oauth(request):
    """Direct redirect to Google OAuth using standard allauth flow"""
    if request.user.is_authenticated:
        return redirect("users:profile")

    # Use standard allauth OAuth flow - redirect to Google OAuth login URL
    return redirect("/accounts/google/login/")


def auth_status(request):
    """Check authentication status for seamless social auth"""
    if request.user.is_authenticated:
        return JsonResponse(
            {
                "authenticated": True,
                "user": {
                    "username": request.user.username,
                    "email": request.user.email,
                    "first_name": request.user.first_name,
                    "last_name": request.user.last_name,
                },
            }
        )
    else:
        return JsonResponse({"authenticated": False})
