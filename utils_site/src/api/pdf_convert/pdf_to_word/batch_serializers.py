"""Batch serializers for PDF to Word conversion."""

from rest_framework import serializers


class PDFToWordBatchSerializer(serializers.Serializer):
    """Serializer for batch PDF to Word conversion."""

    pdf_files = serializers.ListField(
        child=serializers.FileField(),
        required=True,
        help_text="List of PDF files to convert (max 10 for premium users)",
    )
    ocr_enabled = serializers.BooleanField(
        required=False,
        default=False,
        help_text="Enable OCR for scanned PDFs (premium only)",
    )
    ocr_language = serializers.ChoiceField(
        required=False,
        default="auto",
        choices=[
            ("auto", "Auto-detect"),
            ("eng", "English"),
            ("rus", "Russian"),
            ("deu", "German"),
            ("fra", "French"),
            ("spa", "Spanish"),
            ("ita", "Italian"),
            ("por", "Portuguese"),
            ("pol", "Polish"),
            ("ukr", "Ukrainian"),
            ("chi_sim", "Chinese (Simplified)"),
            ("chi_tra", "Chinese (Traditional)"),
            ("jpn", "Japanese"),
            ("kor", "Korean"),
            ("ara", "Arabic"),
            ("hin", "Hindi"),
            ("tur", "Turkish"),
            ("ind", "Indonesian"),
        ],
        help_text="OCR language for text recognition",
    )
