"""
HTML to PDF conversion utilities using Playwright.

Converts HTML content to PDF using Playwright's print-to-pdf functionality.
Supports both HTML strings and URLs with proper security measures.
"""

import asyncio
import os
import tempfile

from django.utils.text import get_valid_filename
from src.api.file_validation import check_disk_space, sanitize_filename
from src.api.logging_utils import get_logger
from src.exceptions import ConversionError, StorageError

logger = get_logger(__name__)


class HTMLToPDFConverter:
    """HTML to PDF converter using Playwright backend."""

    def __init__(self):
        self.timeout_seconds = 60  # 1 minute timeout for Playwright
        self.max_retries = 2  # Maximum retry attempts

    async def convert_html_to_pdf(
        self,
        html_content: str,
        filename: str = "converted",
        suffix: str = "_convertica",
        context: dict = None,
        is_celery_task: bool = False,
        **options,
    ) -> tuple[str, str]:
        """
        Convert HTML content to PDF using Playwright.

        Args:
            html_content: HTML string to convert
            filename: Base filename for output
            suffix: Suffix for output filename
            context: Logging context
            is_celery_task: Whether running in Celery task
            **options: Additional PDF options (page_size, margins, etc.)

        Returns:
            Tuple of (input_html_path, output_pdf_path)
        """
        if context is None:
            context = {}

        if is_celery_task:
            context["is_celery_task"] = True
            context["conversion_environment"] = "celery_worker"

        # Create temporary directory
        tmp_dir = tempfile.mkdtemp(prefix="html2pdf_")
        context["tmp_dir"] = tmp_dir

        try:
            # Check disk space
            disk_ok, disk_err = check_disk_space(tmp_dir, required_mb=100)
            if not disk_ok:
                raise StorageError(
                    disk_err or "Insufficient disk space", context=context
                )

            # Setup file paths
            safe_name = sanitize_filename(get_valid_filename(filename))
            html_path = os.path.join(tmp_dir, f"{safe_name}.html")
            pdf_name = f"{safe_name}{suffix}.pdf"
            pdf_path = os.path.join(tmp_dir, pdf_name)

            context.update(
                {
                    "html_path": html_path,
                    "pdf_path": pdf_path,
                    "input_filename": safe_name,
                    "conversion_method": "playwright",
                    "options": options,
                }
            )

            # Save HTML content
            await self._save_html_content_async(html_content, html_path, context)

            # Convert using Playwright
            await self._convert_with_playwright_async(
                html_path, pdf_path, context, **options
            )

            # Validate output
            if not os.path.exists(pdf_path):
                raise ConversionError(
                    "Playwright conversion failed - no output file generated",
                    context=context,
                )

            logger.info(
                "HTML to PDF conversion completed successfully",
                extra={
                    **context,
                    "event": "html_to_pdf_success",
                    "output_size": os.path.getsize(pdf_path),
                },
            )

            return html_path, pdf_path

        except Exception as e:
            logger.error(
                f"HTML to PDF conversion failed: {e}",
                extra={**context, "event": "html_to_pdf_error"},
                exc_info=True,
            )
            raise

    async def convert_url_to_pdf(
        self,
        url: str,
        filename: str = "converted",
        suffix: str = "_convertica",
        context: dict = None,
        is_celery_task: bool = False,
        **options,
    ) -> tuple[str, str]:
        """
        Convert URL to PDF using Playwright.

        Args:
            url: URL to convert (must be safe)
            filename: Base filename for output
            suffix: Suffix for output filename
            context: Logging context
            is_celery_task: Whether running in Celery task
            **options: Additional PDF options

        Returns:
            Tuple of (url, output_pdf_path)
        """
        if context is None:
            context = {}

        # Validate URL for security
        is_safe, error = self._validate_url(url)
        if not is_safe:
            raise ConversionError(f"Unsafe URL: {error}", context=context)

        # Create temporary directory
        tmp_dir = tempfile.mkdtemp(prefix="url2pdf_")
        context["tmp_dir"] = tmp_dir

        try:
            # Check disk space
            disk_ok, disk_err = check_disk_space(tmp_dir, required_mb=100)
            if not disk_ok:
                raise StorageError(
                    disk_err or "Insufficient disk space", context=context
                )

            # Setup file paths
            safe_name = sanitize_filename(get_valid_filename(filename))
            pdf_name = f"{safe_name}{suffix}.pdf"
            pdf_path = os.path.join(tmp_dir, pdf_name)

            context.update(
                {
                    "url": url,
                    "pdf_path": pdf_path,
                    "input_filename": safe_name,
                    "conversion_method": "playwright_url",
                    "options": options,
                }
            )

            # Convert URL directly using Playwright
            await self._convert_url_with_playwright_async(
                url, pdf_path, context, **options
            )

            # Validate output
            if not os.path.exists(pdf_path):
                raise ConversionError(
                    "Playwright URL conversion failed - no output file generated",
                    context=context,
                )

            logger.info(
                "URL to PDF conversion completed successfully",
                extra={
                    **context,
                    "event": "url_to_pdf_success",
                    "output_size": os.path.getsize(pdf_path),
                },
            )

            return url, pdf_path

        except Exception as e:
            logger.error(
                f"URL to PDF conversion failed: {e}",
                extra={**context, "event": "url_to_pdf_error"},
                exc_info=True,
            )
            raise

    async def _save_html_content_async(
        self, html_content: str, html_path: str, context: dict
    ) -> None:
        """Save HTML content to file asynchronously."""
        loop = asyncio.get_event_loop()

        def _save_html():
            with open(html_path, "w", encoding="utf-8") as f:
                f.write(html_content)

        try:
            await loop.run_in_executor(None, _save_html)
            logger.debug(
                "HTML content saved successfully",
                extra={**context, "event": "html_content_saved"},
            )
        except Exception as e:
            raise StorageError(f"Failed to save HTML content: {e}", context=context)

    async def _convert_with_playwright_async(
        self, html_path: str, pdf_path: str, context: dict, **options
    ) -> None:
        """Convert HTML file to PDF using Playwright."""
        loop = asyncio.get_event_loop()

        def _convert_with_playwright():
            """Perform Playwright conversion with retry logic."""
            try:
                from playwright.async_api import async_playwright
            except ImportError:
                raise ConversionError(
                    "Playwright is not installed. Install with: pip install playwright",
                    context=context,
                )

            async def _run_conversion():
                async with async_playwright() as p:
                    browser = await p.chromium.launch(headless=True)
                    page = await browser.new_page()

                    try:
                        # Load HTML file
                        await page.goto(f"file://{html_path}")

                        # Wait for page to load
                        await page.wait_for_load_state("networkidle")

                        # Default PDF options
                        pdf_options = {
                            "path": pdf_path,
                            "format": "A4",
                            "print_background": True,
                            "margin": {
                                "top": "1cm",
                                "right": "1cm",
                                "bottom": "1cm",
                                "left": "1cm",
                            },
                        }

                        # Override with custom options
                        pdf_options.update(options)

                        # Generate PDF
                        await page.pdf(**pdf_options)

                        logger.info(
                            "Playwright conversion completed",
                            extra={
                                **context,
                                "event": "playwright_complete",
                                "pdf_options": pdf_options,
                            },
                        )

                    finally:
                        await browser.close()

            # Run async function in sync context

            try:
                loop.run_until_complete(_run_conversion())
            except Exception as e:
                logger.error(
                    f"Playwright conversion failed: {e}",
                    extra={**context, "event": "playwright_error"},
                )
                raise ConversionError(
                    f"Playwright conversion failed: {e}", context=context
                )

        # Perform conversion with retries
        for attempt in range(self.max_retries + 1):
            try:
                await loop.run_in_executor(None, _convert_with_playwright)
                break  # Success, exit retry loop

            except ConversionError:
                if attempt == self.max_retries:
                    logger.error(
                        f"Playwright conversion failed after {self.max_retries + 1} attempts",
                        extra={**context, "event": "playwright_max_retries"},
                    )
                    raise

                logger.warning(
                    f"Playwright conversion attempt {attempt + 1} failed, retrying...",
                    extra={
                        **context,
                        "event": "playwright_retry",
                        "attempt": attempt + 1,
                    },
                )
                await asyncio.sleep(1)  # Brief delay before retry

    async def _convert_url_with_playwright_async(
        self, url: str, pdf_path: str, context: dict, **options
    ) -> None:
        """Convert URL to PDF using Playwright."""
        loop = asyncio.get_event_loop()

        def _convert_url_with_playwright():
            """Perform Playwright URL conversion with retry logic."""
            try:
                from playwright.async_api import async_playwright
            except ImportError:
                raise ConversionError(
                    "Playwright is not installed. Install with: pip install playwright",
                    context=context,
                )

            async def _run_url_conversion():
                async with async_playwright() as p:
                    browser = await p.chromium.launch(headless=True)
                    page = await browser.new_page()

                    try:
                        # Navigate to URL
                        await page.goto(url, wait_until="networkidle")

                        # Wait for page to load completely
                        await page.wait_for_timeout(
                            2000
                        )  # 2 seconds for dynamic content

                        # Default PDF options
                        pdf_options = {
                            "path": pdf_path,
                            "format": "A4",
                            "print_background": True,
                            "margin": {
                                "top": "1cm",
                                "right": "1cm",
                                "bottom": "1cm",
                                "left": "1cm",
                            },
                        }

                        # Override with custom options
                        pdf_options.update(options)

                        # Generate PDF
                        await page.pdf(**pdf_options)

                        logger.info(
                            "Playwright URL conversion completed",
                            extra={
                                **context,
                                "event": "playwright_url_complete",
                                "pdf_options": pdf_options,
                            },
                        )

                    finally:
                        await browser.close()

            # Run async function in sync context

            try:
                loop.run_until_complete(_run_url_conversion())
            except Exception as e:
                logger.error(
                    f"Playwright URL conversion failed: {e}",
                    extra={**context, "event": "playwright_url_error"},
                )
                raise ConversionError(
                    f"Playwright URL conversion failed: {e}", context=context
                )

        # Perform conversion with retries
        for attempt in range(self.max_retries + 1):
            try:
                await loop.run_in_executor(None, _convert_url_with_playwright)
                break  # Success, exit retry loop

            except ConversionError:
                if attempt == self.max_retries:
                    logger.error(
                        f"Playwright URL conversion failed after {self.max_retries + 1} attempts",
                        extra={**context, "event": "playwright_url_max_retries"},
                    )
                    raise

                logger.warning(
                    f"Playwright URL conversion attempt {attempt + 1} failed, retrying...",
                    extra={
                        **context,
                        "event": "playwright_url_retry",
                        "attempt": attempt + 1,
                    },
                )
                await asyncio.sleep(1)  # Brief delay before retry

    def _validate_url(self, url: str) -> tuple[bool, str | None]:
        """
        Validate URL for security (prevent SSRF).

        Args:
            url: URL to validate

        Returns:
            Tuple of (is_safe, error_message)
        """
        from urllib.parse import urlparse

        try:
            parsed = urlparse(url)

            # Only allow HTTP/HTTPS
            if parsed.scheme not in ["http", "https"]:
                return False, "Only HTTP and HTTPS URLs are allowed"

            # Block private IP ranges and localhost
            hostname = parsed.hostname
            if hostname:
                # Block localhost and private IPs
                blocked_hosts = [
                    "localhost",
                    "127.0.0.1",
                    "0.0.0.0",
                    "10.",
                    "172.",
                    "192.168.",
                    "169.254.",
                ]

                for blocked in blocked_hosts:
                    if hostname.startswith(blocked):
                        return (
                            False,
                            f"Access to {hostname} is not allowed for security reasons",
                        )

            return True, None

        except Exception as e:
            return False, f"Invalid URL format: {e}"


# Global converter instance
_html_converter = HTMLToPDFConverter()


async def convert_html_to_pdf(
    html_content: str,
    filename: str = "converted",
    suffix: str = "_convertica",
    **options,
) -> tuple[str, str]:
    """
    Convert HTML content to PDF using Playwright.

    Args:
        html_content: HTML string to convert
        filename: Base filename for output
        suffix: Suffix for output filename
        **options: Additional PDF options

    Returns:
        Tuple of (input_html_path, output_pdf_path)
    """
    return await _html_converter.convert_html_to_pdf(
        html_content, filename, suffix, **options
    )


async def convert_url_to_pdf(
    url: str, filename: str = "converted", suffix: str = "_convertica", **options
) -> tuple[str, str]:
    """
    Convert URL to PDF using Playwright.

    Args:
        url: URL to convert (must be safe)
        filename: Base filename for output
        suffix: Suffix for output filename
        **options: Additional PDF options

    Returns:
        Tuple of (url, output_pdf_path)
    """
    return await _html_converter.convert_url_to_pdf(url, filename, suffix, **options)


def validate_html_content(html_content: str) -> tuple[bool, str | None]:
    """
    Validate HTML content.

    Args:
        html_content: HTML string to validate

    Returns:
        Tuple of (is_valid, error_message)
    """
    if not html_content or not html_content.strip():
        return False, "HTML content is empty"

    # Basic HTML validation
    html_content = html_content.strip()

    # Check for basic HTML structure
    if not ("<html" in html_content.lower() or "<body" in html_content.lower()):
        # Still allow it - could be HTML fragment
        pass

    # Check for potentially dangerous content
    dangerous_patterns = [
        "<script",
        "javascript:",
        "data:",
        "vbscript:",
        "<iframe",
        "<object",
        "<embed",
    ]

    html_lower = html_content.lower()
    for pattern in dangerous_patterns:
        if pattern in html_lower:
            return False, f"HTML contains potentially dangerous content: {pattern}"

    return True, None
