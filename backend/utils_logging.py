import logging
from logging.config import dictConfig
import os
import time
from typing import List, Tuple

LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO').upper()  # Ensure uppercase for consistency
print(f"Setting log level to {LOG_LEVEL}")

LOG_CONFIG = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "default": {
            "format": "%(levelname)s: %(message)s",
        },
    },
    "handlers": {
        "default": {
            "level": LOG_LEVEL,
            "formatter": "default",
            "class": "logging.StreamHandler",
        },
    },
    "loggers": {
        "server": {  # Our global logger
            "handlers": ["default"],
            "level": LOG_LEVEL,
            "propagate": False,  # Prevent propagation to root logger
        },
        "": {  # Root logger
            "handlers": ["default"],
            "level": "WARNING",  # Set a higher level for other loggers
            "propagate": True,
        },
    },
}

dictConfig(LOG_CONFIG)
# This is the global logger object that we'll use throughout the server
LOGGER = logging.getLogger("server")

def save_timing(t_start: float, msg: str, timings: List[Tuple[float, str]]) -> float:
    """
    Saves the current duration since t_start along with the message msg into the timings list.
    Returns the current time (for resetting the t_start variable)
    Note that we don't return the timings list because we're modifying it in place.
    """
    t_end = time.time()
    timings.append((t_end - t_start, msg))
    return t_end

def log_timings(timings: List[Tuple[float, str]]) -> None:
    """
    Prints out the timings in the timings list.
    This is handled by our global logger object.
    """
    for timing, msg in timings:
        LOGGER.info(f"{timing:.2f}s: {msg}")

def save_and_log(t_start: float, msg: str, timings: List[Tuple[float, str]]) -> float:
    """
    A convenience function that combines save_timing and log_timings.
    """
    _ = save_timing(t_start, msg, timings)
    log_timings(timings)