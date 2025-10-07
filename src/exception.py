# src/exception.py
import os
import traceback
from typing import Optional

def error_message_detail(error: BaseException, error_detail: Optional[object] = None) -> str:
    try:
        filename = "<unknown>"
        lineno = 0
        if error_detail is not None and hasattr(error_detail, "exc_info"):
            _, _, exc_tb = error_detail.exc_info()
            if exc_tb is not None:
                filename = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
                lineno = exc_tb.tb_lineno
        else:
            tb = getattr(error, "__traceback__", None)
            if tb is not None:
                while tb.tb_next:
                    tb = tb.tb_next
                filename = os.path.split(tb.tb_frame.f_code.co_filename)[1]
                lineno = tb.tb_lineno

        basic = f"Error occurred in script [{filename}] line number [{lineno}] error message [{error}]"
        trace = "".join(traceback.format_exception(type(error), error, error.__traceback__))
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
