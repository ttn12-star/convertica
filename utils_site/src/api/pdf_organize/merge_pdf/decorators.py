# decorators.py
from typing import Callable
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi
from .serializers import MergePDFSerializer


def merge_pdf_docs() -> Callable:
    """Decorator providing Swagger documentation for PDF merge API."""
    
    pdf_binary_schema = openapi.Schema(
        type=openapi.TYPE_STRING,
        format="binary",
        description="Merged PDF file.",
        example="(binary file stream)",
    )
    
    def decorator(func: Callable) -> Callable:
        return swagger_auto_schema(
            operation_description="Merge multiple PDF files into one. "
                                 "Upload 2-10 PDF files to merge them in order.",
            request_body=MergePDFSerializer,
            responses={
                200: openapi.Response(
                    description="Merged PDF file.",
                    content={"application/pdf": pdf_binary_schema},
                ),
                400: "Bad request (invalid PDFs, too few/many files, etc.).",
                413: "File too large.",
                500: "Internal server error.",
            },
            consumes=["multipart/form-data"],
        )(func)
    
    return decorator

