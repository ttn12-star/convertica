# decorators.py
from typing import Callable
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi
from .serializers import PDFToExcelSerializer


def pdf_to_excel_docs() -> Callable:
    """Decorator providing Swagger documentation for PDF to Excel API."""
    
    excel_binary_schema = openapi.Schema(
        type=openapi.TYPE_STRING,
        format="binary",
        description="Excel file (.xlsx) with extracted tables from PDF.",
        example="(binary file stream)",
    )
    
    def decorator(func: Callable) -> Callable:
        return swagger_auto_schema(
            operation_description="Convert PDF to Excel by extracting tables. "
                                 "The PDF must contain tables for this conversion to work. "
                                 "Each table will be placed in a separate sheet.",
            request_body=PDFToExcelSerializer,
            responses={
                200: openapi.Response(
                    description="Excel file (.xlsx) with extracted tables.",
                    content={"application/vnd.openxmlformats-officedocument.spreadsheetml.sheet": excel_binary_schema},
                ),
                400: "Bad request (invalid PDF, no tables found, etc.).",
                413: "File too large.",
                500: "Internal server error.",
            },
            consumes=["multipart/form-data"],
        )(func)
    
    return decorator

