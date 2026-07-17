# decorators.py
"""Swagger docs for the PDF Editor endpoint (superset of Add Text)."""
from collections.abc import Callable

from ..add_text.decorators import add_text_pdf_docs


def pdf_editor_docs() -> Callable:
    """PDF Editor: PDF + JSON operations (text/whiteout/highlight/image/
    signature/shape/ink). Same request contract as Add Text, extra types."""
    return add_text_pdf_docs()
