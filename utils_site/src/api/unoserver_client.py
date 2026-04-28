"""
unoserver HTTP client for LibreOffice document conversion.

Provides a fast path via the unoserver daemon (warm LibreOffice instance)
with automatic fallback to LibreOffice subprocess if unavailable.

Architecture:
  Celery worker  ──HTTP──►  unoserver container  ──UNO──►  LibreOffice (warm)
                    └─ fallback ──►  libreoffice subprocess (cold start)

The warm LibreOffice instance in unoserver eliminates the ~10-15s cold-start
overhead that occurs when spawning a new LibreOffice subprocess per conversion.
"""

import os

import requests
from requests.adapters import HTTPAdapter
from src.api.logging_utils import get_logger

logger = get_logger(__name__)

UNOSERVER_URL = os.environ.get("UNOSERVER_URL", "http://unoserver:2003")
# Timeout for the initial TCP connection to unoserver.
# Short so that if unoserver is down we fall back to subprocess quickly.
UNOSERVER_CONNECT_TIMEOUT = float(os.environ.get("UNOSERVER_CONNECT_TIMEOUT", "3"))
# Timeout (seconds) for the full conversion request read.
UNOSERVER_READ_TIMEOUT = int(os.environ.get("UNOSERVER_READ_TIMEOUT", "180"))

# Module-level Session for connection pooling. Each conversion previously did a
# fresh TCP connect; with the worker doing many conversions in succession this
# reuses keep-alive connections to unoserver, shaving ~5-15ms per request.
_session = requests.Session()
_session.mount(
    "http://",
    HTTPAdapter(pool_connections=4, pool_maxsize=8, max_retries=0),
)
_session.mount(
    "https://",
    HTTPAdapter(pool_connections=4, pool_maxsize=8, max_retries=0),
)


def convert_with_unoserver(
    input_path: str,
    output_path: str,
    filterin: str | None = None,
    filterout: str = "pdf",
    timeout: int = UNOSERVER_READ_TIMEOUT,
) -> bool:
    """
    Convert a document to another format via the unoserver HTTP API.

    Sends the input file as binary POST body and writes the response body
    (the converted file) to output_path.

    Args:
        input_path:  Path to the source document.
        output_path: Path where the converted file will be written.
        filterin:    LibreOffice input filter name (e.g. "MS Word 2007 XML").
                     None lets unoserver auto-detect from file content.
        filterout:   LibreOffice output filter / format string
                     (e.g. "pdf", "pdf:writer_pdf_Export").
        timeout:     Maximum seconds to wait for the conversion response.

    Returns:
        True  – conversion completed successfully via unoserver.
        False – unoserver is unavailable (connection refused / timeout);
                caller should fall back to LibreOffice subprocess.

    Raises:
        ConversionError – unoserver returned an HTTP error (4xx/5xx).
    """
    from src.exceptions import ConversionError

    headers: dict[str, str] = {
        "Content-Type": "application/octet-stream",
    }
    if filterin:
        headers["filterin"] = filterin
    if filterout:
        headers["filterout"] = filterout

    try:
        # Stream the request body straight from disk rather than read()-ing the
        # whole file into memory; for 100-200 MB office documents that pulled
        # the file twice (once into bytes, once into the requests buffer).
        with open(input_path, "rb") as fh:
            response = _session.post(
                f"{UNOSERVER_URL}/request",
                data=fh,
                headers=headers,
                timeout=(UNOSERVER_CONNECT_TIMEOUT, timeout),
                stream=True,
            )
            response.raise_for_status()

            response_size = 0
            with open(output_path, "wb") as out:
                for chunk in response.iter_content(chunk_size=64 * 1024):
                    if chunk:
                        out.write(chunk)
                        response_size += len(chunk)

        logger.info(
            "unoserver conversion successful",
            extra={
                "event": "unoserver_success",
                "input": os.path.basename(input_path),
                "output": os.path.basename(output_path),
                "response_size": response_size,
            },
        )
        return True

    except requests.exceptions.ConnectionError:
        logger.warning(
            "unoserver unavailable (connection refused), falling back to subprocess",
            extra={"event": "unoserver_unavailable", "url": UNOSERVER_URL},
        )
        return False

    except requests.exceptions.Timeout:
        logger.warning(
            "unoserver connect timeout, falling back to subprocess",
            extra={"event": "unoserver_timeout", "url": UNOSERVER_URL},
        )
        return False

    except requests.exceptions.HTTPError as exc:
        status = exc.response.status_code if exc.response is not None else "?"
        body = ""
        if exc.response is not None:
            try:
                body = exc.response.text[:500]
            except Exception:
                pass
        logger.error(
            f"unoserver returned HTTP {status}: {body}",
            extra={"event": "unoserver_http_error", "status": status},
        )
        raise ConversionError(
            f"unoserver conversion failed (HTTP {status}): {body}"
        ) from exc
