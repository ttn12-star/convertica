"""Serializers for batch Sign PDF requests."""

from rest_framework import serializers


class SignPDFBatchSerializer(serializers.Serializer):
    """Serializer for batch Sign PDF requests.

    Applies the same signature image to all supplied PDF files.
    """

    pdf_files = serializers.ListField(
        child=serializers.FileField(),
        required=True,
        min_length=1,
        max_length=10,
        help_text="List of PDF files to sign (up to 10 for premium users).",
    )
    signature_image = serializers.ImageField(
        required=True,
        help_text="Signature image to apply to all PDFs (PNG/JPG; PNG with transparency recommended).",
    )
    page_number = serializers.IntegerField(
        required=False,
        default=1,
        min_value=1,
        help_text="Page number to add the signature to in each PDF (1-indexed).",
    )
    position = serializers.ChoiceField(
        required=False,
        default="bottom-right",
        choices=[
            "bottom-right",
            "bottom-left",
            "bottom-center",
            "top-right",
            "top-left",
            "center",
        ],
        help_text="Position of the signature on the page.",
    )
    signature_width = serializers.IntegerField(
        required=False,
        default=150,
        min_value=50,
        max_value=400,
        help_text="Width of the signature in points (50-400).",
    )
    opacity = serializers.FloatField(
        required=False,
        default=1.0,
        min_value=0.1,
        max_value=1.0,
        help_text="Signature opacity (0.1 to 1.0).",
    )
    all_pages = serializers.BooleanField(
        required=False,
        default=False,
        help_text="Apply the signature to all pages of each PDF (premium feature).",
    )
