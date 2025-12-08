# decorators.py
from typing import Callable

from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema


def add_page_numbers_docs() -> Callable:
    """Decorator providing Swagger documentation for add page numbers API."""

    pdf_binary_schema = openapi.Schema(
        type=openapi.TYPE_STRING,
        format="binary",
        description="PDF file with page numbers added.",
        example="(binary file stream)",
    )

    def decorator(func: Callable) -> Callable:
        return swagger_auto_schema(
            operation_description="Add page numbers to PDF pages. "
            "You can customize position, font size, starting number, and format.",
            schema=None,  # Prevent auto-detection from serializer
            manual_parameters=[
                openapi.Parameter(
                    "pdf_file",
                    openapi.IN_FORM,
                    description="PDF file to add page numbers to",
                    type=openapi.TYPE_FILE,
                    required=True,
                ),
                openapi.Parameter(
                    "position",
                    openapi.IN_FORM,
                    description="Position of page numbers (bottom-center, bottom-left, bottom-right, top-center, top-left, top-right)",
                    type=openapi.TYPE_STRING,
                    required=False,
                ),
                openapi.Parameter(
                    "font_size",
                    openapi.IN_FORM,
                    description="Font size for page numbers (8-72)",
                    type=openapi.TYPE_INTEGER,
                    required=False,
                ),
                openapi.Parameter(
                    "start_number",
                    openapi.IN_FORM,
                    description="Starting page number",
                    type=openapi.TYPE_INTEGER,
                    required=False,
                ),
                openapi.Parameter(
                    "format_str",
                    openapi.IN_FORM,
                    description="Format string for page numbers (use {page} for page number, {total} for total pages)",
                    type=openapi.TYPE_STRING,
                    required=False,
                ),
            ],
            request_body=None,  # Explicitly disable request body to avoid conflict with manual_parameters
            responses={
                200: openapi.Response(
                    description="PDF file with page numbers.",
                    content={"application/pdf": pdf_binary_schema},
                ),
                400: "Bad request (invalid PDF, invalid parameters, etc.).",
                413: "File too large.",
                500: "Internal server error.",
            },
            consumes=["multipart/form-data"],
        )(func)

    return decorator
