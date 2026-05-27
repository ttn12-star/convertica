from rest_framework import serializers


class UnlockZipSerializer(serializers.Serializer):
    """Serializer for removing the password from a ZIP archive."""

    archive_file = serializers.FileField(required=True)
    password = serializers.CharField(
        required=True,
        min_length=1,
        max_length=128,
        write_only=True,
        trim_whitespace=False,
        help_text="The current password of the archive.",
    )
