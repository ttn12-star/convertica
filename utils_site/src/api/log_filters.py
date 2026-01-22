"""
Custom log filters to suppress noisy log messages from bot scanners.
"""

import logging


class SuppressDisallowedHostFilter(logging.Filter):
    """
    Filter out DisallowedHost errors from logs.

    These errors are caused by bot scanners and proxy attacks sending requests
    with invalid Host headers. They are not real errors and just create noise.

    Examples of filtered messages:
    - "Invalid HTTP_HOST header: 'httpbin.org'"
    - "Invalid HTTP_HOST header: '0.0.0.0:8000'"
    - "DisallowedHost at /"
    """

    SUPPRESSED_PATTERNS = [
        "DisallowedHost",
        "Invalid HTTP_HOST header",
        "mstshash",  # RDP scanner
        "Invalid HTTP request line",
    ]

    def filter(self, record):
        message = record.getMessage()
        return all(pattern not in message for pattern in self.SUPPRESSED_PATTERNS)
