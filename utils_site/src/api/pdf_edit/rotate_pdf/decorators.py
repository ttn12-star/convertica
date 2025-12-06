# decorators.py
from typing import Callable
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi
from .serializers import RotatePDFSerializer


def rotate_pdf_docs() -> Callable:
    """Decorator providing Swagger documentation for PDF rotation API."""
    
    pdf_binary_schema = openapi.Schema(
        type=openapi.TYPE_STRING,
        format="binary",
        description="Rotated PDF file.",
        example="(binary file stream)",
    )
    
    def decorator(func: Callable) -> Callable:
        return swagger_auto_schema(
            operation_description="Rotate PDF pages by 90, 180, or 270 degrees. "
                                 "You can rotate all pages or specific pages.",
            request_body=RotatePDFSerializer,
            responses={
                200: openapi.Response(
                    description="Rotated PDF file.",
                    content={
                        "application/pdf": pdf_binary_schema
                    },
                ),
                400: "Bad request (invalid PDF, invalid angle, etc.).",
                413: "File too large.",
                500: "Internal server error.",
            },
            consumes=["multipart/form-data"],
        )(func)
    
    return decorator

