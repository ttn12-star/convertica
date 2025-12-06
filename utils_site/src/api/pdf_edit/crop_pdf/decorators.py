# decorators.py
from typing import Callable
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi
from .serializers import CropPDFSerializer


def crop_pdf_docs() -> Callable:
    """Decorator providing Swagger documentation for PDF crop API."""
    
    pdf_binary_schema = openapi.Schema(
        type=openapi.TYPE_STRING,
        format="binary",
        description="Cropped PDF file.",
        example="(binary file stream)",
    )
    
    def decorator(func: Callable) -> Callable:
        return swagger_auto_schema(
            operation_description="Crop PDF pages by specifying crop box coordinates. "
                                 "You can crop all pages or specific pages.",
            request_body=CropPDFSerializer,
            responses={
                200: openapi.Response(
                    description="Cropped PDF file.",
                    content={"application/pdf": pdf_binary_schema},
                ),
                400: "Bad request (invalid PDF, invalid coordinates, etc.).",
                413: "File too large.",
                500: "Internal server error.",
            },
            consumes=["multipart/form-data"],
        )(func)
    
    return decorator

