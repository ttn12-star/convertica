# decorators.py
from typing import Callable

from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema


def protect_pdf_docs() -> Callable:
    """Decorator providing Swagger documentation for protect PDF API."""

    pdf_binary_schema = openapi.Schema(
        type=openapi.TYPE_STRING,
        format="binary",
        description="Password-protected PDF file.",
        example="(binary file stream)",
    )

    def decorator(func: Callable) -> Callable:
        return swagger_auto_schema(
            operation_description="Protect PDF with password encryption. "
            "The PDF will be encrypted and require a password to open.",
            schema=None,  # Prevent auto-detection from serializer
            manual_parameters=[
                openapi.Parameter(
                    "pdf_file",
                    openapi.IN_FORM,
                    description="PDF file to protect",
                    type=openapi.TYPE_FILE,
                    required=True,
                ),
                openapi.Parameter(
                    "password",
                    openapi.IN_FORM,
                    description="Password to protect the PDF",
                    type=openapi.TYPE_STRING,
                    required=True,
                ),
                openapi.Parameter(
                    "user_password",
                    openapi.IN_FORM,
                    description="User password (optional). If not provided, 'password' will be used",
                    type=openapi.TYPE_STRING,
                    required=False,
                ),
                openapi.Parameter(
                    "owner_password",
                    openapi.IN_FORM,
                    description="Owner password (optional). If not provided, 'password' will be used",
                    type=openapi.TYPE_STRING,
                    required=False,
                ),
            ],
            request_body=None,  # Explicitly disable request body to avoid conflict with manual_parameters
            responses={
                200: openapi.Response(
                    description="Password-protected PDF file.",
                    content={"application/pdf": pdf_binary_schema},
                ),
                400: "Bad request (invalid PDF, weak password, etc.).",
                413: "File too large.",
                500: "Internal server error.",
            },
            consumes=["multipart/form-data"],
        )(func)

    return decorator
