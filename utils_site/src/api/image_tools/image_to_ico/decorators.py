# decorators.py
from collections.abc import Callable

from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema


def image_to_ico_docs() -> Callable:
    """Swagger documentation for the Image-to-ICO API."""

    ico_binary_schema = openapi.Schema(
        type=openapi.TYPE_STRING,
        format="binary",
        description="Multi-resolution Windows .ico file.",
        example="(binary ICO stream)",
    )

    def decorator(func: Callable) -> Callable:
        return swagger_auto_schema(
            operation_description=(
                "Convert an image (PNG, JPEG, WebP, GIF, BMP, TIFF, or SVG) "
                "into a multi-resolution Windows .ico favicon."
            ),
            schema=None,
            manual_parameters=[
                openapi.Parameter(
                    "image_file",
                    openapi.IN_FORM,
                    description="Source image to convert.",
                    type=openapi.TYPE_FILE,
                    required=True,
                ),
                openapi.Parameter(
                    "sizes",
                    openapi.IN_FORM,
                    description=(
                        "Comma-separated square sizes to embed. "
                        "Allowed: 16, 24, 32, 48, 64, 128, 256. Default 16,32,48."
                    ),
                    type=openapi.TYPE_STRING,
                    required=False,
                    default="16,32,48",
                ),
            ],
            request_body=None,
            responses={
                200: openapi.Response(
                    description="Generated .ico file.",
                    content={"image/x-icon": ico_binary_schema},
                ),
                400: "Bad request (invalid image, no valid sizes, etc.).",
                413: "File too large.",
                500: "Internal server error.",
            },
            consumes=["multipart/form-data"],
        )(func)

    return decorator
