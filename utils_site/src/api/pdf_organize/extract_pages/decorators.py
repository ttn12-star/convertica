# decorators.py
from typing import Callable
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi
from .serializers import ExtractPagesSerializer


def extract_pages_docs() -> Callable:
    """Decorator providing Swagger documentation for extract pages API."""
    
    pdf_binary_schema = openapi.Schema(
        type=openapi.TYPE_STRING,
        format="binary",
        description="PDF file with extracted pages.",
        example="(binary file stream)",
    )
    
    def decorator(func: Callable) -> Callable:
        return swagger_auto_schema(
            operation_description="Extract specific pages from PDF into a new file. "
                                 "Specify pages as comma-separated numbers or ranges.",
            request_body=ExtractPagesSerializer,
            responses={
                200: openapi.Response(
                    description="PDF file with extracted pages.",
                    content={"application/pdf": pdf_binary_schema},
                ),
                400: "Bad request (invalid PDF, invalid pages, etc.).",
                413: "File too large.",
                500: "Internal server error.",
            },
            consumes=["multipart/form-data"],
        )(func)
    
    return decorator

