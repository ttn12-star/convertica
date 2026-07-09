"""Shared Swagger docs for batch (multi-file) conversion endpoints.

Batch processing is a premium feature — the free plan is limited to one file
per request — so every batch endpoint can return ``403``. The single-file
``*_docs`` decorators deliberately omit ``403`` because their single-file
endpoints are free; this helper documents the batch contract (multipart files
-> ZIP, plus the ``403``/``400``/``413`` responses the base view already
returns) in one place instead of each batch view reusing the single decorator.

The decorator only produces OpenAPI metadata; it has no effect on request
handling at runtime.
"""

from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema


def batch_premium_docs(*, summary, file_field="pdf_files", tags=None):
    """Build a ``swagger_auto_schema`` decorator for a premium batch endpoint."""
    kwargs = {
        "operation_summary": summary,
        "operation_description": (
            "Batch (multi-file) processing. Premium feature: the free plan is "
            "limited to one file per request. Returns a ZIP archive of the "
            "processed files."
        ),
        "manual_parameters": [
            openapi.Parameter(
                file_field,
                openapi.IN_FORM,
                description="Files to process (repeat the field for each file).",
                type=openapi.TYPE_FILE,
                required=True,
            ),
        ],
        "request_body": None,
        "consumes": ["multipart/form-data"],
        "responses": {
            200: openapi.Response(description="ZIP archive of processed files."),
            400: "Bad request - invalid files or parameters.",
            403: "Premium subscription required (batch processing).",
            413: "File too large.",
            500: "Processing failed.",
        },
    }
    if tags is not None:
        kwargs["tags"] = tags
    return swagger_auto_schema(**kwargs)
