"""Swagger documentation decorators for PDF compare API."""

from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema


def compare_pdf_docs():
    """Swagger docs for visual PDF comparison endpoint."""
    return swagger_auto_schema(
        operation_description=(
            "Compare two PDF files and generate a visual diff package with a detailed report."
        ),
        operation_summary="Compare Two PDFs",
        tags=["PDF Comparison"],
        manual_parameters=[
            openapi.Parameter(
                "pdf_file_1",
                openapi.IN_FORM,
                description="Base PDF file",
                type=openapi.TYPE_FILE,
                required=True,
            ),
            openapi.Parameter(
                "pdf_file_2",
                openapi.IN_FORM,
                description="Second PDF file to compare",
                type=openapi.TYPE_FILE,
                required=True,
            ),
            openapi.Parameter(
                "diff_threshold",
                openapi.IN_FORM,
                description=(
                    "Visual diff sensitivity threshold from 5 to 80 "
                    "(lower value = more sensitive)"
                ),
                type=openapi.TYPE_INTEGER,
                default=32,
            ),
        ],
        responses={
            200: openapi.Response(
                description="ZIP archive with visual diffs and reports",
                schema=openapi.Schema(type=openapi.TYPE_FILE),
            ),
            400: "Bad request",
            403: "Premium subscription required",
            413: "File too large",
            500: "Comparison failed",
        },
    )
