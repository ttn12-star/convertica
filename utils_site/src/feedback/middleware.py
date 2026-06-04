"""Attach the feedback token to successful tool-conversion downloads.

`BaseConversionAPIView` (sync) and `TaskResultAPIView` (async) set the
`X-Convertica-Feedback-Token` header themselves. Many other tool views don't:
custom single-file views (merge, split, compress), the `post_async()` path, and
every `BaseBatchAPIView` ZIP response. This middleware closes that gap centrally
by reading the resolved view's ``CONVERSION_TYPE`` and stamping the token on any
successful file-download response that doesn't already carry one — so the
post-conversion rating form appears on every tool.
"""

import logging

logger = logging.getLogger(__name__)

_HEADER = "X-Convertica-Feedback-Token"


class FeedbackTokenResponseMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        try:
            # Already stamped (async result endpoint, or sync base view).
            if response.has_header(_HEADER):
                return response
            if response.status_code != 200:
                return response
            # Only successful file downloads (every tool response sets this).
            if "attachment" not in response.get("Content-Disposition", "").lower():
                return response

            match = getattr(request, "resolver_match", None)
            view_func = getattr(match, "func", None) if match else None
            view_class = getattr(view_func, "view_class", None)
            slug = getattr(view_class, "CONVERSION_TYPE", "") if view_class else ""
            if slug:
                from src.feedback.tokens import create_feedback_token

                response[_HEADER] = create_feedback_token(tool_slug=slug)
        except Exception as exc:  # never break a real download over feedback
            logger.debug("feedback token middleware skipped: %s", exc)
        return response
