# decorators.py
from typing import Callable
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi
from .serializers import ProtectPDFSerializer


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
            request_body=ProtectPDFSerializer,
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

