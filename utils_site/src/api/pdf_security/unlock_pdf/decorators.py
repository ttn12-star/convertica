# decorators.py
from typing import Callable
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi
from .serializers import UnlockPDFSerializer


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
            request_body=UnlockPDFSerializer,
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

