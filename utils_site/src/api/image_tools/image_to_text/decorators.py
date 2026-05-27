# decorators.py
from collections.abc import Callable

from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema


def image_to_text_docs() -> Callable:
    """Swagger documentation for the Image to Text (OCR) API."""

    def decorator(func: Callable) -> Callable:
        return swagger_auto_schema(
            operation_description=(
                "Extract text from an image using OCR. Supported input: JPEG, PNG, "
                "WebP, HEIC/HEIF, BMP, TIFF, GIF. Returns the extracted text as a "
                "UTF-8 text/plain file."
            ),
            schema=None,
            manual_parameters=[
                openapi.Parameter(
                    "image_file",
                    openapi.IN_FORM,
                    description="Image file to extract text from.",
                    type=openapi.TYPE_FILE,
                    required=True,
                ),
                openapi.Parameter(
                    "language",
                    openapi.IN_FORM,
                    description="OCR language (site code, e.g. 'en', 'ru') or 'auto'.",
                    type=openapi.TYPE_STRING,
                    required=False,
                    default="auto",
                ),
                openapi.Parameter(
                    "confidence_threshold",
                    openapi.IN_FORM,
                    description="Minimum per-word confidence to keep (0-100, default 60).",
                    type=openapi.TYPE_INTEGER,
                    required=False,
                    default=60,
                ),
            ],
            request_body=None,
            responses={
                200: openapi.Response(description="Extracted text (text/plain)."),
                400: "Bad request (invalid or unsupported image).",
                413: "File too large.",
                500: "Internal server error.",
            },
            consumes=["multipart/form-data"],
        )(func)

    return decorator
