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
        help_text="JPG/JPEG image file(s) to be converted into PDF format. Multiple files will be combined into one PDF. Send multiple 'image_file' parameters for multiple files."
    )

