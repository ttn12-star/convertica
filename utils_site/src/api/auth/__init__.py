"""Authentication backends for /api/v1."""

from .web_token import WebTokenAuthentication, mint_web_token

__all__ = ["WebTokenAuthentication", "mint_web_token"]
