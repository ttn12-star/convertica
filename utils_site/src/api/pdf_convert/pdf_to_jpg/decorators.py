# decorators.py
from typing import Callable
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi
from .serializers import PDFToJPGSerializer


def pdf_to_jpg_docs() -> Callable:
    """Decorator providing Swagger documentation for PDF → JPG conversion API.

    Returns:
        Callable: Decorated DRF view method.
    """

    jpg_binary_schema = openapi.Schema(
        type=openapi.TYPE_STRING,
        format="binary",
        description="Binary JPG/JPEG image file.",
        example="(binary file stream)",
    )

    def decorator(func: Callable) -> Callable:
        return swagger_auto_schema(
            operation_description="Convert a PDF page into a JPG image. "
                                 "By default converts the first page. "
                                 "You can specify page number and DPI for quality control.",
            request_body=PDFToJPGSerializer,
            responses={
                200: openapi.Response(
                    description="Converted JPG image file.",
                    content={
                        "image/jpeg": jpg_binary_schema
                    },
                ),
                400: "Bad request (invalid PDF, page number out of range, etc.).",
                413: "File too large.",
                500: "Internal server error.",
            },
            consumes=["multipart/form-data"],
        )(func)

    return decorator

