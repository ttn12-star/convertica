# serializers.py
from rest_framework import serializers


class MergePDFSerializer(serializers.Serializer):
    """Serializer for PDF merge requests."""
    pdf_files = serializers.ListField(
        child=serializers.FileField(),
        allow_empty=False,
        min_length=2,
        max_length=10,
        help_text="List of PDF files to merge (2-10 files)."
    )
    order = serializers.ChoiceField(
        choices=['upload', 'alphabetical'],
        required=False,
        default="upload",
        help_text="Merge order: 'upload' (as uploaded) or 'alphabetical'."
    )
    
    def validate_pdf_files(self, value):
        """Validate that at least 2 files are provided."""
        if len(value) < 2:
            raise serializers.ValidationError("At least 2 PDF files are required.")
        if len(value) > 10:
            raise serializers.ValidationError("Maximum 10 PDF files allowed.")
        return value

