"""
Base exceptions for the application.
"""

from typing import Any


class ConversionError(Exception):
    """Base exception for conversion failures."""

    def __init__(self, message: str, context: dict[str, Any] | None = None):
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

    def to_dict(self) -> dict[str, Any]:
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


class OCRFailedError(ConversionError):
    """OCR was requested and failed on every page: report it, don't degrade."""

    retryable = False  # a missing language pack fails the same way again


class StorageError(ConversionError):
    """Raised when file system / storage operations fail."""


class EncryptedArchiveError(EncryptedPDFError):
    """Raised for archive password problems (already protected / wrong password).

    Subclasses EncryptedPDFError so the API base view returns HTTP 400 with the
    message shown verbatim to the user.
    """


class InvalidArchiveError(InvalidPDFError):
    """Raised when an uploaded archive is invalid/corrupt or exceeds safety guards.

    Subclasses InvalidPDFError so the API base view returns HTTP 400.
    """


# Parser errors that mean "this file is damaged", not "our code failed".
_DAMAGED_INPUT_ERRORS = (
    # (top-level package, class name): libraries move their exceptions between
    # modules across versions (pdfminer's PSException: psparser in 20231228,
    # psexceptions later), so the exact module path is not compared.
    ("pypdf", "PyPdfError"),
    ("pymupdf", "FileDataError"),
    ("pymupdf", "FzErrorFormat"),
    ("pymupdf", "FzErrorArgument"),
    ("pdfminer", "PSException"),  # base of PSEOF and every PDFException
    ("pdfplumber", "PdfminerException"),
)


def caused_by_damaged_input(error: BaseException) -> bool:
    """Whether a converter's error is really the parser rejecting the file.

    Converters wrap such errors in a ConversionError, which reads as a 500
    ("Internal server error") for what is the user's truncated or corrupt PDF.
    Follows only explicit `raise ... from` links: an implicit __context__
    means our own code failed while handling a parser error (a typo in an
    except clause, say), and that must stay a 500. Matched by class name so
    no parser has to be importable here.
    """
    seen = set()
    while error is not None and id(error) not in seen:
        seen.add(id(error))
        if isinstance(error, InvalidPDFError):  # already judged the input's fault
            return True
        # PIL reports a cut-off JPEG/PNG as a plain OSError.
        if isinstance(error, OSError) and (
            "image file is truncated" in str(error)
            or "Truncated File Read" in str(error)
        ):
            return True
        for klass in type(error).__mro__:
            package = klass.__module__.split(".", 1)[0]
            if (package, klass.__name__) in _DAMAGED_INPUT_ERRORS:
                return True
        error = error.__cause__
    return False
