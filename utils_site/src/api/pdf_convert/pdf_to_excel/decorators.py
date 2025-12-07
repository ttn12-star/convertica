# decorators.py
from typing import Callable

from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema


def pdf_to_excel_docs() -> Callable:
    """Decorator providing Swagger documentation for PDF to Excel API."""

    excel_binary_schema = openapi.Schema(
        type=openapi.TYPE_STRING,
        format="binary",
        description="Excel file (.xlsx) with extracted tables from PDF.",
        example="(binary file stream)",
    )

    def decorator(func: Callable) -> Callable:
        return swagger_auto_schema(
            operation_description="Convert PDF to Excel by extracting tables. "
            "The PDF must contain tables for this conversion to work. "
            "Each table will be placed in a separate sheet.",
            manual_parameters=[
                openapi.Parameter(
                    "pdf_file",
                    openapi.IN_FORM,
                    description="PDF file with tables to convert",
                    type=openapi.TYPE_FILE,
                    required=True,
                ),
                openapi.Parameter(
                    "pages",
                    openapi.IN_FORM,
                    description="Pages to extract (comma-separated, ranges, or 'all')",
                    type=openapi.TYPE_STRING,
                    required=False,
                ),
            ],
            responses={
                200: openapi.Response(
                    description="Excel file (.xlsx) with extracted tables.",
                    content={
                        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet": excel_binary_schema
                    },
                ),
                400: "Bad request (invalid PDF, no tables found, etc.).",
                413: "File too large.",
                500: "Internal server error.",
            },
            consumes=["multipart/form-data"],
        )(func)

    return decorator
