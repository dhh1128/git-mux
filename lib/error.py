import traceback, sys

from colors import ERROR_COLOR
from ansi import ewritec, writec, NORMTXT

FULL_TRACE = True

def write(msg=None):
    ewritec(ERROR_COLOR)
    if msg:
        ewritec(msg)
    exc_type, exc_value, exc_traceback = sys.exc_info()
    if FULL_TRACE:
        traceback.print_exc()
    else:
        lines = traceback.format_exception_only(exc_type, exc_value)
        for line in lines:
            ewritec(line)
