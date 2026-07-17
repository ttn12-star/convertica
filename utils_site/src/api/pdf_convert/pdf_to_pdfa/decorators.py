# decorators.py
from collections.abc import Callable

from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema


def pdf_to_pdfa_docs() -> Callable:
    """Decorator providing Swagger documentation for the PDF to PDF/A API."""

    pdf_binary_schema = openapi.Schema(
        type=openapi.TYPE_STRING,
        format="binary",
        description="Converted PDF/A file.",
        example="(binary file stream)",
    )

    def decorator(func: Callable) -> Callable:
        return swagger_auto_schema(
            operation_description=(
                "Convert a PDF to archival PDF/A (ISO 19005). Premium feature. "
                "Choose the conformance level: pdfa-1b, pdfa-2b (default), or pdfa-3b."
            ),
            schema=None,
            manual_parameters=[
                openapi.Parameter(
                    "pdf_file",
                    openapi.IN_FORM,
                    description="PDF file to convert to PDF/A",
                    type=openapi.TYPE_FILE,
                    required=True,
                ),
                openapi.Parameter(
                    "conformance",
                    openapi.IN_FORM,
                    description="PDF/A level: pdfa-1b, pdfa-2b, or pdfa-3b",
                    type=openapi.TYPE_STRING,
                    required=False,
                ),
            ],
            request_body=None,
            responses={
                200: openapi.Response(
                    description="Converted PDF/A file.",
                    content={"application/pdf": pdf_binary_schema},
                ),
                400: "Bad request (invalid or encrypted PDF, non-conformant output).",
                403: "Premium subscription required.",
                413: "File too large.",
                500: "Internal server error.",
            },
            consumes=["multipart/form-data"],
        )(func)

    return decorator
