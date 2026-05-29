# serializers.py
from rest_framework import serializers

from .utils import ALLOWED_SIZES


class ImageToICOSerializer(serializers.Serializer):
    """Serializer for image-to-ICO favicon conversion requests."""

    # FileField (not ImageField): SVG is a valid input here but is not a valid
    # ImageField payload.
    image_file = serializers.FileField(
        required=True,
        help_text="Source image (PNG, JPEG, WebP, GIF, BMP, TIFF, or SVG).",
    )
    sizes = serializers.CharField(
        required=False,
        default="16,32,48",
        help_text=(
            "Comma-separated square sizes to embed. Allowed: "
            "16, 24, 32, 48, 64, 128, 256."
        ),
    )

    def validate_sizes(self, value: str) -> list[int]:
        """Parse comma-separated sizes into a validated list of ints."""
        parsed: list[int] = []
        for part in str(value).split(","):
            part = part.strip()
            if not part:
                continue
            try:
                size = int(part)
            except ValueError:
                continue
            if size in ALLOWED_SIZES and size not in parsed:
                parsed.append(size)

        if not parsed:
            raise serializers.ValidationError(
                "No valid sizes provided. Allowed sizes: "
                + ", ".join(str(s) for s in ALLOWED_SIZES)
                + "."
            )
        return parsed
