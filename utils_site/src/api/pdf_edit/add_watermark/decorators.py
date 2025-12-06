# decorators.py
from typing import Callable
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi
from .serializers import AddWatermarkSerializer


def add_watermark_docs() -> Callable:
    """Decorator providing Swagger documentation for add watermark API."""
    
    pdf_binary_schema = openapi.Schema(
        type=openapi.TYPE_STRING,
        format="binary",
        description="PDF file with watermark added.",
        example="(binary file stream)",
    )
    
    def decorator(func: Callable) -> Callable:
        return swagger_auto_schema(
            operation_description="Add text or image watermark to PDF pages. "
                                 "You can customize position, opacity, and font size.",
            request_body=AddWatermarkSerializer,
            responses={
                200: openapi.Response(
                    description="PDF file with watermark.",
                    content={"application/pdf": pdf_binary_schema},
                ),
                400: "Bad request (invalid PDF, invalid parameters, etc.).",
                413: "File too large.",
                500: "Internal server error.",
            },
            consumes=["multipart/form-data"],
        )(func)
    
    return decorator

