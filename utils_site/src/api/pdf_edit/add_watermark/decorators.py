# decorators.py
from collections.abc import Callable

from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema


def add_watermark_docs() -> Callable:
    """Decorator providing Swagger documentation for add watermark API."""

    pdf_binary_schema = openapi.Schema(
        type=openapi.TYPE_STRING,
        format="binary",
        description="PDF file with watermark added.",
        example="(binary file stream)",
    )

    def decorator(func: Callable) -> Callable:
        return swagger_auto_schema(
            operation_description="Add text or image watermark to PDF pages. "
            "You can customize position, opacity, and font size.",
            auto_schema=None,  # Completely disable auto schema generation
            schema=None,  # Prevent auto-detection from serializer
            manual_parameters=[
                openapi.Parameter(
                    "pdf_file",
                    openapi.IN_FORM,
                    description="PDF file to add watermark to",
                    type=openapi.TYPE_FILE,
                    required=True,
                ),
                openapi.Parameter(
                    "watermark_text",
                    openapi.IN_FORM,
                    description="Text to use as watermark",
                    type=openapi.TYPE_STRING,
                    required=False,
                ),
                openapi.Parameter(
                    "watermark_file",
                    openapi.IN_FORM,
                    description="Image file to use as watermark (PNG, JPG). If provided, watermark_text is ignored",
                    type=openapi.TYPE_FILE,
                    required=False,
                ),
                openapi.Parameter(
                    "position",
                    openapi.IN_FORM,
                    description="Position of watermark (center or diagonal)",
                    type=openapi.TYPE_STRING,
                    required=False,
                ),
                openapi.Parameter(
                    "opacity",
                    openapi.IN_FORM,
                    description="Opacity of watermark (0.1-1.0)",
                    type=openapi.TYPE_NUMBER,
                    required=False,
                ),
                openapi.Parameter(
                    "font_size",
                    openapi.IN_FORM,
                    description="Font size for text watermark (12-200)",
                    type=openapi.TYPE_INTEGER,
                    required=False,
                ),
            ],
            request_body=None,  # Explicitly disable request body to avoid conflict with manual_parameters
            responses={
                200: openapi.Response(
                    description="PDF file with watermark.",
                    content={"application/pdf": pdf_binary_schema},
                ),
                400: "Bad request (invalid PDF, invalid parameters, etc.).",
                413: "File too large.",
                500: "Internal server error.",
            },
            consumes=["multipart/form-data"],
        )(func)

    return decorator
