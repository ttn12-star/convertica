# decorators.py
from typing import Callable
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi
from .serializers import AddPageNumbersSerializer


def add_page_numbers_docs() -> Callable:
    """Decorator providing Swagger documentation for add page numbers API."""
    
    pdf_binary_schema = openapi.Schema(
        type=openapi.TYPE_STRING,
        format="binary",
        description="PDF file with page numbers added.",
        example="(binary file stream)",
    )
    
    def decorator(func: Callable) -> Callable:
        return swagger_auto_schema(
            operation_description="Add page numbers to PDF pages. "
                                 "You can customize position, font size, starting number, and format.",
            request_body=AddPageNumbersSerializer,
            responses={
                200: openapi.Response(
                    description="PDF file with page numbers.",
                    content={"application/pdf": pdf_binary_schema},
                ),
                400: "Bad request (invalid PDF, invalid parameters, etc.).",
                413: "File too large.",
                500: "Internal server error.",
            },
            consumes=["multipart/form-data"],
        )(func)
    
    return decorator

