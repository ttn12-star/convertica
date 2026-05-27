from collections.abc import Callable

from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema


def unlock_zip_docs() -> Callable:
    """Swagger documentation for the Unlock ZIP API."""
    zip_binary_schema = openapi.Schema(
        type=openapi.TYPE_STRING,
        format="binary",
        description="Unlocked ZIP archive.",
        example="(binary file stream)",
    )

    def decorator(func: Callable) -> Callable:
        return swagger_auto_schema(
            operation_description="Remove the password from an encrypted ZIP archive.",
            schema=None,
            manual_parameters=[
                openapi.Parameter(
                    "archive_file",
                    openapi.IN_FORM,
                    description="Password-protected ZIP archive",
                    type=openapi.TYPE_FILE,
                    required=True,
                ),
                openapi.Parameter(
                    "password",
                    openapi.IN_FORM,
                    description="Current password of the archive",
                    type=openapi.TYPE_STRING,
                    required=True,
                ),
            ],
            request_body=None,
            responses={
                200: openapi.Response(
                    description="Unlocked ZIP archive.",
                    content={"application/zip": zip_binary_schema},
                ),
                400: "Bad request (wrong password, not encrypted, invalid archive).",
                413: "File too large.",
            },
        )(func)

    return decorator
