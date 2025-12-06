# decorators.py
from typing import Callable
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi


def compress_pdf_docs() -> Callable:
    """Decorator providing Swagger documentation for compress PDF API."""
    
    pdf_binary_schema = openapi.Schema(
        type=openapi.TYPE_STRING,
        format="binary",
        description="Compressed PDF file.",
        example="(binary file stream)",
    )
    
    def decorator(func: Callable) -> Callable:
        return swagger_auto_schema(
            operation_description="Compress PDF to reduce file size. "
                                 "Choose compression level: low (faster, less compression), "
                                 "medium (balanced), or high (slower, more compression).",
            manual_parameters=[
                openapi.Parameter(
                    'pdf_file',
                    openapi.IN_FORM,
                    description="PDF file to compress",
                    type=openapi.TYPE_FILE,
                    required=True,
                ),
                openapi.Parameter(
                    'compression_level',
                    openapi.IN_FORM,
                    description="Compression level (low, medium, or high)",
                    type=openapi.TYPE_STRING,
                    required=False,
                ),
            ],
            responses={
                200: openapi.Response(
                    description="Compressed PDF file.",
                    content={"application/pdf": pdf_binary_schema},
                ),
                400: "Bad request (invalid PDF, etc.).",
                413: "File too large.",
                500: "Internal server error.",
            },
            consumes=["multipart/form-data"],
        )(func)
    
    return decorator

