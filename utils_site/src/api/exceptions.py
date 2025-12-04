# exceptions.py
class ConversionError(Exception):
    """Base exception for conversion failures."""


class EncryptedPDFError(ConversionError):
    """Raised when a PDF is password-protected or encrypted."""


class InvalidPDFError(ConversionError):
    """Raised when PDF structure is invalid or cannot be parsed."""


class StorageError(ConversionError):
    """Raised when file system / storage operations fail."""
