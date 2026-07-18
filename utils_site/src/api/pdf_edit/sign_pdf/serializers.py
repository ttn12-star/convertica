# serializers.py
"""Serializers for the single-file Sign PDF endpoint.

Accepts a JSON `signatures` array with per-signature coordinates so the
front-end visual editor can place any number of signatures at arbitrary
positions on any page. The legacy `position`-enum contract still exists
on the *batch* endpoint (see `batch_serializers.py`) because batch is a
"same signature on every file" use-case where per-coordinate placement
makes no sense.
"""

import base64
import json
import re

from rest_framework import serializers

# Match add_text's contract: only png/jpeg/webp, with a decoded-size cap.
_SIG_DATA_URI_RE = re.compile(r"^data:image/(png|jpeg|webp);base64,", re.IGNORECASE)
_SIG_MAX_IMAGE_BYTES = 3 * 1024 * 1024


class SignatureItemSerializer(serializers.Serializer):
    """One placed signature: which page, where, how big, what image."""

    page = serializers.IntegerField(
        min_value=0,
        help_text="0-indexed page number.",
    )
    x = serializers.FloatField(
        min_value=0,
        help_text="X coordinate (PDF points, top-left origin).",
    )
    y = serializers.FloatField(
        min_value=0,
        help_text="Y coordinate (PDF points, top-left origin).",
    )
    width = serializers.FloatField(
        min_value=10,
        max_value=600,
        help_text="Width in PDF points (10-600).",
    )
    height = serializers.FloatField(
        min_value=10,
        max_value=600,
        help_text="Height in PDF points (10-600).",
    )
    image_data_uri = serializers.CharField(
        max_length=4_000_000,  # ~3 MB of base64 — caller is supposed to keep it small
        help_text="Signature image as a data URI (data:image/png;base64,...).",
    )

    def validate_image_data_uri(self, value: str) -> str:
        # Whitelist the image subtype and cap the decoded size, mirroring
        # add_text — the old check accepted any data:image/* and never verified
        # the decoded byte size (only the base64 char count).
        if not _SIG_DATA_URI_RE.match(value or ""):
            raise serializers.ValidationError(
                "Must be a data:image/(png|jpeg|webp);base64 URI."
            )
        _, b64 = value.split(";base64,", 1)
        try:
            raw = base64.b64decode(b64, validate=True)
        except (ValueError, TypeError) as exc:
            raise serializers.ValidationError("Image is not valid base64.") from exc
        if len(raw) > _SIG_MAX_IMAGE_BYTES:
            raise serializers.ValidationError("Signature image exceeds 3 MB.")
        return value


class SignPDFSerializer(serializers.Serializer):
    """Sign-PDF input: a PDF plus a JSON array of placed signatures."""

    MAX_SIGNATURES = 50

    pdf_file = serializers.FileField(
        required=True,
        help_text="PDF file to sign.",
    )
    signatures = serializers.CharField(
        required=True,
        help_text=(
            "JSON-encoded array of signature placements. Each item: "
            "{page, x, y, width, height, image_data_uri}."
        ),
    )

    def validate_signatures(self, value):
        try:
            items = json.loads(value) if isinstance(value, str) else value
        except (TypeError, ValueError) as exc:
            raise serializers.ValidationError(
                "signatures must be a JSON array.",
            ) from exc

        if not isinstance(items, list):
            raise serializers.ValidationError("signatures must be a JSON array.")
        if not items:
            raise serializers.ValidationError("At least one signature is required.")
        if len(items) > self.MAX_SIGNATURES:
            raise serializers.ValidationError(
                f"At most {self.MAX_SIGNATURES} signatures per document.",
            )

        validated: list[dict] = []
        for index, item in enumerate(items):
            inner = SignatureItemSerializer(data=item)
            if not inner.is_valid():
                raise serializers.ValidationError(
                    {f"signatures[{index}]": inner.errors},
                )
            validated.append(inner.validated_data)
        return validated
