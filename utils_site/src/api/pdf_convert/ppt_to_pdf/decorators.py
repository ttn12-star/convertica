"""
Decorators for PowerPoint to PDF API documentation.
"""

from collections.abc import Callable

from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema


def ppt_to_pdf_docs() -> Callable:
    """Decorator providing Swagger documentation for PowerPoint to PDF API."""

    ppt_file_schema = openapi.Schema(
        type=openapi.TYPE_FILE,
        description="PowerPoint file (.ppt or .pptx) to convert to PDF",
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
        operation_summary="Convert PowerPoint to PDF",
        operation_description="Convert PowerPoint (.ppt and .pptx) files to PDF format using LibreOffice.",
        tags=["PowerPoint Conversion"],
        manual_parameters=[
            openapi.Parameter(
                "ppt",
                openapi.IN_FORM,
                type=openapi.TYPE_FILE,
                required=True,
                description="PowerPoint file to convert",
            ),
        ],
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                "ppt_file": ppt_file_schema,
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
