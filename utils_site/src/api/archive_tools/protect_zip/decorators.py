from collections.abc import Callable

from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema


def protect_zip_docs() -> Callable:
    """Swagger documentation for the Protect ZIP API."""
    zip_binary_schema = openapi.Schema(
        type=openapi.TYPE_STRING,
        format="binary",
        description="Password-protected ZIP archive.",
        example="(binary file stream)",
    )

    def decorator(func: Callable) -> Callable:
        return swagger_auto_schema(
            operation_description="Encrypt a ZIP archive with an AES-256 password.",
            schema=None,
            manual_parameters=[
                openapi.Parameter(
                    "archive_file",
                    openapi.IN_FORM,
                    description="ZIP archive to protect",
                    type=openapi.TYPE_FILE,
                    required=True,
                ),
                openapi.Parameter(
                    "password",
                    openapi.IN_FORM,
                    description="Password to encrypt the archive",
                    type=openapi.TYPE_STRING,
                    required=True,
                ),
            ],
            request_body=None,
            responses={
                200: openapi.Response(
                    description="Password-protected ZIP archive.",
                    content={"application/zip": zip_binary_schema},
                ),
                400: "Bad request (invalid/encrypted/oversized archive, empty password).",
                413: "File too large.",
            },
        )(func)

    return decorator
