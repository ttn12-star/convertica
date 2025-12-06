# decorators.py
from typing import Callable
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi
from .serializers import RemovePagesSerializer


def remove_pages_docs() -> Callable:
    """Decorator providing Swagger documentation for remove pages API."""
    
    pdf_binary_schema = openapi.Schema(
        type=openapi.TYPE_STRING,
        format="binary",
        description="PDF file with pages removed.",
        example="(binary file stream)",
    )
    
    def decorator(func: Callable) -> Callable:
        return swagger_auto_schema(
            operation_description="Remove specific pages from PDF. "
                                 "Specify pages as comma-separated numbers or ranges.",
            request_body=RemovePagesSerializer,
            responses={
                200: openapi.Response(
                    description="PDF file with pages removed.",
                    content={"application/pdf": pdf_binary_schema},
                ),
                400: "Bad request (invalid PDF, invalid pages, etc.).",
                413: "File too large.",
                500: "Internal server error.",
            },
            consumes=["multipart/form-data"],
        )(func)
    
    return decorator

