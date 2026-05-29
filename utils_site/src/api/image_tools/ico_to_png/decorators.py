# decorators.py
from collections.abc import Callable

from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema


def ico_to_png_docs() -> Callable:
    """Swagger documentation for the ICO-to-PNG API."""

    png_binary_schema = openapi.Schema(
        type=openapi.TYPE_STRING,
        format="binary",
        description="PNG image extracted from the .ico.",
        example="(binary PNG stream)",
    )

    def decorator(func: Callable) -> Callable:
        return swagger_auto_schema(
            operation_description=(
                "Convert a .ico file to PNG, extracting the largest embedded frame."
            ),
            schema=None,
            manual_parameters=[
                openapi.Parameter(
                    "ico_file",
                    openapi.IN_FORM,
                    description="Source .ico file to convert.",
                    type=openapi.TYPE_FILE,
                    required=True,
                ),
            ],
            request_body=None,
            responses={
                200: openapi.Response(
                    description="Generated PNG file.",
                    content={"image/png": png_binary_schema},
                ),
                400: "Bad request (invalid .ico file, etc.).",
                413: "File too large.",
                500: "Internal server error.",
            },
            consumes=["multipart/form-data"],
        )(func)

    return decorator
