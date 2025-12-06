# serializers.py
from rest_framework import serializers


class AddWatermarkSerializer(serializers.Serializer):
    """Serializer for adding watermark to PDF."""
    pdf_file = serializers.FileField(required=True)
    watermark_text = serializers.CharField(
        required=False,
        default="CONFIDENTIAL",
        max_length=100,
        help_text="Text to use as watermark."
    )
    watermark_file = serializers.FileField(
        required=False,
        help_text="Image file to use as watermark (PNG, JPG). If provided, watermark_text is ignored."
    )
    position = serializers.ChoiceField(
        choices=['center', 'diagonal'],
        required=False,
        default='diagonal',
        help_text="Position of watermark."
    )
    opacity = serializers.FloatField(
        required=False,
        default=0.3,
        min_value=0.1,
        max_value=1.0,
        help_text="Opacity of watermark (0.1-1.0)."
    )
    font_size = serializers.IntegerField(
        required=False,
        default=72,
        min_value=12,
        max_value=200,
        help_text="Font size for text watermark (12-200)."
    )

