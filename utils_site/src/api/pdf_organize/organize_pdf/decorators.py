# decorators.py
from typing import Callable
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi
from .serializers import OrganizePDFSerializer


def organize_pdf_docs() -> Callable:
    """Decorator providing Swagger documentation for organize PDF API."""
    
    pdf_binary_schema = openapi.Schema(
        type=openapi.TYPE_STRING,
        format="binary",
        description="Organized PDF file.",
        example="(binary file stream)",
    )
    
    def decorator(func: Callable) -> Callable:
        return swagger_auto_schema(
            operation_description="General PDF organization operations. "
                                 "This endpoint can be extended for various organization tasks.",
            request_body=OrganizePDFSerializer,
            responses={
                200: openapi.Response(
                    description="Organized PDF file.",
                    content={"application/pdf": pdf_binary_schema},
                ),
                400: "Bad request (invalid PDF, etc.).",
                413: "File too large.",
                500: "Internal server error.",
            },
            consumes=["multipart/form-data"],
        )(func)
    
    return decorator

