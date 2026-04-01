# decorators.py
from collections.abc import Callable

from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema


def flatten_pdf_docs() -> Callable:
    """Decorator providing Swagger documentation for PDF flatten API."""

    pdf_binary_schema = openapi.Schema(
        type=openapi.TYPE_STRING,
        format="binary",
        description="Flattened PDF file.",
        example="(binary file stream)",
    )

    def decorator(func: Callable) -> Callable:
        return swagger_auto_schema(
            operation_description=(
                "Flatten a PDF by removing interactive form fields and annotations. "
                "The result is a static PDF with all interactive elements removed."
            ),
            operation_summary="Flatten PDF",
            tags=["PDF Edit"],
            schema=None,
            manual_parameters=[
                openapi.Parameter(
                    "pdf_file",
                    openapi.IN_FORM,
                    description="PDF file to flatten",
                    type=openapi.TYPE_FILE,
                    required=True,
                ),
            ],
            request_body=None,
            responses={
                200: openapi.Response(
                    description="Flattened PDF file.",
                    content={"application/pdf": pdf_binary_schema},
                ),
                400: "Bad request (invalid PDF).",
                413: "File too large.",
                500: "Internal server error.",
            },
            consumes=["multipart/form-data"],
        )(func)

    return decorator
