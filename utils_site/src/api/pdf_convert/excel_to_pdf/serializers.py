"""
Serializers for Excel to PDF conversion API.
"""

from rest_framework import serializers

ORIENTATION_CHOICES = ("auto", "portrait", "landscape")
FIT_MODE_CHOICES = ("fit_width", "actual")


class ExcelToPDFSerializer(serializers.Serializer):
    """Serializer for Excel to PDF conversion requests."""

    excel_file = serializers.FileField(
        required=True, help_text="Excel file (.xls or .xlsx) to convert to PDF"
    )
    orientation = serializers.ChoiceField(
        choices=ORIENTATION_CHOICES,
        required=False,
        default="auto",
        help_text="Page orientation: 'auto' (landscape for wide sheets), "
        "'portrait' or 'landscape'.",
    )
    fit_mode = serializers.ChoiceField(
        choices=FIT_MODE_CHOICES,
        required=False,
        default="fit_width",
        help_text="'fit_width' scales each sheet so all columns fit one page "
        "width (default); 'actual' keeps the sheet's own size.",
    )


class ExcelToPDFBatchSerializer(serializers.Serializer):
    """Serializer for batch Excel to PDF conversion requests."""

    excel_files = serializers.ListField(
        child=serializers.FileField(),
        required=True,
        min_length=1,
        max_length=10,  # Premium users can process up to 10 files
        help_text="List of Excel files (.xls or .xlsx) to convert to PDF",
    )
