# decorators.py
from collections.abc import Callable

from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema


def jpg_to_pdf_docs() -> Callable:
    """Decorator providing Swagger documentation for JPG → PDF conversion API.

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
            operation_description="Convert one or more JPG/JPEG images into a PDF document. "
            "Multiple images will be combined into a single PDF, with each image on a separate page. "
            "To upload multiple files, send multiple 'image_file' parameters.",
            schema=None,  # Prevent auto-detection from serializer
            manual_parameters=[
                openapi.Parameter(
                    "image_file",
                    openapi.IN_FORM,
                    description="JPG/JPEG image file(s) to convert. Can be sent multiple times for multiple files.",
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
                400: "Bad request (invalid image, unsupported format, etc.).",
                413: "File too large.",
                500: "Internal server error.",
            },
            consumes=["multipart/form-data"],
        )(func)

    return decorator
