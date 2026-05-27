from rest_framework import serializers


class ProtectZipSerializer(serializers.Serializer):
    """Serializer for protecting a ZIP archive with a password."""

    archive_file = serializers.FileField(required=True)
    password = serializers.CharField(
        required=True,
        min_length=1,
        max_length=128,
        write_only=True,
        trim_whitespace=False,
        help_text="Password used to AES-256-encrypt the archive.",
    )
