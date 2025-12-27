"""
Examples of using combined rate limiting in API views.
This file shows how to apply rate limits to different types of endpoints.
"""

from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from .rate_limit_utils import combined_rate_limit


# Example 1: Standard conversion endpoint
class PDFToWordAPIView(APIView):
    """
    PDF to Word conversion with combined rate limiting.

    Rate limits:
    - IP: 100 requests/hour (prevents IP-based abuse)
    - Anonymous: 100 requests/hour
    - Authenticated: 1,000 requests/hour
    - Premium: 10,000 requests/hour
    """

    @combined_rate_limit(group="api_conversion", ip_rate="100/h", methods=["POST"])
    def post(self, request):
        # Your conversion logic here
        return Response({"status": "success"})


# Example 2: Batch conversion endpoint (stricter limits)
class PDFToWordBatchAPIView(APIView):
    """
    Batch PDF to Word conversion with strict rate limiting.

    Rate limits:
    - IP: 10 requests/hour (batch is resource-intensive)
    - Anonymous: 0 requests/hour (not allowed)
    - Authenticated: 50 requests/hour
    - Premium: 500 requests/hour
    """

    @combined_rate_limit(group="api_batch", ip_rate="10/h", methods=["POST"])
    def post(self, request):
        # Check if user is authenticated (batch requires auth)
        if not request.user.is_authenticated:
            return Response(
                {"error": "Batch operations require authentication"},
                status=status.HTTP_401_UNAUTHORIZED,
            )

        # Your batch conversion logic here
        return Response({"status": "success"})


# Example 3: Authentication endpoints (very strict)
class LoginAPIView(APIView):
    """
    Login endpoint with strict rate limiting to prevent brute force.

    Rate limits:
    - IP: 10 requests/hour (prevents brute force from single IP)
    - User: 20 requests/hour (prevents credential stuffing)
    """

    @combined_rate_limit(group="api_auth", ip_rate="10/h", methods=["POST"])
    def post(self, request):
        # Your login logic here
        return Response({"status": "success"})


# Example 4: Public API endpoint (moderate limits)
class ToolsListAPIView(APIView):
    """
    Public tools list endpoint with moderate rate limiting.

    Rate limits:
    - IP: 200 requests/hour
    - User: 500-5000 requests/hour (based on premium status)
    """

    @combined_rate_limit(group="api_other", ip_rate="200/h", methods=["GET"])
    def get(self, request):
        # Your tools list logic here
        return Response({"tools": []})


# Example 5: Using in function-based views
from django.http import JsonResponse


@combined_rate_limit(group="api_conversion", ip_rate="100/h", methods=["POST"])
def pdf_to_word_view(request):
    """Function-based view with rate limiting."""
    if request.method == "POST":
        # Your conversion logic here
        return JsonResponse({"status": "success"})
    return JsonResponse({"error": "Method not allowed"}, status=405)


# Example 6: Multiple methods with different limits
class FileUploadAPIView(APIView):
    """
    File upload endpoint with different limits for different methods.
    """

    # GET requests (checking status) - more lenient
    @combined_rate_limit(group="api_other", ip_rate="200/h", methods=["GET"])
    def get(self, request):
        return Response({"status": "ready"})

    # POST requests (uploading) - stricter
    @combined_rate_limit(group="api_conversion", ip_rate="100/h", methods=["POST"])
    def post(self, request):
        return Response({"status": "uploaded"})


from django.core.exceptions import PermissionDenied

# Example 7: Custom rate limit handling
from django_ratelimit.exceptions import Ratelimited


class CustomRateLimitView(APIView):
    """
    View with custom rate limit error handling.
    """

    @combined_rate_limit(group="api_conversion", ip_rate="100/h", methods=["POST"])
    def post(self, request):
        try:
            # Your logic here
            return Response({"status": "success"})
        except Ratelimited as e:
            # Custom handling
            return Response(
                {
                    "error": "Rate limit exceeded",
                    "message": "Please upgrade to Premium for higher limits",
                    "upgrade_url": "/premium/",
                },
                status=status.HTTP_429_TOO_MANY_REQUESTS,
            )
