# decorators.py
from collections.abc import Callable

from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema


def password_protect_image_docs() -> Callable:
    """Swagger docs for the password-protect-image API."""
    pdf_binary_schema = openapi.Schema(
        type=openapi.TYPE_STRING,
        format="binary",
        description="Password-protected PDF containing the image(s).",
        example="(binary file stream)",
    )

    def decorator(func: Callable) -> Callable:
        return swagger_auto_schema(
            operation_description=(
                "Turn one or more images into a single AES-256 password-"
                "protected PDF. The PDF requires the password to open."
            ),
            schema=None,
            manual_parameters=[
                openapi.Parameter(
                    "image_files",
                    openapi.IN_FORM,
                    description="Image file(s) to protect (send multiple for multiple).",
                    type=openapi.TYPE_FILE,
                    required=True,
                ),
                openapi.Parameter(
                    "password",
                    openapi.IN_FORM,
                    description="Password to protect the output PDF",
                    type=openapi.TYPE_STRING,
                    required=True,
                ),
                openapi.Parameter(
                    "user_password",
                    openapi.IN_FORM,
                    description="User password (optional). If not provided, 'password' will be used",
                    type=openapi.TYPE_STRING,
                    required=False,
                ),
                openapi.Parameter(
                    "owner_password",
                    openapi.IN_FORM,
                    description="Owner password (optional). If not provided, 'password' will be used",
                    type=openapi.TYPE_STRING,
                    required=False,
                ),
            ],
            request_body=None,
            responses={
                200: openapi.Response(
                    description="Password-protected PDF.",
                    content={"application/pdf": pdf_binary_schema},
                ),
                400: "Bad request (invalid image, empty password, too many files).",
                413: "File too large.",
                500: "Internal server error.",
            },
            consumes=["multipart/form-data"],
        )(func)

    return decorator
