"""
Central optimization manager for Convertica.
Clean, organized system for adaptive resource management.
"""

import asyncio
import inspect
import os

import psutil
from django.core.files.uploadedfile import UploadedFile

from .logging_utils import get_logger

logger = get_logger(__name__)


def _filter_kwargs_for_callable(func, provided_kwargs: dict) -> dict:
    sig = inspect.signature(func)
    params = sig.parameters
    accepts_var_kw = any(
        p.kind == inspect.Parameter.VAR_KEYWORD for p in params.values()
    )
    if accepts_var_kw:
        return provided_kwargs
    return {k: v for k, v in provided_kwargs.items() if k in params}


class OptimizationManager:
    """
    Central manager for all optimization decisions and resource monitoring.
    """

    def __init__(self):
        self.total_memory_gb = self._get_memory_gb()
        self.cpu_count = os.cpu_count() or 2
        self.config = self._load_config()
        self._decision_cache = {}

    def _get_memory_gb(self) -> float:
        """Get total system memory in GB."""
        try:
            return psutil.virtual_memory().total / (1024**3)
        except Exception:
            return 4.0

    def _load_config(self) -> dict[str, any]:
        """Load configuration based on available resources."""
        if self.total_memory_gb >= 16:
            return self._high_performance_config()
        elif self.total_memory_gb >= 8:
            return self._medium_performance_config()
        elif self.total_memory_gb >= 4:
            return self._low_performance_config()
        else:
            return self._minimal_config()

    def _high_performance_config(self) -> dict[str, any]:
        """16GB+ server configuration."""
        return {
            "optimization_enabled": True,
            "parallel_processing": True,
            "thread_workers": {"batch": 4, "image": 6, "ocr": 3},
            "batch_sizes": {"pdf": 20, "image": 15, "ocr": 10},
            "memory_limits": {"batch_mb": 1000, "ocr_text": 100000, "dpi": 300},
            "timeouts": {"libreoffice": 300, "pdf": 600, "ocr": 180},
        }

    def _medium_performance_config(self) -> dict[str, any]:
        """8GB server configuration."""
        return {
            "optimization_enabled": True,
            "parallel_processing": True,
            "thread_workers": {"batch": 3, "image": 4, "ocr": 2},
            "batch_sizes": {"pdf": 10, "image": 8, "ocr": 5},
            "memory_limits": {"batch_mb": 700, "ocr_text": 75000, "dpi": 250},
            "timeouts": {"libreoffice": 240, "pdf": 480, "ocr": 150},
        }

    def _low_performance_config(self) -> dict[str, any]:
        """4GB server configuration."""
        return {
            "optimization_enabled": True,
            "parallel_processing": True,
            "thread_workers": {"batch": 2, "image": 3, "ocr": 1},
            "batch_sizes": {"pdf": 5, "image": 4, "ocr": 3},
            "memory_limits": {"batch_mb": 500, "ocr_text": 50000, "dpi": 200},
            "timeouts": {"libreoffice": 180, "pdf": 300, "ocr": 120},
        }

    def _minimal_config(self) -> dict[str, any]:
        """<4GB server configuration."""
        return {
            "optimization_enabled": False,
            "parallel_processing": False,
            "thread_workers": {"batch": 1, "image": 1, "ocr": 1},
            "batch_sizes": {"pdf": 2, "image": 2, "ocr": 1},
            "memory_limits": {"batch_mb": 200, "ocr_text": 25000, "dpi": 150},
            "timeouts": {"libreoffice": 120, "pdf": 180, "ocr": 60},
        }

    def should_optimize(self, converter_type: str, file_size_mb: float = 0) -> bool:
        """Make intelligent optimization decision."""
        cache_key = f"{converter_type}_{file_size_mb}"
        if cache_key in self._decision_cache:
            return self._decision_cache[cache_key]

        # Base checks
        if not self.config["optimization_enabled"]:
            decision = False
            reason = "Optimization disabled"
        elif file_size_mb > 50 and self.total_memory_gb < 8:
            decision = False
            reason = "Large file on memory-constrained server"
        elif self._get_memory_usage() > 85:
            decision = False
            reason = "High memory usage"
        else:
            decision = True
            reason = "Resources adequate"

        self._decision_cache[cache_key] = decision
        logger.info(f"Optimization {decision} for {converter_type}: {reason}")
        return decision

    def _get_memory_usage(self) -> float:
        """Get current memory usage percentage."""
        try:
            return psutil.virtual_memory().percent
        except Exception:
            return 0.0

    async def convert_pdf_to_jpg(
        self, uploaded_file: UploadedFile, **kwargs
    ) -> tuple[str, str]:
        """Adaptive PDF to JPG conversion."""
        # Skip optimization for Celery tasks to avoid conflicts
        if kwargs.get("is_celery_task", False):
            from .pdf_convert.pdf_to_jpg.utils import convert_pdf_to_jpg_sequential

            # Remove Celery-specific kwargs
            filtered_kwargs = {k: v for k, v in kwargs.items() if k != "is_celery_task"}
            filtered_kwargs = _filter_kwargs_for_callable(
                convert_pdf_to_jpg_sequential, filtered_kwargs
            )
            return await asyncio.to_thread(
                convert_pdf_to_jpg_sequential, uploaded_file, **filtered_kwargs
            )

        # Try optimized version if available
        try:
            from .pdf_convert.pdf_to_jpg_optimized import convert_pdf_to_jpg_optimized

            if self.should_optimize("pdf_to_jpg", uploaded_file.size / (1024 * 1024)):
                try:
                    return await convert_pdf_to_jpg_optimized(uploaded_file, **kwargs)
                except Exception as e:
                    logger.warning(f"Optimized conversion failed: {e}")
        except ImportError:
            logger.debug("Optimized PDF to JPG module not available, using fallback")

        # Fallback
        from .pdf_convert.pdf_to_jpg.utils import convert_pdf_to_jpg_sequential

        # Remove Celery-specific kwargs
        filtered_kwargs = {k: v for k, v in kwargs.items() if k != "is_celery_task"}
        filtered_kwargs = _filter_kwargs_for_callable(
            convert_pdf_to_jpg_sequential, filtered_kwargs
        )
        return await asyncio.to_thread(
            convert_pdf_to_jpg_sequential, uploaded_file, **filtered_kwargs
        )

    async def convert_jpg_to_pdf(
        self, uploaded_file: UploadedFile, **kwargs
    ) -> tuple[str, str]:
        """Adaptive JPG to PDF conversion."""
        # Skip optimization for Celery tasks to avoid conflicts
        if kwargs.get("is_celery_task", False):
            from .pdf_convert.jpg_to_pdf.utils import (
                convert_jpg_to_pdf as _convert_jpg_to_pdf_sync,
            )

            return await _convert_jpg_to_pdf_sync(
                uploaded_file, suffix=kwargs.get("suffix", "_convertica"), **kwargs
            )

        if self.should_optimize("jpg_to_pdf", uploaded_file.size / (1024 * 1024)):
            from .pdf_convert.jpg_to_pdf_optimized import convert_jpg_to_pdf_optimized

            try:
                return await convert_jpg_to_pdf_optimized(uploaded_file, **kwargs)
            except Exception as e:
                logger.warning(f"Optimized conversion failed: {e}")

        # Fallback
        from .pdf_convert.jpg_to_pdf.utils import _convert_jpg_to_pdf_sequential

        return await _convert_jpg_to_pdf_sequential(uploaded_file, **kwargs)

    async def convert_pdf_to_docx(
        self, uploaded_file: UploadedFile, **kwargs
    ) -> tuple[str, str]:
        """Adaptive PDF to DOCX conversion."""
        # Skip optimization for Celery tasks to avoid conflicts
        if kwargs.get("is_celery_task", False):
            from .pdf_convert.pdf_to_word.utils import _convert_pdf_to_docx_sequential

            return await _convert_pdf_to_docx_sequential(
                uploaded_file,
                kwargs.get("suffix", "_convertica"),
                kwargs.get("ocr_enabled", False),
                {},
                kwargs.get("ocr_language", "auto"),
            )

        if self.should_optimize("pdf_to_docx", uploaded_file.size / (1024 * 1024)):
            from .pdf_convert.pdf_to_word_optimized import convert_pdf_to_docx_optimized

            try:
                return await convert_pdf_to_docx_optimized(uploaded_file, **kwargs)
            except Exception as e:
                logger.warning(f"Optimized conversion failed: {e}")

        # Fallback
        from .pdf_convert.pdf_to_word.utils import _convert_pdf_to_docx_sequential

        return await _convert_pdf_to_docx_sequential(
            uploaded_file,
            kwargs.get("suffix", "_convertica"),
            kwargs.get("ocr_enabled", False),
            kwargs.get("context") or {},
            kwargs.get("ocr_language", "auto"),
        )

    async def convert_word_to_pdf(
        self, uploaded_file: UploadedFile, **kwargs
    ) -> tuple[str, str]:
        """Adaptive Word to PDF conversion."""
        # Skip optimization for Celery tasks to avoid conflicts
        if kwargs.get("is_celery_task", False):
            from .pdf_convert.word_to_pdf_optimized import convert_word_to_pdf_optimized

            filtered_kwargs = _filter_kwargs_for_callable(
                convert_word_to_pdf_optimized, kwargs
            )
            return await convert_word_to_pdf_optimized(uploaded_file, **filtered_kwargs)

        # Temporarily disable optimized version due to validation issues
        # if self.should_optimize("word_to_pdf", uploaded_file.size / (1024*1024)):
        #     from .pdf_convert.word_to_pdf_optimized import convert_word_to_pdf_optimized
        #     try:
        #         return await convert_word_to_pdf_optimized(uploaded_file, **kwargs)
        #     except Exception as e:
        #         logger.warning(f"Optimized conversion failed: {e}")

        # Use fallback directly
        from .pdf_convert.word_to_pdf.utils import (
            convert_word_to_pdf as _convert_word_to_pdf_sync,
        )

        return await _convert_word_to_pdf_sync(uploaded_file, **kwargs)

    def get_status(self) -> dict[str, any]:
        """Get current optimization status."""
        return {
            "memory_gb": self.total_memory_gb,
            "cpu_count": self.cpu_count,
            "memory_usage": self._get_memory_usage(),
            "optimization_enabled": self.config["optimization_enabled"],
            "parallel_processing": self.config["parallel_processing"],
            "cached_decisions": len(self._decision_cache),
        }


# Global instance
optimization_manager = OptimizationManager()


# Public API
async def convert_pdf_to_jpg(uploaded_file: UploadedFile, **kwargs) -> tuple[str, str]:
    """Convert PDF to JPG with adaptive optimization."""
    return await optimization_manager.convert_pdf_to_jpg(uploaded_file, **kwargs)


async def convert_jpg_to_pdf(uploaded_file: UploadedFile, **kwargs) -> tuple[str, str]:
    """Convert JPG to PDF with adaptive optimization."""
    return await optimization_manager.convert_jpg_to_pdf(uploaded_file, **kwargs)


async def convert_pdf_to_docx(uploaded_file: UploadedFile, **kwargs) -> tuple[str, str]:
    """Convert PDF to DOCX with adaptive optimization."""
    return await optimization_manager.convert_pdf_to_docx(uploaded_file, **kwargs)


async def convert_word_to_pdf(uploaded_file: UploadedFile, **kwargs) -> tuple[str, str]:
    """Convert Word to PDF with adaptive optimization."""
    return await optimization_manager.convert_word_to_pdf(uploaded_file, **kwargs)


def get_optimization_status() -> dict[str, any]:
    """Get current optimization status."""
    return optimization_manager.get_status()
