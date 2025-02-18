import base64
import inspect
import pandas as pd


class SqlExecutionError(Exception):
    def __init__(self, sql, error_message):
        # Call the base class constructor with the parameters it needs
        super().__init__(f"{error_message}")

        # Now for your custom code...
        self.sql = sql


def deduplicate_columns(df: pd.DataFrame):
    # de-duplicate column names
    # if the same column name exists more than once, add a suffix
    deduplicated_df = df.copy()
    columns = deduplicated_df.columns.tolist()
    seen = {}
    for i, item in enumerate(columns):
        if item in seen:
            columns[i] = f"{item}_{seen[item]}"
            seen[item] += 1
        else:
            seen[item] = 1

    deduplicated_df.columns = columns

    return deduplicated_df


def wrap_in_async(fn):
    """
    If a function isn't async, wrap it in an async function for create_Task to work
    """
    wrapped_fn = fn
    if not inspect.iscoroutinefunction(fn):

        async def async_fn(**kwargs):
            return fn(**kwargs)

        wrapped_fn = async_fn

    return wrapped_fn


def encode_image(image_path):
    """
    Encodes an image to base64.
    """
    with open(image_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode("utf-8")


def longest_substring_overlap(s1, s2, min_substr_len_match):
    """
    If the longest overlap is greater than or equal to min_substr_len_match,
    return True and matched string, otherwise return False and longest matched string.

    Args:
        s1 (str): First string.
        s2 (str): Second string.
        min_substr_len_match (int): Minimum substring length to consider as a match.

    Returns:
        bool: True if the minimum substring length match is reached, otherwise False.
        str: The overlapping substring.
    """
    max_overlap = 0
    overlap_string = ""

    for i in range(len(s1)):
        for j in range(len(s2)):
            k = 0
            while i + k < len(s1) and j + k < len(s2) and s1[i + k] == s2[j + k]:
                k += 1
            if k > max_overlap:
                max_overlap = k
                overlap_string = s1[i : i + k]

    return max_overlap >= min_substr_len_match, overlap_string
