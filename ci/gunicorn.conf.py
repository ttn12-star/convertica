"""
Gunicorn configuration file for production.

Key changes from inline config:
- Removed --preload to avoid memory issues with fork() and DB connections
- Added worker lifecycle hooks for better debugging
- Reduced max_requests to prevent memory bloat
- Using sync worker instead of gthread for better stability
"""

import os
import sys

# Server socket
bind = "0.0.0.0:8000"

# Worker processes
# Using sync workers instead of gthread for better stability
# gthread can cause issues with DB connection pooling and memory
workers = int(os.environ.get("GUNICORN_WORKERS", 2))
worker_class = (
    "sync"  # Changed from gthread - more stable, avoids connection pool issues
)
threads = 1  # Not used with sync workers, but kept for documentation

# Timeouts
timeout = 300  # 5 minutes for long conversions
graceful_timeout = 30
keepalive = 5

# Worker lifecycle
# Restart workers after N requests to prevent memory leaks
# Lower value = more frequent restarts = less memory accumulation
max_requests = 100  # Aggressive restart to prevent OOM on 4GB server
max_requests_jitter = 20  # Add randomness to prevent all workers restarting at once

# Use /dev/shm for worker heartbeat files (faster than disk)
worker_tmp_dir = "/dev/shm"

# Logging
accesslog = "-"  # stdout
errorlog = "-"  # stderr
loglevel = "info"
capture_output = True  # Capture stdout/stderr from workers

# Access log format with timing info
access_log_format = '%(h)s %(l)s %(u)s %(t)s "%(r)s" %(s)s %(b)s "%(f)s" "%(a)s" %(D)s'

# DO NOT use preload_app - it can cause issues with:
# - Database connections being shared between forked workers
# - Memory not being properly released after fork
# - Stale connections after worker restart
preload_app = False


# Worker lifecycle hooks for debugging crashes
def on_starting(server):
    """Called just before the master process is initialized."""
    server.log.info("Gunicorn master starting...")


def on_reload(server):
    """Called when SIGHUP is received."""
    server.log.info("Gunicorn reloading configuration...")


def when_ready(server):
    """Called just after the server is started."""
    server.log.info("Gunicorn master ready. Spawning workers...")


def pre_fork(server, worker):
    """Called just before a worker is forked."""
    server.log.debug("Pre-fork: About to spawn worker")


def post_fork(server, worker):
    """Called just after a worker is forked.

    This is the right place to initialize connections that shouldn't
    be shared between workers (like database connections).
    """
    server.log.info(f"Worker {worker.pid} spawned")

    # Close any inherited database connections
    # Django will create new connections when needed
    try:
        from django.db import connections

        for conn in connections.all():
            conn.close()
    except Exception as e:
        server.log.warning(f"Failed to close DB connections in post_fork: {e}")

    # Close Redis connections too
    try:
        from django.core.cache import cache

        cache.close()
    except Exception as e:
        server.log.debug(f"Failed to close cache in post_fork: {e}")


def pre_exec(server):
    """Called just before a new master process is forked."""
    server.log.info("Gunicorn master forking new master...")


def child_exit(server, worker):
    """Called when a worker is terminated.

    This is crucial for debugging - logs when workers die.
    """
    # exitcode may not be available on all worker types (e.g., SyncWorker)
    exit_code = getattr(worker, "exitcode", None)
    server.log.warning(f"Worker {worker.pid} exited (exit code: {exit_code})")

    # Log memory info if available
    try:
        import resource

        usage = resource.getrusage(resource.RUSAGE_CHILDREN)
        server.log.info(
            f"Worker {worker.pid} resource usage: "
            f"max_rss={usage.ru_maxrss}KB, "
            f"user_time={usage.ru_utime}s, "
            f"sys_time={usage.ru_stime}s"
        )
    except Exception:
        pass


def worker_int(worker):
    """Called when a worker receives SIGINT or SIGQUIT."""
    worker.log.warning(f"Worker {worker.pid} received interrupt signal")


def worker_abort(worker):
    """Called when a worker receives SIGABRT.

    This usually happens when the worker timeout is exceeded.
    """
    worker.log.error(f"Worker {worker.pid} was aborted (timeout or SIGABRT)")

    # Try to log what the worker was doing
    try:
        import threading
        import traceback

        # Log all threads
        for thread_id, frame in sys._current_frames().items():
            worker.log.error(f"Thread {thread_id}:")
            for line in traceback.format_stack(frame):
                worker.log.error(line.strip())
    except Exception as e:
        worker.log.error(f"Failed to get stack trace: {e}")


def worker_exit(server, worker):
    """Called just after a worker exits."""
    server.log.info(f"Worker {worker.pid} finished and exited")


def nworkers_changed(server, new_value, old_value):
    """Called when the number of workers changes."""
    server.log.info(f"Number of workers changed: {old_value} -> {new_value}")
