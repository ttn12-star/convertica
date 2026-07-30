# serializers.py
from rest_framework import serializers


class JPGToPDFSerializer(serializers.Serializer):
    """
    Serializer for uploading JPG/JPEG image files to convert them to PDF.
    Supports multiple files - all images will be combined into a single PDF.

    Note: For multiple files, send multiple 'image_file' parameters in the form.
    """

    image_file = serializers.FileField(
        required=True,
        help_text=(
            "JPG/JPEG image file(s) to be converted into PDF format. "
            "Multiple files will be combined into one PDF. "
            "Send multiple 'image_file' parameters for multiple files."
        ),
    )

    quality = serializers.IntegerField(
        required=False,
        default=85,
        min_value=60,
        max_value=95,
        help_text="JPEG quality for images in PDF (60-95). Higher quality = better image clarity but larger file size. Default: 85 (recommended).",
    )

    # Before this existed the answer depended on which code path ran: the
    # optimized converter defaulted to Letter while the sequential fallback and
    # the multi-file branch hardcoded A4, so the same upload could come back on
    # either sheet. Now it is one explicit choice everywhere.
    page_size = serializers.ChoiceField(
        choices=["a4", "letter"],
        required=False,
        default="a4",
        help_text="Page size of the generated PDF: a4 (default) or letter.",
    )
