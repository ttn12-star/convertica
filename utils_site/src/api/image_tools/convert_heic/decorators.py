"""Swagger documentation for the HEIC Converter API (premium)."""

from collections.abc import Callable

from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema


def convert_heic_docs() -> Callable:
    """Decorator providing Swagger docs for the HEIC Converter endpoint."""

    binary_schema = openapi.Schema(
        type=openapi.TYPE_STRING,
        format="binary",
        description="Converted image file (JPG, PNG, or PDF).",
        example="(binary file stream)",
    )

    def decorator(func: Callable) -> Callable:
        return swagger_auto_schema(
            operation_description=(
                "Convert an Apple HEIC / HEIF photo to JPG, PNG, or PDF. "
                "Free for single files (subject to the daily quota); batch "
                "conversion is Premium. "
                "Common use: re-encode iPhone photos for compatibility with "
                "Windows, web, or print workflows."
            ),
            schema=None,
            manual_parameters=[
                openapi.Parameter(
                    "image_file",
                    openapi.IN_FORM,
                    description="HEIC or HEIF file to convert.",
                    type=openapi.TYPE_FILE,
                    required=True,
                ),
                openapi.Parameter(
                    "output_format",
                    openapi.IN_FORM,
                    description="Target format: JPEG (alias JPG), PNG, or PDF.",
                    type=openapi.TYPE_STRING,
                    required=False,
                    enum=["JPEG", "JPG", "PNG", "PDF"],
                    default="JPEG",
                ),
                openapi.Parameter(
                    "quality",
                    openapi.IN_FORM,
                    description="Quality for JPEG output (10-100, default 90).",
                    type=openapi.TYPE_INTEGER,
                    required=False,
                    default=90,
                ),
            ],
            request_body=None,
            responses={
                200: openapi.Response(
                    description="Converted file (image/jpeg, image/png, or application/pdf).",
                    schema=binary_schema,
                ),
                400: "Bad request (invalid or unsupported file).",
                403: "Premium subscription required.",
                413: "File too large.",
                500: "Internal server error.",
            },
            consumes=["multipart/form-data"],
        )(func)

    return decorator
