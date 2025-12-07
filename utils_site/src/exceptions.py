"""
Base exceptions for the application.
"""

from typing import Any, Dict, Optional


class ConversionError(Exception):
    """Base exception for conversion failures."""

    def __init__(self, message: str, context: Optional[Dict[str, Any]] = None):
        """
        Args:
            message: Human-readable error message
            context: Additional context for logging (filename, filesize, etc.)
        """
        super().__init__(message)
        self.message = message
        self.context = context or {}

    def __str__(self) -> str:
        return self.message

    def to_dict(self) -> Dict[str, Any]:
        """Convert exception to dictionary for logging/API responses."""
        return {
            "error": self.__class__.__name__,
            "message": self.message,
            "context": self.context,
        }


class EncryptedPDFError(ConversionError):
    """Raised when a PDF is password-protected or encrypted."""


class InvalidPDFError(ConversionError):
    """Raised when PDF structure is invalid or cannot be parsed."""


class StorageError(ConversionError):
    """Raised when file system / storage operations fail."""
