"""
Decorators for Excel to PDF API documentation.
"""

from collections.abc import Callable

from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema


def excel_to_pdf_docs() -> Callable:
    """Decorator providing Swagger documentation for Excel to PDF API."""

    excel_file_schema = openapi.Schema(
        type=openapi.TYPE_FILE,
        description="Excel file (.xls or .xlsx) to convert to PDF",
    )

    response_schema = openapi.Schema(
        type=openapi.TYPE_OBJECT,
        properties={
            "success": openapi.Schema(
                type=openapi.TYPE_BOOLEAN,
                description="Whether the conversion was successful",
            ),
            "message": openapi.Schema(
                type=openapi.TYPE_STRING,
                description="Success or error message",
            ),
            "download_url": openapi.Schema(
                type=openapi.TYPE_STRING,
                description="URL to download the converted PDF",
            ),
            "task_id": openapi.Schema(
                type=openapi.TYPE_STRING,
                description="Task ID for async conversion tracking",
            ),
        },
    )

    return swagger_auto_schema(
        operation_summary="Convert Excel to PDF",
        operation_description="Convert Excel (.xls Northern .xlsx) files to PDF format using LibreOffice.",
        tags=["Excel Conversion"],
        manual_parameters=[
            openapi.Parameter(
                "excel",
                openapi.IN_FORM,
                type=openapi.TYPE_FILE,
                required=True,
                description="Excel file to convert",
            ),
        ],
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                "excel_file": excel_file_schema,
            },
        ),
        responses={
            200: openapi.Response(
                description="Conversion successful",
                schema=response_schema,
            ),
            400: openapi.Response(
                description="Bad request - invalid file or parameters",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        "error": openapi.Schema(
                            type=openapi.TYPE_STRING,
                            description="Error message",
                        ),
                    },
                ),
            ),
            413: openapi.Response(
                description="File too large",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        "error": openapi.Schema(
                            type=openapi.TYPE_STRING,
                            description="Error message",
                        ),
                    },
                ),
            ),
            500: openapi.Response(
                description="Internal server error",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        "error": openapi.Schema(
                            type=openapi.TYPE_STRING,
                            description="Error message",
                        ),
                    },
                ),
            ),
        },
    )
