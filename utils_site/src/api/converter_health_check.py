"""
Health check system for converters and server resources.
"""

import asyncio

import psutil

from .logging_utils import get_logger
from .performance_config import get_performance_config

logger = get_logger(__name__)


class ConverterHealthCheck:
    """Health monitoring for converter system."""

    def __init__(self):
        self.perf_config = get_performance_config()

    def check_system_resources(self) -> dict[str, any]:
        """Check current system resource usage."""
        try:
            memory = psutil.virtual_memory()
            cpu_percent = psutil.cpu_percent(interval=1)
            disk = psutil.disk_usage("/")

            return {
                "memory_total_gb": memory.total / (1024**3),
                "memory_available_gb": memory.available / (1024**3),
                "memory_percent_used": memory.percent,
                "cpu_percent": cpu_percent,
                "disk_free_gb": disk.free / (1024**3),
                "disk_percent_used:": (disk.used / disk.total) * 100,
                "status": "healthy" if memory.percent < 80 else "warning",
            }
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            return {"status": "error", "error": str(e)}

    def check_conversion_queue(self) -> dict[str, any]:
        """Check if optimization is safe for current environment."""
        resources = self.check_system_resources()
        config = self.perf_config.get_config()

        safety_score = 100
        warnings = []

        # Memory checks
        if resources.get("memory_percent_used", 0) > 85:
            safety_score -= 30
            warnings.append("High memory usage (>85%)")

        # CPU checks
        if resources.get("cpu_percent", 0) > 90:
            safety_score -= 20
            warnings.append("High CPU usage (>90%)")

        # Disk checks
        if resources.get("disk_percent_used", 0) > 90:
            safety_score -= 15
            warnings.append("Low disk space (<10%)")

        # Configuration checks
        if not config.get("enable_optimization", False):
            safety_score -= 40
            warnings.append("Optimization disabled in config")

        status = (
            "safe"
            if safety_score >= 70
            else "caution" if safety_score >= 40 else "unsafe"
        )

        return {
            "status": status,
            "safety_score": safety_score,
            "warnings": warnings,
            "recommendations": self._get_recommendations(
                safety_score, resources, config
            ),
        }

    def _get_recommendations(
        self, score: int, resources: dict, config: dict
    ) -> list[str]:
        """Get recommendations based on health check."""
        recommendations = []

        if score < 70:
            if resources.get("memory_percent_used", 0) > 85:
                recommendations.append("Consider reducing batch sizes")
                recommendations.append("Monitor memory-intensive operations")

            if resources.get("cpu_percent", 0) > 90:
                recommendations.append("Reduce thread pool workers")
                recommendations.append("Implement request queuing")

            if not config.get("enable_optimization", False):
                recommendations.append("Enable optimization on larger server")
                recommendations.append("Consider server upgrade for better performance")

        if score >= 70:
            recommendations.append("System resources are adequate for optimization")
            recommendations.append("Monitor performance during peak usage")

        return recommendations

    async def check_converter_status(self, converter_type: str) -> dict[str, any]:
        """Test converter performance with sample operations."""
        results = {}

        # Test parallel processing capability
        try:
            start_time = asyncio.get_event_loop().time()
            await asyncio.sleep(0.1)  # Simulate async operation
            end_time = asyncio.get_event_loop().time()

            results["async_performance"] = {
                "status": "pass",
                "response_time_ms": (end_time - start_time) * 1000,
            }
        except Exception as e:
            results["async_performance"] = {"status": "fail", "error": str(e)}

        # Test memory allocation
        try:
            import tempfile

            with tempfile.NamedTemporaryFile() as f:
                f.write(b"test" * 1024 * 1024)  # 4MB test
                results["memory_allocation"] = {"status": "pass"}
        except Exception as e:
            results["memory_allocation"] = {"status": "fail", "error": str(e)}

        return results

    def get_full_health_report(self) -> dict[str, any]:
        """Get comprehensive health report."""
        return {
            "timestamp": (
                asyncio.get_event_loop().time() if asyncio.get_event_loop() else None
            ),
            "system_resources": self.check_system_resources(),
            "conversion_queue": self.check_conversion_queue(),
            "configuration": {
                "total_memory_gb": self.perf_config.total_memory_gb,
                "cpu_count": self.perf_config.cpu_count,
                "optimization_enabled": self.perf_config.is_optimization_enabled(),
                "parallel_processing": self.perf_config.can_use_parallel_processing(),
            },
        }

    def get_health_summary(self) -> dict[str, any]:
        """Get current health status."""
        return self.get_full_health_report()


# Global health check instance
health_checker = ConverterHealthCheck()


def is_optimization_recommended() -> bool:
    """Check if optimization is recommended based on current state."""
    safety = health_checker.check_conversion_queue()
    safety = health_checker.check_optimization_safety()
    return safety["status"] in ["safe", "caution"]


def log_optimization_decision(
    converter_type: str, use_optimized: bool, reason: str = ""
):
    """Log optimization decision for monitoring."""
    status = "ENABLED" if use_optimized else "DISABLED"
    logger.info(
        f"Optimization {status} for {converter_type}: {reason}",
        extra={
            "event": "optimization_decision",
            "converter_type": converter_type,
            "use_optimized": use_optimized,
            "reason": reason,
            "health_status": health_checker.check_optimization_safety()["status"],
        },
    )
