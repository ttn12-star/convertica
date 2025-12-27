"""
Cache utilities for PDF operations.

Provides caching for expensive operations like PDF validation,
page counting, and file size calculations.
"""

import hashlib
from typing import Optional

from django.core.cache import cache


def get_cache_key(prefix: str, *args) -> str:
    """Generate a cache key from prefix and arguments.

    Args:
        prefix: Cache key prefix (e.g., 'pdf_pages', 'pdf_valid')
        *args: Arguments to include in the key

    Returns:
        Cache key string
    """
    key_data = f"{prefix}:{'|'.join(str(arg) for arg in args)}"
    key_hash = hashlib.md5(key_data.encode()).hexdigest()
    return f"{prefix}:{key_hash}"


def cache_pdf_page_count(pdf_path: str, page_count: int, timeout: int = 3600) -> None:
    """Cache PDF page count.

    Args:
        pdf_path: Path to PDF file
        page_count: Number of pages
        timeout: Cache timeout in seconds (default: 1 hour)
    """
    cache_key = get_cache_key("pdf_pages", pdf_path)
    cache.set(cache_key, page_count, timeout=timeout)


def get_cached_pdf_page_count(pdf_path: str) -> int | None:
    """Get cached PDF page count.

    Args:
        pdf_path: Path to PDF file

    Returns:
        Cached page count or None if not cached
    """
    cache_key = get_cache_key("pdf_pages", pdf_path)
    return cache.get(cache_key)


def cache_pdf_validation(pdf_path: str, is_valid: bool, timeout: int = 3600) -> None:
    """Cache PDF validation result.

    Args:
        pdf_path: Path to PDF file
        is_valid: Whether PDF is valid
        timeout: Cache timeout in seconds (default: 1 hour)
    """
    cache_key = get_cache_key("pdf_valid", pdf_path)
    cache.set(cache_key, is_valid, timeout=timeout)


def get_cached_pdf_validation(pdf_path: str) -> bool | None:
    """Get cached PDF validation result.

    Args:
        pdf_path: Path to PDF file

    Returns:
        Cached validation result or None if not cached
    """
    cache_key = get_cache_key("pdf_valid", pdf_path)
    return cache.get(cache_key)


def cache_file_hash(file_path: str, file_hash: str, timeout: int = 86400) -> None:
    """Cache file hash (MD5/SHA256).

    Args:
        file_path: Path to file
        file_hash: File hash
        timeout: Cache timeout in seconds (default: 24 hours)
    """
    cache_key = get_cache_key("file_hash", file_path)
    cache.set(cache_key, file_hash, timeout=timeout)


def get_cached_file_hash(file_path: str) -> str | None:
    """Get cached file hash.

    Args:
        file_path: Path to file

    Returns:
        Cached file hash or None if not cached
    """
    cache_key = get_cache_key("file_hash", file_path)
    return cache.get(cache_key)


def invalidate_pdf_cache(pdf_path: str) -> None:
    """Invalidate all cached data for a PDF file.

    Args:
        pdf_path: Path to PDF file
    """
    cache.delete(get_cache_key("pdf_pages", pdf_path))
    cache.delete(get_cache_key("pdf_valid", pdf_path))
    cache.delete(get_cache_key("file_hash", pdf_path))
