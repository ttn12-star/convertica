# decorators.py
from collections.abc import Callable

from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema


def convert_image_docs() -> Callable:
    """Decorator providing Swagger documentation for the Image Converter API.

    Returns:
        Callable: Decorated DRF view method.
    """

    image_binary_schema = openapi.Schema(
        type=openapi.TYPE_STRING,
        format="binary",
        description="Converted image file in the requested format.",
        example="(binary image stream)",
    )

    def decorator(func: Callable) -> Callable:
        return swagger_auto_schema(
            operation_description=(
                "Convert an image to a different format. "
                "Supported input formats: JPEG, PNG, WebP, GIF, BMP, TIFF. "
                "Supported output formats: JPEG, PNG, WebP, GIF, BMP, TIFF. "
                "Alpha channel is handled automatically for formats that do not support it."
            ),
            schema=None,
            manual_parameters=[
                openapi.Parameter(
                    "image_file",
                    openapi.IN_FORM,
                    description="Image file to convert.",
                    type=openapi.TYPE_FILE,
                    required=True,
                ),
                openapi.Parameter(
                    "output_format",
                    openapi.IN_FORM,
                    description="Target format: JPEG, PNG, WebP, GIF, BMP, or TIFF.",
                    type=openapi.TYPE_STRING,
                    required=True,
                    enum=["JPEG", "PNG", "WebP", "GIF", "BMP", "TIFF"],
                ),
                openapi.Parameter(
                    "quality",
                    openapi.IN_FORM,
                    description="Quality for lossy formats (JPEG, WebP) — 10-100, default 90.",
                    type=openapi.TYPE_INTEGER,
                    required=False,
                    default=90,
                ),
            ],
            request_body=None,
            responses={
                200: openapi.Response(
                    description="Converted image file.",
                    content={"image/*": image_binary_schema},
                ),
                400: "Bad request (invalid image, unsupported format, etc.).",
                413: "File too large.",
                500: "Internal server error.",
            },
            consumes=["multipart/form-data"],
        )(func)

    return decorator
