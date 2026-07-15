# serializers.py
from rest_framework import serializers


class PasswordProtectImageSerializer(serializers.Serializer):
    """Upload image(s) + password → single AES-256 password-protected PDF.

    Multiple files: send multiple 'image_files' parameters in the form.
    """

    image_files = serializers.FileField(
        required=True,
        help_text=(
            "Image file(s) (JPG, PNG, WebP, GIF) to lock into one password-"
            "protected PDF. Send multiple 'image_files' parameters for multiple."
        ),
    )
    password = serializers.CharField(
        required=True,
        min_length=1,
        max_length=100,
        write_only=True,
        trim_whitespace=True,
        help_text="Password required to open the resulting PDF.",
    )
    user_password = serializers.CharField(
        required=False,
        min_length=1,
        max_length=100,
        write_only=True,
        trim_whitespace=True,
        allow_blank=True,
        help_text="User password (optional); falls back to 'password'.",
    )
    owner_password = serializers.CharField(
        required=False,
        min_length=1,
        max_length=100,
        write_only=True,
        trim_whitespace=True,
        allow_blank=True,
        help_text="Owner password (optional); falls back to 'password'.",
    )
    quality = serializers.IntegerField(
        required=False,
        default=85,
        min_value=60,
        max_value=95,
        help_text="JPEG quality of images embedded in the PDF (60-95). Default 85.",
    )
