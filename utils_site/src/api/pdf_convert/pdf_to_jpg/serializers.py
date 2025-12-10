# serializers.py
from rest_framework import serializers


class PDFToJPGSerializer(serializers.Serializer):
    """
    Serializer for uploading a PDF file to convert it to JPG.
    """

    pdf_file = serializers.FileField(
        required=True, help_text="PDF file to be converted into JPG format"
    )
    page = serializers.IntegerField(
        required=False,
        default=None,
        allow_null=True,
        min_value=1,
        help_text="Page number to convert (optional). If not specified, converts all pages to ZIP archive.",
    )
    dpi = serializers.IntegerField(
        required=False,
        default=300,
        min_value=72,
        max_value=600,
        help_text="DPI (dots per inch) for image quality (default: 300, range: 72-600)",
    )
