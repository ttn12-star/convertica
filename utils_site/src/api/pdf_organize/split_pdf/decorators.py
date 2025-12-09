# decorators.py
from collections.abc import Callable

from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema


def split_pdf_docs() -> Callable:
    """Decorator providing Swagger documentation for PDF split API."""

    zip_binary_schema = openapi.Schema(
        type=openapi.TYPE_STRING,
        format="binary",
        description="ZIP file containing split PDF files.",
        example="(binary file stream)",
    )

    def decorator(func: Callable) -> Callable:
        return swagger_auto_schema(
            operation_description="Split PDF into multiple files. "
            "You can split by individual pages, page ranges, or every N pages.",
            schema=None,  # Prevent auto-detection from serializer
            manual_parameters=[
                openapi.Parameter(
                    "pdf_file",
                    openapi.IN_FORM,
                    description="PDF file to split",
                    type=openapi.TYPE_FILE,
                    required=True,
                ),
                openapi.Parameter(
                    "split_type",
                    openapi.IN_FORM,
                    description="Split type: 'page' (one page per file), 'range' (by page ranges), 'every_n' (every N pages)",
                    type=openapi.TYPE_STRING,
                    required=False,
                ),
                openapi.Parameter(
                    "pages",
                    openapi.IN_FORM,
                    description=(
                        "For 'page': comma-separated page numbers. "
                        "For 'range': ranges like '1-3,5-7'. "
                        "For 'every_n': number of pages per file"
                    ),
                    type=openapi.TYPE_STRING,
                    required=False,
                ),
            ],
            request_body=None,  # Explicitly disable request body to avoid conflict with manual_parameters
            responses={
                200: openapi.Response(
                    description="ZIP file containing split PDF files.",
                    content={"application/zip": zip_binary_schema},
                ),
                400: "Bad request (invalid PDF, invalid parameters, etc.).",
                413: "File too large.",
                500: "Internal server error.",
            },
            consumes=["multipart/form-data"],
        )(func)

    return decorator
