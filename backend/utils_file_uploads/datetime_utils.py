"""
Utilities for handling date and time operations.
"""

import re
from dateutil import parser


class DateTimeUtils:
    """Utilities for handling date and time operations."""

    # Common terms that indicate date columns
    DATE_TERMS = [
        "date", "time", "year", "month", "day", "quarter", "qtr", 
        "yr", "mm", "dd", "yyyy", "created", "modified", "updated", 
        "timestamp", "dob", "birth", "start", "end", "period", 
        "calendar", "fiscal", "dtm", "dt", "ymd", "mdy", "dmy",
    ]

    # Common terms that indicate time-only columns
    TIME_TERMS = [
        "time", "hour", "minute", "second", "hr", "min", "sec",
        "am", "pm", "duration", "interval"
    ]

    # Common date patterns for regex matching
    COMMON_DATE_PATTERNS = [
        # MM/DD/YYYY or DD/MM/YYYY
        r"^\d{1,2}[/\-\.]\d{1,2}[/\-\.]\d{2,4}$",
        # YYYY/MM/DD
        r"^\d{4}[/\-\.]\d{1,2}[/\-\.]\d{1,2}$",
        # Month name formats: Jan 01, 2020 or January 1, 2020
        r"^[A-Za-z]{3,9}\.?\s+\d{1,2},?\s+\d{2,4}$",
        # 01-Jan-2020 or 1-January-20
        r"^\d{1,2}[/\-\.\s]+[A-Za-z]{3,9}\.?[/\-\.\s]+\d{2,4}$",
        # Formats like 01Jan2023 or 01JAN2023
        r"^\d{1,2}[A-Za-z]{3,9}\d{2,4}$",
        # Short date format like MM/DD or MM-DD
        r"^\d{1,2}[/\-\.]\d{1,2}$",
    ]

    # Common time patterns for regex matching
    TIME_PATTERNS = [
        # HH:MM or HH:MM:SS (24-hour format)
        r"^([01]\d|2[0-3]):[0-5]\d(:[0-5]\d)?$",
        # H:MM or H:MM:SS (single digit hour)
        r"^[0-9]:[0-5]\d(:[0-5]\d)?$",
        # HH:MM AM/PM or HH:MM:SS AM/PM (12-hour format)
        r"^(0?[1-9]|1[0-2]):[0-5]\d(:[0-5]\d)?\s*[AaPp][Mm]$",
        # Military time (0000-2359)
        r"^([01]\d|2[0-3])([0-5]\d)$",
    ]

    @classmethod
    def is_date_column_name(cls, col_name):
        """
        Check if a column name indicates it might contain date/time data.

        Args:
            col_name: Column name to check

        Returns:
            True if the column name suggests date content
        """
        if not isinstance(col_name, str):
            return False

        # Normalize the column name for better matching
        name_lower = col_name.lower()

        # Check for ID patterns - don't treat as dates
        if (
            name_lower == "id"
            or name_lower.endswith("_id")
            or name_lower.startswith("id_")
            or "_id_" in name_lower
        ):
            return False

        # Check if any date term appears in the column name
        for term in cls.DATE_TERMS:
            if term in name_lower:
                return True

        # Check for common date patterns
        if re.search(r"(_|^)(dt|date|time)(_|$)", name_lower):
            return True

        return False

    @classmethod
    def is_time_column_name(cls, col_name):
        """
        Check if a column name indicates it might contain time-only data.

        Args:
            col_name: Column name to check

        Returns:
            True if the column name suggests time content
        """
        if not isinstance(col_name, str):
            return False

        # Normalize the column name for better matching
        name_lower = col_name.lower()

        # Check for ID patterns
        if (
            name_lower == "id"
            or name_lower.endswith("_id")
            or name_lower.startswith("id_")
            or "_id_" in name_lower
        ):
            return False

        # Simple direct check for common time column patterns
        if (
            "_time" in name_lower
            or name_lower.startswith("time_")
            or name_lower == "time"
            or name_lower in ["hour", "minute", "second"]
        ):

            # Exclude patterns that suggest datetime rather than just time
            if not any(
                date_term in name_lower
                for date_term in ["date", "timestamp", "datetime"]
            ):
                return True

        # Date terms that would indicate this is a full date/timestamp, not just time
        for term in cls.DATE_TERMS:
            if term in name_lower and term not in cls.TIME_TERMS:
                return False

        # Check if any time-specific term appears in the name
        for term in cls.TIME_TERMS:
            # Match whole words or components with word boundaries
            if (
                re.search(rf"(^|_){term}($|_)", name_lower)
                or name_lower == term
                or name_lower.endswith(f"_{term}")
                or name_lower.startswith(f"{term}_")
            ):
                return True

        return False

    @classmethod
    def can_parse_date(cls, val):
        """
        Check if a value can be parsed as a date.

        Args:
            val: Value to check

        Returns:
            True if the value appears to be a date
        """
        if not isinstance(val, str):
            val = str(val)

        val = val.strip()

        # Quick rejections
        if (
            not val
            or val.lower() in ("invalid date", "not a date", "na", "n/a")
            or len(val) <= 4
        ):
            return False

        # Detect date ranges like "Feb 14-21" or "Feb 26 - Mar 4" and exclude them
        if re.search(
            r"([A-Za-z]{3,9}\.?\s+\d{1,2}\s*[-–]\s*\d{1,2})", val
        ) or re.search(r"([A-Za-z]{3,9}\.?\s+\d{1,2}\s*[-–]\s*[A-Za-z]{3,9})", val):
            return False

        # Check against common date patterns
        for pattern in cls.COMMON_DATE_PATTERNS:
            if re.match(pattern, val):
                try:
                    parser.parse(val)
                    return True
                except:
                    pass

        # Handle all-digit strings
        if re.fullmatch(r"\d+", val):
            if len(val) in (6, 8):  # YYMMDD or YYYYMMDD format
                try:
                    parser.parse(val)
                    return True
                except Exception:
                    return False
            return False

        # For strings without date separators
        if not re.search(r"[\s/\-\.:]", val):
            try:
                parsed_date = parser.parse(val, fuzzy=False)
                return 1900 <= parsed_date.year <= 2100
            except:
                return False

        # Special handling for US-style dates
        if re.match(r"^\d{1,2}/\d{1,2}/\d{2,4}$", val):
            try:
                parsed_date = parser.parse(val, fuzzy=False)
                return 1900 <= parsed_date.year <= 2100
            except:
                pass

        # Final attempt with dateutil parser
        try:
            parsed_date = parser.parse(val, fuzzy=False)
            return 1900 <= parsed_date.year <= 2100
        except Exception:
            return False

    @classmethod
    def can_parse_time(cls, val):
        """
        Check if a value can be parsed as a time-only value.

        Args:
            val: Value to check

        Returns:
            True if the value appears to be a time
        """
        if not isinstance(val, str):
            val = str(val)

        val = val.strip()

        # Quick rejections
        if not val or len(val) < 3 or re.match(r"^(19|20)\d{2}$", val):
            return False

        # Check against time patterns
        for pattern in cls.TIME_PATTERNS:
            if re.match(pattern, val):
                try:
                    # Special handling for military time
                    if len(val) == 4 and val.isdigit():
                        return bool(re.match(r"^([01]\d|2[0-3])([0-5]\d)$", val))
                    _ = parser.parse(val).time()
                    return True
                except Exception:
                    pass

        # Try more general time parsing
        try:
            parsed = parser.parse(val)

            # Check if this looks like a time-only value:
            # 1. Has colon (common in time)
            # 2. Doesn't have date separators
            if ":" in val and not any(x in val for x in ["/", "-", ".", ","]):
                # Check if the original string contains the time component
                # but not common month/day names
                time_str = parsed.strftime("%H:%M")
                month_day_terms = [
                    "jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", 
                    "oct", "nov", "dec", "monday", "tuesday", "wednesday", "thursday",
                    "friday", "saturday", "sunday"
                ]
                
                if time_str in val and not any(x in val.lower() for x in month_day_terms):
                    return True

            return False
        except Exception:
            return False