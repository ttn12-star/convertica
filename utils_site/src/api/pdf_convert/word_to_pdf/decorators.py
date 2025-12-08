from typing import Callable

from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema


def word_to_pdf_docs() -> Callable:
    """Decorator providing Swagger documentation for DOCX → PDF conversion API.

    Returns:
        Callable: Decorated DRF view method.
    """
    pdf_binary_schema = openapi.Schema(
        type=openapi.TYPE_STRING,
        format="binary",
        description="Binary PDF file.",
        example="(binary file stream)",
    )

    def decorator(func: Callable) -> Callable:
        return swagger_auto_schema(
            operation_description="Convert a DOCX file into a PDF document.",
            schema=None,  # Prevent auto-detection from serializer
            manual_parameters=[
                openapi.Parameter(
                    "word_file",
                    openapi.IN_FORM,
                    description="Word file (.doc or .docx) to convert",
                    type=openapi.TYPE_FILE,
                    required=True,
                ),
            ],
            request_body=None,  # Explicitly disable request body to avoid conflict with manual_parameters
            responses={
                200: openapi.Response(
                    description="Converted PDF file.",
                    content={"application/pdf": pdf_binary_schema},
                ),
                400: "Bad request.",
                413: "File too large.",
                500: "Internal server error.",
            },
            consumes=["multipart/form-data"],
        )(func)

    return decorator
