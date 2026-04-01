# decorators.py
from collections.abc import Callable

from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema


def optimize_image_docs() -> Callable:
    """Decorator providing Swagger documentation for the Image Optimizer API.

    Returns:
        Callable: Decorated DRF view method.
    """

    image_binary_schema = openapi.Schema(
        type=openapi.TYPE_STRING,
        format="binary",
        description="Optimized image file (JPEG, PNG, WebP, or GIF).",
        example="(binary image stream)",
    )

    def decorator(func: Callable) -> Callable:
        return swagger_auto_schema(
            operation_description=(
                "Optimize an image by compressing it to reduce file size. "
                "Supports JPEG, PNG, WebP, and GIF formats. "
                "Optionally convert to a different format or resize to fit within max dimensions."
            ),
            schema=None,
            manual_parameters=[
                openapi.Parameter(
                    "image_file",
                    openapi.IN_FORM,
                    description="Image file to optimize (JPEG, PNG, WebP, GIF).",
                    type=openapi.TYPE_FILE,
                    required=True,
                ),
                openapi.Parameter(
                    "quality",
                    openapi.IN_FORM,
                    description="Compression quality (10-100, default 85).",
                    type=openapi.TYPE_INTEGER,
                    required=False,
                    default=85,
                ),
                openapi.Parameter(
                    "output_format",
                    openapi.IN_FORM,
                    description="Output format: '' (keep original), 'JPEG', 'PNG', or 'WebP'.",
                    type=openapi.TYPE_STRING,
                    required=False,
                    default="",
                ),
                openapi.Parameter(
                    "max_width",
                    openapi.IN_FORM,
                    description="Maximum output width in pixels (optional, maintains aspect ratio).",
                    type=openapi.TYPE_INTEGER,
                    required=False,
                ),
                openapi.Parameter(
                    "max_height",
                    openapi.IN_FORM,
                    description="Maximum output height in pixels (optional, maintains aspect ratio).",
                    type=openapi.TYPE_INTEGER,
                    required=False,
                ),
            ],
            request_body=None,
            responses={
                200: openapi.Response(
                    description="Optimized image file.",
                    content={"image/*": image_binary_schema},
                ),
                400: "Bad request (invalid image, unsupported format, etc.).",
                413: "File too large.",
                500: "Internal server error.",
            },
            consumes=["multipart/form-data"],
        )(func)

    return decorator
