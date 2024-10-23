import json
import logging
from logging.config import dictConfig
import os
import time
from typing import Any, Dict, List, Tuple, Union

LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()  # Ensure uppercase for consistency

if LOG_LEVEL == "":
    LOG_LEVEL = "INFO"

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


def truncate_list(
    l: List, max_len_list: int = 10, max_len_str: int = 100, to_str: bool = True
) -> str:
    """
    Returns a string of the first max_len elements of the list l.
    This is avoid printing out large lists in the logs.
    """
    num_elements = len(l)
    l_trunc = []
    for item in l[:max_len_list]:
        if isinstance(item, dict):
            l_trunc.append(truncate_dict(item, max_len_list, max_len_str, to_str=False))
        elif isinstance(item, list):
            l_trunc.append(truncate_list(item, max_len_list, max_len_str, to_str=False))
        elif isinstance(item, str) and len(item) > max_len_str:
            l_trunc.append(item[:max_len_str] + f"...[{len(item)} chars]")
        else:
            l_trunc.append(item)
    if to_str:
        if num_elements > max_len_list:
            return (
                "["
                + ", ".join([str(i) for i in l_trunc])
                + f"...({num_elements} total elements)]"
            )
        else:
            return json.dumps(l_trunc, indent=2)
    else:
        return l_trunc


def truncate_dict(
    obj: Dict, max_len_list: int = 10, max_len_str: int = 100, to_str: bool = True
) -> Union[str, Dict]:
    """
    Returns a string representation of a dictionary, truncating it if it's too long.
    """

    def inner(obj, max_len_list, max_len_str):
        ret_obj = {}
        for k, v in obj.items():
            if isinstance(v, list):
                ret_obj[k] = truncate_list(v, max_len_list, max_len_str, to_str=False)
            elif isinstance(v, dict):
                ret_obj[k] = inner(v, max_len_list, max_len_str)
            elif isinstance(v, str) and len(str(v)) > max_len_str:
                ret_obj[k] = str(v)[:max_len_str] + f"...[{len(v)} chars]"
            else:
                ret_obj[k] = v
        return ret_obj

    ret_obj = inner(obj, max_len_list, max_len_str)
    if to_str:
        return json.dumps(ret_obj, indent=2)
    else:
        return ret_obj


def truncate_obj(
    obj: Any, max_len_list: int = 10, max_len_str: int = 500, to_str: bool = True
) -> Union[str, Dict]:
    """
    Returns a string representation of the object obj, truncating it if it's too long.
    This is the generic function that can handle strings, lists, dictionaries,
    and nested structures of these. Use this if you don't know what type you'll be receiving.
    """
    try:
        if isinstance(obj, list):
            return truncate_list(obj, max_len_list, max_len_str, to_str)
        elif isinstance(obj, dict):
            return truncate_dict(obj, max_len_list, max_len_str, to_str)
        elif isinstance(obj, str) and len(obj) > max_len_str:
            return obj[:max_len_str] + f"...[{len(obj)} chars]"
        else:
            return str(obj) if to_str else obj
    except Exception as e:
        LOGGER.error(f"Error in truncate_obj: {e}")
        return "" if to_str else None
