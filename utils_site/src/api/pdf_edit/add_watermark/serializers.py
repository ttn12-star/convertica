# serializers.py
from rest_framework import serializers

# Watermark image is a second, unvalidated trust boundary (validate_file_basic
# only checks the primary pdf_file). Cap its size and verify real image magic
# bytes before it reaches PIL.Image.open in utils.
_WM_MAX_BYTES = 10 * 1024 * 1024  # 10 MB


class AddWatermarkSerializer(serializers.Serializer):
    """Serializer for adding watermark to PDF."""

    pdf_file = serializers.FileField(required=True)
    watermark_text = serializers.CharField(
        required=False,
        default="CONFIDENTIAL",
        max_length=100,
        help_text="Text to use as watermark.",
    )
    watermark_file = serializers.FileField(
        required=False,
        help_text="Image file to use as watermark (PNG, JPG). If provided, watermark_text is ignored.",
    )

    def validate_watermark_file(self, value):
        """Size + magic-byte check on the optional watermark image."""
        if value is None:
            return value
        if value.size > _WM_MAX_BYTES:
            raise serializers.ValidationError(
                "Watermark image must be smaller than 10 MB."
            )
        head = value.read(12)
        value.seek(0)
        is_png = head.startswith(b"\x89PNG\r\n\x1a\n")
        is_jpeg = head.startswith(b"\xff\xd8\xff")
        is_webp = head[:4] == b"RIFF" and head[8:12] == b"WEBP"
        if not (is_png or is_jpeg or is_webp):
            raise serializers.ValidationError(
                "Watermark must be a PNG, JPEG or WEBP image."
            )
        return value

    position = serializers.ChoiceField(
        choices=["center", "diagonal", "custom"],
        required=False,
        default="diagonal",
        help_text="Position of watermark.",
    )
    x = serializers.FloatField(
        required=False, help_text="X coordinate for custom position (in points)."
    )
    y = serializers.FloatField(
        required=False, help_text="Y coordinate for custom position (in points)."
    )
    color = serializers.CharField(
        required=False,
        default="#000000",
        max_length=7,
        help_text="Color of watermark in hex format (e.g., #FF0000 for red).",
    )
    opacity = serializers.FloatField(
        required=False,
        default=0.3,
        min_value=0.1,
        max_value=1.0,
        help_text="Opacity of watermark (0.1-1.0).",
    )
    font_size = serializers.IntegerField(
        required=False,
        default=72,
        min_value=12,
        max_value=200,
        help_text="Font size for text watermark (12-200).",
    )
    rotation = serializers.FloatField(
        required=False,
        default=0.0,
        min_value=-360.0,
        max_value=360.0,
        help_text="Rotation angle in degrees (-360 to 360).",
    )
    scale = serializers.FloatField(
        required=False,
        default=1.0,
        min_value=0.1,
        max_value=3.0,
        help_text="Scale factor for watermark (0.1 to 3.0).",
    )
    pages = serializers.CharField(
        required=False,
        default="all",
        help_text="Pages to add watermark to. Use 'all' for all pages, or comma-separated page numbers (1-indexed).",
    )
