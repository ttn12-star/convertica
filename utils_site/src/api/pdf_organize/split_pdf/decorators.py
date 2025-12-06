# decorators.py
from typing import Callable
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi
from .serializers import SplitPDFSerializer


def split_pdf_docs() -> Callable:
    """Decorator providing Swagger documentation for PDF split API."""
    
    zip_binary_schema = openapi.Schema(
        type=openapi.TYPE_STRING,
        format="binary",
        description="ZIP file containing split PDF files.",
        example="(binary file stream)",
    )
    
    def decorator(func: Callable) -> Callable:
        return swagger_auto_schema(
            operation_description="Split PDF into multiple files. "
                                 "You can split by individual pages, page ranges, or every N pages.",
            request_body=SplitPDFSerializer,
            responses={
                200: openapi.Response(
                    description="ZIP file containing split PDF files.",
                    content={"application/zip": zip_binary_schema},
                ),
                400: "Bad request (invalid PDF, invalid parameters, etc.).",
                413: "File too large.",
                500: "Internal server error.",
            },
            consumes=["multipart/form-data"],
        )(func)
    
    return decorator

