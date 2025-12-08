# decorators.py
from typing import Callable

from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema


def unlock_pdf_docs() -> Callable:
    """Decorator providing Swagger documentation for unlock PDF API."""

    pdf_binary_schema = openapi.Schema(
        type=openapi.TYPE_STRING,
        format="binary",
        description="Unlocked PDF file (password removed).",
        example="(binary file stream)",
    )

    def decorator(func: Callable) -> Callable:
        return swagger_auto_schema(
            operation_description="Unlock PDF by removing password protection. "
            "Requires the correct password to unlock the PDF.",
            schema=None,  # Prevent auto-detection from serializer
            manual_parameters=[
                openapi.Parameter(
                    "pdf_file",
                    openapi.IN_FORM,
                    description="Password-protected PDF file to unlock",
                    type=openapi.TYPE_FILE,
                    required=True,
                ),
                openapi.Parameter(
                    "password",
                    openapi.IN_FORM,
                    description="Password to unlock the PDF",
                    type=openapi.TYPE_STRING,
                    required=True,
                ),
            ],
            request_body=None,  # Explicitly disable request body to avoid conflict with manual_parameters
            responses={
                200: openapi.Response(
                    description="Unlocked PDF file (no password required).",
                    content={"application/pdf": pdf_binary_schema},
                ),
                400: "Bad request (invalid PDF, incorrect password, etc.).",
                413: "File too large.",
                500: "Internal server error.",
            },
            consumes=["multipart/form-data"],
        )(func)

    return decorator
