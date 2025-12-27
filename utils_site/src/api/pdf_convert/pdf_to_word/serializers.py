# serializers.py
try:
    from rest_framework import serializers
except ImportError:
    # Fallback for linting issues
    import os
    import sys

    sys.path.append(os.path.join(os.path.dirname(__file__), "../../../../../"))
    from rest_framework import serializers


class PDFToWordSerializer(serializers.Serializer):
    """
    Serializer for uploading a PDF file to convert it to Word.
    """

    pdf_file = serializers.FileField(
        required=True, help_text="PDF file to be converted into Word format"
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
        help_text="OCR language for text recognition (auto-detect uses eng+rus+deu+fra+spa+chi_sim)",
    )
    ocr_confidence_threshold = serializers.IntegerField(
        required=False,
        default=60,
        min_value=0,
        max_value=100,
        help_text="Minimum confidence threshold for OCR text (0-100, default 60)",
    )
