# decorators.py
from collections.abc import Callable

from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema


def resize_pdf_docs() -> Callable:
    """Decorator providing Swagger documentation for the page-size API."""

    pdf_binary_schema = openapi.Schema(
        type=openapi.TYPE_STRING,
        format="binary",
        description="PDF with the new page size.",
        example="(binary file stream)",
    )

    def decorator(func: Callable) -> Callable:
        return swagger_auto_schema(
            operation_description=(
                "Place every page of a PDF on a different paper size "
                "(A4, US Letter or Legal). A4 and Letter are different shapes, "
                "so in the default 'auto' mode the content stays at 100% when "
                "it fits the new sheet and is shrunk by the smallest amount "
                "that crops nothing when it does not. Text and vector graphics "
                "are not rasterised."
            ),
            operation_summary="Change PDF page size",
            tags=["PDF Edit"],
            # drf-yasg speaks Swagger 2.0: responses take `schema=`, never the
            # OpenAPI 3 `content=`, or the docs page badge goes INVALID.
            schema=None,
            manual_parameters=[
                openapi.Parameter(
                    "pdf_file",
                    openapi.IN_FORM,
                    description="PDF file to re-sheet",
                    type=openapi.TYPE_FILE,
                    required=True,
                ),
                openapi.Parameter(
                    "target_size",
                    openapi.IN_FORM,
                    description="Target paper size (default: letter)",
                    type=openapi.TYPE_STRING,
                    enum=["a4", "letter", "legal"],
                    required=False,
                ),
                openapi.Parameter(
                    "mode",
                    openapi.IN_FORM,
                    description=(
                        "auto (default) never crops; fit always scales the "
                        "page to the sheet"
                    ),
                    type=openapi.TYPE_STRING,
                    enum=["auto", "fit"],
                    required=False,
                ),
            ],
            request_body=None,
            responses={
                200: openapi.Response(
                    description="PDF with the new page size.",
                    schema=pdf_binary_schema,
                ),
                400: "Bad request (invalid PDF, unknown size or mode).",
                413: "File too large.",
                500: "Internal server error.",
            },
            consumes=["multipart/form-data"],
        )(func)

    return decorator
