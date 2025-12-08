# decorators.py
from typing import Callable

from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema


def rotate_pdf_docs() -> Callable:
    """Decorator providing Swagger documentation for PDF rotation API."""

    pdf_binary_schema = openapi.Schema(
        type=openapi.TYPE_STRING,
        format="binary",
        description="Rotated PDF file.",
        example="(binary file stream)",
    )

    def decorator(func: Callable) -> Callable:
        return swagger_auto_schema(
            operation_description="Rotate PDF pages by 90, 180, or 270 degrees. "
            "You can rotate all pages or specific pages.",
            schema=None,  # Prevent auto-detection from serializer
            manual_parameters=[
                openapi.Parameter(
                    "pdf_file",
                    openapi.IN_FORM,
                    description="PDF file to rotate",
                    type=openapi.TYPE_FILE,
                    required=True,
                ),
                openapi.Parameter(
                    "angle",
                    openapi.IN_FORM,
                    description="Rotation angle in degrees (90, 180, or 270)",
                    type=openapi.TYPE_INTEGER,
                    required=False,
                ),
                openapi.Parameter(
                    "pages",
                    openapi.IN_FORM,
                    description="Pages to rotate ('all' or comma-separated page numbers)",
                    type=openapi.TYPE_STRING,
                    required=False,
                ),
            ],
            request_body=None,  # Explicitly disable request body to avoid conflict with manual_parameters
            responses={
                200: openapi.Response(
                    description="Rotated PDF file.",
                    content={"application/pdf": pdf_binary_schema},
                ),
                400: "Bad request (invalid PDF, invalid angle, etc.).",
                413: "File too large.",
                500: "Internal server error.",
            },
            consumes=["multipart/form-data"],
        )(func)

    return decorator
