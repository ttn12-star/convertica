# decorators.py
from collections.abc import Callable

from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema


def crop_pdf_docs() -> Callable:
    """Decorator providing Swagger documentation for PDF crop API."""

    pdf_binary_schema = openapi.Schema(
        type=openapi.TYPE_STRING,
        format="binary",
        description="Cropped PDF file.",
        example="(binary file stream)",
    )

    def decorator(func: Callable) -> Callable:
        return swagger_auto_schema(
            operation_description="Crop PDF pages by specifying crop box coordinates. "
            "You can crop all pages or specific pages.",
            schema=None,  # Prevent auto-detection from serializer
            manual_parameters=[
                openapi.Parameter(
                    "pdf_file",
                    openapi.IN_FORM,
                    description="PDF file to crop",
                    type=openapi.TYPE_FILE,
                    required=True,
                ),
                openapi.Parameter(
                    "x",
                    openapi.IN_FORM,
                    description="X coordinate of crop box (left edge in points)",
                    type=openapi.TYPE_NUMBER,
                    required=False,
                ),
                openapi.Parameter(
                    "y",
                    openapi.IN_FORM,
                    description="Y coordinate of crop box (bottom edge in points)",
                    type=openapi.TYPE_NUMBER,
                    required=False,
                ),
                openapi.Parameter(
                    "width",
                    openapi.IN_FORM,
                    description="Width of crop box in points",
                    type=openapi.TYPE_NUMBER,
                    required=False,
                ),
                openapi.Parameter(
                    "height",
                    openapi.IN_FORM,
                    description="Height of crop box in points",
                    type=openapi.TYPE_NUMBER,
                    required=False,
                ),
                openapi.Parameter(
                    "pages",
                    openapi.IN_FORM,
                    description="Pages to crop ('all' or comma-separated page numbers)",
                    type=openapi.TYPE_STRING,
                    required=False,
                ),
            ],
            request_body=None,  # Explicitly disable request body to avoid conflict with manual_parameters
            responses={
                200: openapi.Response(
                    description="Cropped PDF file.",
                    content={"application/pdf": pdf_binary_schema},
                ),
                400: "Bad request (invalid PDF, invalid coordinates, etc.).",
                413: "File too large.",
                500: "Internal server error.",
            },
            consumes=["multipart/form-data"],
        )(func)

    return decorator
