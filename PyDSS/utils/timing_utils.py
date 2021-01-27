"""Utility functions for timing measurements."""

import functools
import logging
import time


logger = logging.getLogger(__name__)


def timed_info(func):
    """Decorator to measure and logger.info a function's execution time."""
    @functools.wraps(func)
    def timed_(*args, **kwargs):
        return _timed(func, logger.info, *args, **kwargs)

    return timed_


def timed_debug(func):
    """Decorator to measure and logger.debug a function's execution time."""
    @functools.wraps(func)
    def timed_(*args, **kwargs):
        return _timed(func, logger.debug, *args, **kwargs)

    return timed_


def _timed(func, log_func, *args, **kwargs):
    start = time.time()
    result = func(*args, **kwargs)
    total = time.time() - start
    log_func("execution-time=%s func=%s", get_time_duration_string(total),
             func.__name__)
    return result


def get_time_duration_string(seconds):
    """Returns a string with the time converted to reasonable units."""
    if seconds >= 1:
        val = "{:.3f} s".format(seconds)
    elif seconds >= .001:
        val = "{:.3f} ms".format(seconds * 1000)
    elif seconds >= .000001:
        val = "{:.3f} us".format(seconds * 1000000)
    elif seconds == 0:
        val = "0 s"
    else:
        val = "{:.3f} ns".format(seconds * 1000000000)

    return val
