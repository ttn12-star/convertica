# decorators.py
from collections.abc import Callable

from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema


def generate_favicon_docs() -> Callable:
    """Swagger documentation for the Generate-Favicon API."""

    zip_binary_schema = openapi.Schema(
        type=openapi.TYPE_STRING,
        format="binary",
        description="ZIP archive with favicon assets.",
        example="(binary ZIP stream)",
    )

    def decorator(func: Callable) -> Callable:
        return swagger_auto_schema(
            operation_description=(
                "Generate a complete favicon package (ZIP) from one source "
                "image: favicon.ico, PNG icons, apple-touch-icon, "
                "android-chrome icons, site.webmanifest, and an HTML snippet."
            ),
            schema=None,
            manual_parameters=[
                openapi.Parameter(
                    "image_file",
                    openapi.IN_FORM,
                    description="Source image to build the favicon package from.",
                    type=openapi.TYPE_FILE,
                    required=True,
                ),
            ],
            request_body=None,
            responses={
                200: openapi.Response(
                    description="ZIP archive of favicon assets.",
                    schema=zip_binary_schema,
                ),
                400: "Bad request (invalid image, etc.).",
                413: "File too large.",
                500: "Internal server error.",
            },
            consumes=["multipart/form-data"],
        )(func)

    return decorator
