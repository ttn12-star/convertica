# decorators.py
from typing import Callable
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi


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
            manual_parameters=[
                openapi.Parameter(
                    'pdf_files',
                    openapi.IN_FORM,
                    description="PDF files to merge (2-10 files). Can upload multiple files with the same field name.",
                    type=openapi.TYPE_FILE,
                    required=True,
                ),
                openapi.Parameter(
                    'order',
                    openapi.IN_FORM,
                    description="Merge order: 'upload' (as uploaded) or 'alphabetical'",
                    type=openapi.TYPE_STRING,
                    required=False,
                ),
            ],
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

