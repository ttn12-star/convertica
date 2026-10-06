"""Stop conversion work left running in a thread after its task gave up.

A Celery task runs blocking converters (pdf2docx, OCR, compress) in executor
threads. On a soft time limit or a cancel the task ends, but Python cannot
kill a thread: it ran on for minutes, holding the GIL and making the next
tasks in the same worker child 10-30x slower (the hard limit is per task, so
it never fired). tasks._run_coro marks such threads; long loops call check()
between pages and the thread unwinds at the next one.
"""

import threading

_FLAG = "_convertica_stop"


class Stopped(BaseException):
    """BaseException so converters' `except Exception` cannot swallow it."""


def request_stop(threads) -> None:
    for thread in threads:
        # On the thread object, not its ident: idents are reused by the next
        # task's fresh threads, which must not inherit the stop.
        setattr(thread, _FLAG, True)


def check() -> None:
    if getattr(threading.current_thread(), _FLAG, False):
        raise Stopped("conversion abandoned by its task")


_pdf2docx_hooked = False


def install_pdf2docx_hook() -> None:
    """Check before every page in pdf2docx's two slow per-page loops."""
    global _pdf2docx_hooked
    if _pdf2docx_hooked:
        return
    from pdf2docx.page.Page import Page
    from pdf2docx.page.RawPage import RawPage

    def checked(method):
        def run_unless_stopped(self, *args, **kwargs):
            check()
            return method(self, *args, **kwargs)

        return run_unless_stopped

    RawPage.restore = checked(RawPage.restore)  # layout extraction, per page
    Page.parse = checked(Page.parse)  # docx structure, per page
    Page.make_docx = checked(Page.make_docx)  # writing, per page
    _pdf2docx_hooked = True
