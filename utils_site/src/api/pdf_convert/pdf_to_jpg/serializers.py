# serializers.py
from rest_framework import serializers


class PDFToJPGSerializer(serializers.Serializer):
    """
    Serializer for uploading a PDF file to convert it to JPG.
    """

    pdf_file = serializers.FileField(
        required=True, help_text="PDF file to be converted into JPG format"
    )
    pages = serializers.CharField(
        required=False,
        default="all",
        help_text='Pages to convert: "all" for all pages, or specific pages like "1,3,5" or "1-5". Default: "all".',
    )
    dpi = serializers.IntegerField(
        required=False,
        default=300,
        min_value=72,
        max_value=600,
        help_text="DPI (dots per inch) for image quality (default: 300, range: 72-600)",
    )
