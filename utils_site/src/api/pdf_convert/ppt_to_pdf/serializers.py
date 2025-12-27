"""
Serializers for PowerPoint to PDF conversion API.
"""

from rest_framework import serializers


class PowerPointToPDFSerializer(serializers.Serializer):
    """Serializer for PowerPoint to PDF conversion requests."""

    ppt_file = serializers.FileField(
        required=True, help_text="PowerPoint file (.ppt or .pptx) to convert to PDF"
    )


class PowerPointToPDFBatchSerializer(serializers.Serializer):
    """Serializer for batch PowerPoint to PDF conversion requests."""

    ppt_files = serializers.ListField(
        child=serializers.FileField(),
        required=True,
        min_length=1,
        max_length=10,  # Premium users can process up to 10 files
        help_text="List of PowerPoint files (.ppt or .pptx) to convert to PDF",
    )
