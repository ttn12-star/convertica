# decorators.py
"""Swagger documentation for Sign PDF endpoints.

Two decorators because single-file and batch use different contracts:

* `sign_pdf_docs` — single-file: a PDF plus a JSON `signatures` array.
* `sign_pdf_batch_docs` — batch: up to 10 PDFs plus one signature image
  and an enum position (same placement applied to every file).

The single-file shape exists because the new visual editor places the
signature at arbitrary (x, y) per page. Batch keeps the old enum because
per-coordinate placement is meaningless when every file has different
dimensions.
"""
from collections.abc import Callable

from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema

_PDF_RESPONSE = openapi.Schema(
    type=openapi.TYPE_STRING,
    format="binary",
    description="Signed PDF file.",
    example="(binary file stream)",
)


def sign_pdf_docs() -> Callable:
    """Single-file Sign PDF: PDF + JSON signatures array."""

    def decorator(func: Callable) -> Callable:
        return swagger_auto_schema(
            operation_description=(
                "Add one or more image signatures to a PDF at arbitrary "
                "positions. Premium only. The `signatures` field is a "
                "JSON-encoded array of placement objects; each object "
                "carries the target page (0-indexed), top-left (x, y) in "
                "PDF points, width/height in PDF points, and a base64 "
                "image data URI (typically a transparent PNG produced by "
                "the in-browser draw/type/upload editor)."
            ),
            manual_parameters=[
                openapi.Parameter(
                    "pdf_file",
                    openapi.IN_FORM,
                    description="PDF file to sign",
                    type=openapi.TYPE_FILE,
                    required=True,
                ),
                openapi.Parameter(
                    "signatures",
                    openapi.IN_FORM,
                    description=(
                        "JSON array, e.g. "
                        '[{"page":0,"x":400,"y":700,"width":150,"height":60,'
                        '"image_data_uri":"data:image/png;base64,..."}]'
                    ),
                    type=openapi.TYPE_STRING,
                    required=True,
                ),
            ],
            responses={
                200: openapi.Response(
                    description="Signed PDF file.",
                    content={"application/pdf": _PDF_RESPONSE},
                ),
                400: "Bad request (invalid PDF, malformed signatures JSON).",
                403: "Premium required.",
                413: "File too large.",
                500: "Internal server error.",
            },
            consumes=["multipart/form-data"],
        )(func)

    return decorator


def sign_pdf_batch_docs() -> Callable:
    """Batch Sign PDF: many PDFs + one image + enum position."""

    def decorator(func: Callable) -> Callable:
        return swagger_auto_schema(
            operation_description=(
                "Apply the same signature image to up to 10 PDFs at once. "
                "Uses an enum position because batch files have different "
                "dimensions. Premium only. Returns a ZIP archive."
            ),
            manual_parameters=[
                openapi.Parameter(
                    "pdf_files",
                    openapi.IN_FORM,
                    description="PDF files to sign (up to 10).",
                    type=openapi.TYPE_FILE,
                    required=True,
                ),
                openapi.Parameter(
                    "signature_image",
                    openapi.IN_FORM,
                    description="Signature image (PNG/JPG; PNG with transparency recommended).",
                    type=openapi.TYPE_FILE,
                    required=True,
                ),
                openapi.Parameter(
                    "page_number",
                    openapi.IN_FORM,
                    description="Page number to sign (1-indexed, default 1).",
                    type=openapi.TYPE_INTEGER,
                    required=False,
                ),
                openapi.Parameter(
                    "position",
                    openapi.IN_FORM,
                    description=(
                        "Position: bottom-right, bottom-left, bottom-center, "
                        "top-right, top-left, center."
                    ),
                    type=openapi.TYPE_STRING,
                    required=False,
                ),
                openapi.Parameter(
                    "signature_width",
                    openapi.IN_FORM,
                    description="Width in points (50-400, default 150).",
                    type=openapi.TYPE_INTEGER,
                    required=False,
                ),
                openapi.Parameter(
                    "opacity",
                    openapi.IN_FORM,
                    description="Opacity (0.1-1.0, default 1.0).",
                    type=openapi.TYPE_NUMBER,
                    required=False,
                ),
                openapi.Parameter(
                    "all_pages",
                    openapi.IN_FORM,
                    description="Apply to all pages.",
                    type=openapi.TYPE_BOOLEAN,
                    required=False,
                ),
            ],
            responses={
                200: openapi.Response(
                    description="ZIP archive of signed PDFs.",
                    content={"application/zip": _PDF_RESPONSE},
                ),
                400: "Bad request.",
                403: "Premium required.",
                413: "File too large.",
                500: "Internal server error.",
            },
            consumes=["multipart/form-data"],
        )(func)

    return decorator
