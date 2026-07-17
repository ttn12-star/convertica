# serializers.py
from rest_framework import serializers


class ProtectPDFSerializer(serializers.Serializer):
    """Serializer for protecting PDF with password."""

    pdf_file = serializers.FileField(required=True)
    password = serializers.CharField(
        required=True,
        min_length=1,
        max_length=100,
        write_only=True,
        trim_whitespace=True,
        help_text=(
            "Password to protect the PDF. This will be used for both user "
            "and owner password if not specified separately."
        ),
    )
    user_password = serializers.CharField(
        required=False,
        min_length=1,
        max_length=100,
        write_only=True,
        trim_whitespace=True,
        allow_blank=True,
        help_text="User password (optional). If not provided, 'password' will be used.",
    )
    owner_password = serializers.CharField(
        required=False,
        min_length=1,
        max_length=100,
        write_only=True,
        trim_whitespace=True,
        allow_blank=True,
        help_text="Owner password (optional). If not provided, 'password' will be used.",
    )
    # Premium permission toggles (server-gated in the view).
    restrict_printing = serializers.BooleanField(
        required=False,
        default=False,
        help_text="Disallow printing the document (Premium).",
    )
    restrict_copying = serializers.BooleanField(
        required=False,
        default=False,
        help_text=(
            "Disallow copying text and graphics (Premium). Accessibility "
            "extraction for screen readers stays allowed."
        ),
    )
    restrict_modifying = serializers.BooleanField(
        required=False,
        default=False,
        help_text="Disallow editing, annotating and assembling pages (Premium).",
    )
