# serializers.py
import json

from rest_framework import serializers


class OrganizePDFSerializer(serializers.Serializer):
    """Serializer for general PDF organization requests."""

    pdf_file = serializers.FileField(required=True)
    operation = serializers.ChoiceField(
        choices=["reorder", "sort"],
        required=False,
        default="reorder",
        help_text="Organization operation type.",
    )
    page_order = serializers.CharField(
        required=False,
        allow_blank=True,
        help_text="JSON array of page indices in the desired order (0-based).",
    )

    def validate_page_order(self, value):
        """Validate and parse page_order JSON string."""
        if not value:
            return None

        try:
            order = json.loads(value)
            if not isinstance(order, list):
                raise serializers.ValidationError("page_order must be a JSON array.")
            if not order:
                raise serializers.ValidationError("page_order cannot be empty.")
            if not all(isinstance(x, int) and x >= 0 for x in order):
                raise serializers.ValidationError(
                    "page_order must contain non-negative integers."
                )
            # Check for duplicates
            if len(set(order)) != len(order):
                raise serializers.ValidationError(
                    "page_order contains duplicate page indices."
                )
            return order
        except json.JSONDecodeError as exc:
            raise serializers.ValidationError("page_order must be valid JSON.") from exc
