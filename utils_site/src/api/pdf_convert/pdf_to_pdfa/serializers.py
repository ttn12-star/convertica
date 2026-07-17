from rest_framework import serializers


class PDFToPDFASerializer(serializers.Serializer):
    """Serializer for the PDF to PDF/A converter."""

    pdf_file = serializers.FileField(required=True)
    conformance = serializers.ChoiceField(
        choices=["pdfa-1b", "pdfa-2b", "pdfa-3b"],
        default="pdfa-2b",
        required=False,
        help_text=(
            "PDF/A level: 1b (maximum compatibility, no transparency), "
            "2b (recommended, default), 3b (allows embedded file attachments)."
        ),
    )
