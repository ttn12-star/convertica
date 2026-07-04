"""
Performance configuration for different server environments.
Provides adaptive optimization based on available resources.
"""

import os

import psutil

from .logging_utils import get_logger

logger = get_logger(__name__)


class PerformanceConfig:
    """
    Adaptive performance configuration based on server resources.
    """

    def __init__(self):
        self.total_memory_gb = self._get_total_memory_gb()
        self.cpu_count = os.cpu_count() or 2
        self.config = self._determine_config()

    def _get_total_memory_gb(self) -> float:
        """Get the memory budget (GB) that should drive the performance tier.

        Prefers the container cgroup limit over host RAM: psutil.virtual_memory()
        reports the whole HOST (e.g. 4 GB) while the worker container is capped
        far lower (1.5 GB, ~750 MB per prefork child). Using host RAM picked a
        too-generous tier and defeated the OOM safety margin (CONVERTICA-59).
        """
        # Explicit override wins (set to the per-worker budget in prod).
        env_memory = os.environ.get("SERVER_MEMORY_GB")
        if env_memory:
            try:
                return float(env_memory)
            except ValueError:
                logger.warning("Invalid SERVER_MEMORY_GB value: %s", env_memory)

        try:
            host_gb = psutil.virtual_memory().total / (1024**3)
        except Exception:
            host_gb = 4.0  # Default fallback for 4GB dev server

        cgroup_gb = self._cgroup_limit_gb()
        if cgroup_gb is not None:
            return min(cgroup_gb, host_gb)
        return host_gb

    @staticmethod
    def _cgroup_limit_gb() -> float | None:
        """Container memory limit in GB from cgroup v2 then v1.

        Returns None when there is no limit (bare host, "max", or an unlimited
        sentinel), so the caller falls back to host RAM.
        """
        for path in (
            "/sys/fs/cgroup/memory.max",  # cgroup v2
            "/sys/fs/cgroup/memory/memory.limit_in_bytes",  # cgroup v1
        ):
            try:
                with open(path) as fh:
                    raw = fh.read().strip()
            except OSError:
                continue
            if raw == "max":
                return None
            try:
                gb = int(raw) / (1024**3)
            except ValueError:
                continue
            # cgroup v1 "unlimited" is a huge sentinel (~8 EB); anything above a
            # plausible container size means "no real limit".
            if gb <= 0 or gb > 1024:
                return None
            return gb
        return None

    def _determine_config(self) -> dict[str, any]:
        """Determine configuration based on available resources."""
        if self.total_memory_gb >= 16:
            return self._get_high_performance_config()
        elif self.total_memory_gb >= 8:
            return self._get_medium_performance_config()
        elif self.total_memory_gb >= 4:
            return self._get_low_performance_config()
        else:
            return self._get_minimal_config()

    def _get_high_performance_config(self) -> dict[str, any]:
        """Configuration for 16GB+ servers."""
        config = {
            "enable_optimization": True,
            "parallel_processing": True,
            "thread_pool_workers": {
                "batch_processing": 4,
                "image_processing": 6,
                "ocr_processing": 3,
            },
            "batch_sizes": {"pdf_pages": 20, "image_processing": 15, "ocr_pages": 10},
            "memory_limits": {
                "max_batch_memory_mb": 1000,
                "ocr_text_limit": 100000,
                "pdf2image_dpi": 300,
            },
            "timeouts": {
                "libreoffice": 300,
                "pdf_conversion": 600,
                "ocr_processing": 180,
            },
            "retry_settings": {"max_retries": 3, "retry_delay": 30},
        }
        logger.info(f"High performance config loaded: {self.total_memory_gb:.1f}GB RAM")
        return config

    def _get_medium_performance_config(self) -> dict[str, any]:
        """Configuration for 8GB servers."""
        config = {
            "enable_optimization": True,
            "parallel_processing": True,
            "thread_pool_workers": {
                "batch_processing": 3,
                "image_processing": 4,
                "ocr_processing": 2,
            },
            "batch_sizes": {"pdf_pages": 10, "image_processing": 8, "ocr_pages": 5},
            "memory_limits": {
                "max_batch_memory_mb": 700,
                "ocr_text_limit": 75000,
                "pdf2image_dpi": 250,
            },
            "timeouts": {
                "libreoffice": 240,
                "pdf_conversion": 480,
                "ocr_processing": 150,
            },
            "retry_settings": {"max_retries": 2, "retry_delay": 45},
        }
        logger.info(
            f"Medium performance config loaded: {self.total_memory_gb:.1f}GB RAM"
        )
        return config

    def _get_low_performance_config(self) -> dict[str, any]:
        """Configuration for 4GB servers (current setup)."""
        config = {
            "enable_optimization": True,
            "parallel_processing": True,
            "thread_pool_workers": {
                "batch_processing": 2,
                "image_processing": 3,
                "ocr_processing": 1,
            },
            "batch_sizes": {"pdf_pages": 5, "image_processing": 4, "ocr_pages": 3},
            "memory_limits": {
                "max_batch_memory_mb": 500,
                "ocr_text_limit": 50000,
                "pdf2image_dpi": 200,
            },
            "timeouts": {
                "libreoffice": 180,
                "pdf_conversion": 300,
                "ocr_processing": 120,
            },
            "retry_settings": {"max_retries": 2, "retry_delay": 60},
        }
        logger.info(f"Low performance config loaded: {self.total_memory_gb:.1f}GB RAM")
        return config

    def _get_minimal_config(self) -> dict[str, any]:
        """Configuration for <4GB servers (minimal optimization)."""
        config = {
            "enable_optimization": False,  # Disable optimization for very low memory
            "parallel_processing": False,
            "thread_pool_workers": {
                "batch_processing": 1,
                "image_processing": 1,
                "ocr_processing": 1,
            },
            "batch_sizes": {"pdf_pages": 2, "image_processing": 2, "ocr_pages": 1},
            "memory_limits": {
                "max_batch_memory_mb": 200,
                "ocr_text_limit": 25000,
                "pdf2image_dpi": 150,
            },
            "timeouts": {
                "libreoffice": 120,
                "pdf_conversion": 180,
                "ocr_processing": 60,
            },
            "retry_settings": {"max_retries": 1, "retry_delay": 90},
        }
        logger.warning(
            f"Minimal config loaded: {self.total_memory_gb:.1f}GB RAM - optimization disabled"
        )
        return config

    def get_config(self) -> dict[str, any]:
        """Get current performance configuration."""
        return self.config

    def is_optimization_enabled(self) -> bool:
        """Check if optimization is enabled for current environment."""
        return self.config.get("enable_optimization", False)

    def get_thread_workers(self, pool_type: str) -> int:
        """Get thread worker count for specific pool type."""
        return self.config.get("thread_pool_workers", {}).get(pool_type, 1)

    def get_batch_size(self, operation_type: str) -> int:
        """Get batch size for specific operation type."""
        return self.config.get("batch_sizes", {}).get(operation_type, 2)

    def get_memory_limit(self, limit_type: str) -> int:
        """Get memory limit for specific type."""
        return self.config.get("memory_limits", {}).get(limit_type, 200)

    def get_timeout(self, operation_type: str) -> int:
        """Get timeout for specific operation type."""
        return self.config.get("timeouts", {}).get(operation_type, 120)

    def can_use_parallel_processing(self) -> bool:
        """Check if parallel processing is recommended."""
        return self.config.get("parallel_processing", False)


# Global performance configuration instance
performance_config = PerformanceConfig()


def get_performance_config() -> PerformanceConfig:
    """Get global performance configuration instance."""
    return performance_config


def is_optimization_safe() -> bool:
    """Check if optimization is safe for current environment."""
    return performance_config.is_optimization_enabled()


def get_safe_workers(pool_type: str) -> int:
    """Get safe number of workers for current environment."""
    return performance_config.get_thread_workers(pool_type)


def get_safe_batch_size(operation_type: str) -> int:
    """Get safe batch size for current environment."""
    return performance_config.get_batch_size(operation_type)
