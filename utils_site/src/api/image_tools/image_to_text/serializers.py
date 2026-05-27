"""Serializer for the Image to Text (OCR) tool."""

from rest_framework import serializers

from ...ocr_utils import SITE_LANGUAGES

# Site language codes the OCR engine supports, plus 'auto' detection.
_LANGUAGE_CHOICES = ["auto", *sorted(SITE_LANGUAGES.keys())]


class ImageToTextSerializer(serializers.Serializer):
    """Single image → extracted plain text.

    Uses FileField (not ImageField) because Pillow's image verification in
    ImageField runs before the pillow-heif plugin is guaranteed to be
    registered, which would reject HEIC. Extension/content-type whitelisting is
    enforced by ImageToTextAPIView's ALLOWED_EXTENSIONS / ALLOWED_CONTENT_TYPES.
    """

    image_file = serializers.FileField(
        required=True,
        help_text="Image file (JPEG, PNG, WebP, HEIC/HEIF, BMP, TIFF, GIF).",
    )
    language = serializers.ChoiceField(
        required=False,
        default="auto",
        choices=_LANGUAGE_CHOICES,
        help_text="OCR language (site code) or 'auto' for multi-language detection.",
    )
    confidence_threshold = serializers.IntegerField(
        required=False,
        default=60,
        min_value=0,
        max_value=100,
        help_text="Minimum per-word OCR confidence to keep (0-100, default 60).",
    )
    output_format = serializers.ChoiceField(
        required=False,
        default="txt",
        choices=["txt", "docx"],
        help_text="Output format: 'txt' (default, free) or 'docx' (Word, premium).",
    )
