# src/exception.py
import os
import traceback
from typing import Optional

def _last_traceback_frame(tb):
    if tb is None:
        return None
    while getattr(tb, "tb_next", None):
        tb = tb.tb_next
    return tb

def error_message_detail(error: BaseException, error_detail: Optional[object] = None) -> str:
    try:
        filename = "<unknown>"
        lineno = 0

        if error_detail is not None and hasattr(error_detail, "exc_info"):
            try:
                _, _, exc_tb = error_detail.exc_info()
            except Exception:
                exc_tb = None
            last_tb = _last_traceback_frame(exc_tb)
            if last_tb is not None:
                filename = os.path.split(last_tb.tb_frame.f_code.co_filename)[1]
                lineno = last_tb.tb_lineno
        else:
            tb = getattr(error, "__traceback__", None)
            last_tb = _last_traceback_frame(tb)
            if last_tb is not None:
                filename = os.path.split(last_tb.tb_frame.f_code.co_filename)[1]
                lineno = last_tb.tb_lineno

        basic = f"Error occurred in script [{filename}] line number [{lineno}] error message [{error}]"
        trace = "".join(traceback.format_exception(type(error), error, getattr(error, "__traceback__", None)))
        return f"{basic}\nFull traceback:\n{trace}"
    except Exception as e:
        return f"Failed to generate detailed error message: {e}. Original error: {error}"

class CustomException(Exception):
    def __init__(self, error_message: BaseException, error_detail: Optional[object] = None):
        detailed = error_message_detail(error_message, error_detail=error_detail)
        super().__init__(str(error_message))
        self.error_message = detailed
        self.original_exception = error_message

    def __str__(self) -> str:
        return self.error_message

    def __repr__(self) -> str:
        return f"CustomException({self.original_exception!r})"
