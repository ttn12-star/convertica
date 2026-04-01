# decorators.py
from collections.abc import Callable

from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema


def sign_pdf_docs() -> Callable:
    """Decorator providing Swagger documentation for the Sign PDF API."""

    pdf_binary_schema = openapi.Schema(
        type=openapi.TYPE_STRING,
        format="binary",
        description="Signed PDF file.",
        example="(binary file stream)",
    )

    def decorator(func: Callable) -> Callable:
        return swagger_auto_schema(
            operation_description="Add an image signature to a PDF page. "
            "Supports PNG with transparency. "
            "Choose the position, size, and opacity of the signature.",
            auto_schema=None,
            schema=None,
            manual_parameters=[
                openapi.Parameter(
                    "pdf_file",
                    openapi.IN_FORM,
                    description="PDF file to sign",
                    type=openapi.TYPE_FILE,
                    required=True,
                ),
                openapi.Parameter(
                    "signature_image",
                    openapi.IN_FORM,
                    description="Signature image file (PNG/JPG; PNG with transparency recommended)",
                    type=openapi.TYPE_FILE,
                    required=True,
                ),
                openapi.Parameter(
                    "page_number",
                    openapi.IN_FORM,
                    description="Page number to sign (1-indexed, default 1)",
                    type=openapi.TYPE_INTEGER,
                    required=False,
                ),
                openapi.Parameter(
                    "position",
                    openapi.IN_FORM,
                    description=(
                        "Position of the signature: bottom-right, bottom-left, "
                        "bottom-center, top-right, top-left, center"
                    ),
                    type=openapi.TYPE_STRING,
                    required=False,
                ),
                openapi.Parameter(
                    "signature_width",
                    openapi.IN_FORM,
                    description="Width of the signature in points (50-400, default 150)",
                    type=openapi.TYPE_INTEGER,
                    required=False,
                ),
                openapi.Parameter(
                    "opacity",
                    openapi.IN_FORM,
                    description="Signature opacity (0.1-1.0, default 1.0)",
                    type=openapi.TYPE_NUMBER,
                    required=False,
                ),
                openapi.Parameter(
                    "all_pages",
                    openapi.IN_FORM,
                    description="Apply the signature to all pages (premium feature)",
                    type=openapi.TYPE_BOOLEAN,
                    required=False,
                ),
            ],
            request_body=None,
            responses={
                200: openapi.Response(
                    description="Signed PDF file.",
                    content={"application/pdf": pdf_binary_schema},
                ),
                400: "Bad request (invalid PDF, missing signature image, invalid parameters).",
                413: "File too large.",
                500: "Internal server error.",
            },
            consumes=["multipart/form-data"],
        )(func)

    return decorator
