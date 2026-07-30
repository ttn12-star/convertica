# serializers.py
from rest_framework import serializers

from .utils import MODES, PAGE_SIZES


class ResizePDFSerializer(serializers.Serializer):
    """Serializer for PDF page-size change requests."""

    pdf_file = serializers.FileField(
        required=True,
        help_text="PDF file whose pages should be placed on a different sheet",
    )
    target_size = serializers.ChoiceField(
        choices=sorted(PAGE_SIZES),
        required=False,
        default="letter",
        help_text="Target paper size: a4, letter or legal",
    )
    mode = serializers.ChoiceField(
        choices=list(MODES),
        required=False,
        default="auto",
        help_text=(
            "auto: keep content at 100% when it fits the new sheet, otherwise "
            "shrink by the smallest amount that crops nothing. "
            "fit: always scale the whole page to the sheet."
        ),
    )
