# decorators.py
"""Swagger documentation for the Add Text to PDF endpoint."""
from collections.abc import Callable

from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema

_PDF_RESPONSE = openapi.Schema(
    type=openapi.TYPE_STRING,
    format="binary",
    description="Edited PDF file.",
    example="(binary file stream)",
)


def add_text_pdf_docs() -> Callable:
    """Add Text to PDF: PDF + JSON operations array."""

    def decorator(func: Callable) -> Callable:
        return swagger_auto_schema(
            operation_description=(
                "Place text boxes, whiteout rectangles, and highlights onto "
                "a PDF at arbitrary positions. Free under the global daily "
                "quota. The `operations` field is a JSON-encoded array; each "
                "item carries the type (text/whiteout/highlight), target page "
                "(0-indexed), top-left (x, y) and width/height in PDF points, "
                "and for text: the content, font_key (sans/serif/mono), "
                "font_size, #rrggbb color, bold/italic/underline flags, and "
                "alignment. Text is embedded as real, selectable text with "
                "Unicode support (Latin, Cyrillic, Arabic, Devanagari)."
            ),
            manual_parameters=[
                openapi.Parameter(
                    "pdf_file",
                    openapi.IN_FORM,
                    description="PDF file to edit",
                    type=openapi.TYPE_FILE,
                    required=True,
                ),
                openapi.Parameter(
                    "operations",
                    openapi.IN_FORM,
                    description=(
                        "JSON array, e.g. "
                        '[{"type":"text","page":0,"x":100,"y":200,"width":200,'
                        '"height":40,"text":"Hello","font_size":14,'
                        '"color":"#111111"}]'
                    ),
                    type=openapi.TYPE_STRING,
                    required=True,
                ),
            ],
            request_body=None,  # disable auto-detect (manual params use multipart/form-data)
            responses={
                200: openapi.Response(
                    description="Edited PDF file.",
                    content={"application/pdf": _PDF_RESPONSE},
                ),
                400: "Bad request (invalid PDF, malformed operations JSON).",
                413: "File too large.",
                429: "Daily quota exceeded.",
                500: "Internal server error.",
            },
            consumes=["multipart/form-data"],
        )(func)

    return decorator
