# decorators.py
from collections.abc import Callable

from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema


def pdf_to_word_docs() -> Callable:
    """Decorator providing Swagger documentation for PDF → DOCX conversion API.

    Returns:
        Callable: Decorated DRF view method.
    """

    docx_binary_schema = openapi.Schema(
        type=openapi.TYPE_STRING,
        format="binary",
        description="Binary DOCX file.",
        example="(binary file stream)",
    )

    def decorator(func: Callable) -> Callable:
        return swagger_auto_schema(
            operation_description="Convert a PDF file into a DOCX document.",
            schema=None,  # Prevent auto-detection from serializer
            manual_parameters=[
                openapi.Parameter(
                    "pdf_file",
                    openapi.IN_FORM,
                    description="PDF file to convert",
                    type=openapi.TYPE_FILE,
                    required=True,
                ),
            ],
            request_body=None,  # Explicitly disable request body to avoid conflict with manual_parameters
            responses={
                200: openapi.Response(
                    description="Converted DOCX file.",
                    content={
                        "application/vnd.openxmlformats-officedocument.wordprocessingml.document": docx_binary_schema
                    },
                ),
                400: "Bad request.",
                413: "File too large.",
                500: "Internal server error.",
            },
            consumes=["multipart/form-data"],
        )(func)

    return decorator
