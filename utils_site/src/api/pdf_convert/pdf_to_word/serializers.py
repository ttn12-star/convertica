# serializers.py
from rest_framework import serializers


class PDFToWordSerializer(serializers.Serializer):
    """
    Serializer for uploading a PDF file to convert it to Word.
    """

    pdf_file = serializers.FileField(
        required=True, help_text="PDF file to be converted into Word format"
    )
