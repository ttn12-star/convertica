# serializers.py
from rest_framework import serializers


class JPGToPDFSerializer(serializers.Serializer):
    """
    Serializer for uploading JPG/JPEG image files to convert them to PDF.
    """
    image_file = serializers.FileField(
        required=True,
        help_text="JPG/JPEG image file(s) to be converted into PDF format"
    )

