"""
Utilities for type detection and conversion.
"""

import re
from .datetime_utils import DateTimeUtils


class TypeUtils:
    """Utilities for type detection and conversion."""

    @staticmethod
    def to_float_if_possible(val):
        """
        Attempt to parse a value to numeric after cleaning.

        Args:
            val: Value to convert

        Returns:
            Float value if conversion is possible, None otherwise
        """
        if not val:
            return None

        try:
            # Handle accounting negative numbers (123.45) -> -123.45
            val_str = str(val).strip()
            if val_str.startswith("(") and val_str.endswith(")"):
                val_str = "-" + val_str[1:-1].strip("$").strip()

            # Clean the value by removing non-numeric symbols
            cleaned_val = re.sub(r"[^\d.\-+eE]", "", val_str)

            # Basic validations
            if cleaned_val in ("", ".", "-", "+"):
                return None

            digit_count = sum(c.isdigit() for c in val_str)
            alphanum_count = sum(c.isalnum() for c in val_str)

            if digit_count == 0 or alphanum_count == 0 or alphanum_count > digit_count:
                return None

            # Try parsing as float
            return float(cleaned_val)
        except:
            return None

    @staticmethod
    def guess_column_type(series, column_name=None, sample_size=50):
        """
        Guess the most appropriate Postgres column type for a data series.

        Args:
            series: Pandas Series to analyze
            column_name: Original column name for heuristics
            sample_size: Number of samples to take for analysis

        Returns:
            PostgreSQL data type as string
        """
        # Drop nulls/empty values
        non_null_values = [str(v) for v in series.dropna() if str(v).strip() != ""]

        # If there's nothing in this column, assume TEXT
        if len(non_null_values) == 0:
            return "TEXT"

        # Sample values to limit computational overhead
        sampled_values = (
            non_null_values[:sample_size]
            if len(non_null_values) > sample_size
            else non_null_values
        )

        # Check column name heuristics
        column_suggests_date = (
            column_name is not None and DateTimeUtils.is_date_column_name(column_name)
        )
        column_suggests_time = (
            column_name is not None and DateTimeUtils.is_time_column_name(column_name)
        )

        # Check if column is ID or suggests numeric values
        column_is_id = False
        column_suggests_numeric = False

        if column_name is not None:
            column_name = str(column_name)
            name_lower = column_name.lower()
            # Check for ID patterns
            if (
                name_lower == "id"
                or name_lower.endswith("_id")
                or name_lower.startswith("id_")
                or "_id_" in name_lower
            ):
                column_is_id = True
                column_suggests_date = False
                column_suggests_time = False
                column_suggests_numeric = True

            # Check for numeric indicator terms
            numeric_terms = [
                "amount", "total", "sum", "value", "price", "cost", "revenue", "income",
                "expense", "fee", "rate", "ratio", "score", "balance", "million", "billion",
                "thousand", "usd", "eur", "gbp", "jpy", "dollar", "euro", "pound", "yen",
                "currency", "money", "cash", "profit", "loss", "gain", "discount", "tax",
                "interest", "count", "number", "quantity", "weight", "height", "width",
                "length", "volume", "area", "size", "measurement", "percentage", "percent"
            ]

            col_lower = name_lower.replace("_", " ")
            for term in numeric_terms:
                if term in col_lower:
                    column_suggests_numeric = True
                    break

        # Check for obvious text values
        has_obvious_text = any(
            re.search(r"[a-df-zA-DF-Z]", v)
            and not DateTimeUtils.can_parse_date(v)
            and not DateTimeUtils.can_parse_time(v)
            for v in sampled_values
        )

        # Count different value types
        pct_count = sum(1 for v in sampled_values if str(v).strip().endswith("%"))
        time_count = sum(1 for v in sampled_values if DateTimeUtils.can_parse_time(v))
        date_count = sum(1 for v in sampled_values if DateTimeUtils.can_parse_date(v))
        us_date_count = sum(
            1
            for v in sampled_values
            if re.match(r"^(\d{1,2}|\d{4})/\d{1,2}/(\d{2}|\d{4})$", v.strip())
        )
        decimal_count = sum(
            1 for v in sampled_values if re.match(r"^-?\$?[0-9,]+\.\d+$", v.strip())
        )
        short_date_count = sum(
            1 for v in sampled_values if re.match(r"^\d{1,2}[/\-\.]\d{1,2}$", v.strip())
        )
        sci_notation_count = sum(
            1
            for v in sampled_values
            if re.search(r"^-?\d*\.?\d+[eE][+-]?\d+$", v.strip())
        )
        yyyymmdd_count = sum(
            1
            for v in sampled_values
            if re.fullmatch(r"\d{8}", v) and DateTimeUtils.can_parse_date(v)
        )
        iso_date_count = sum(
            1 for v in sampled_values if re.match(r"^\d{4}-\d{2}-\d{2}", v.strip())
        )

        # Calculate ratios
        total_samples = len(sampled_values)
        pct_ratio = pct_count / total_samples
        time_ratio = time_count / total_samples
        date_ratio = min(date_count / total_samples, 1.0)
        us_date_ratio = us_date_count / total_samples
        decimal_ratio = decimal_count / total_samples
        short_date_ratio = short_date_count / total_samples
        sci_notation_ratio = sci_notation_count / total_samples
        yyyymmdd_ratio = yyyymmdd_count / total_samples
        iso_date_ratio = iso_date_count / total_samples

        # Parse numeric values
        float_parsed = [TypeUtils.to_float_if_possible(v) for v in sampled_values]
        numeric_count = sum(x is not None for x in float_parsed)
        numeric_ratio = numeric_count / total_samples

        # Decision tree for type inference

        # Percentage check
        if pct_ratio > 0.3:
            return "DOUBLE PRECISION" if pct_ratio > 0.8 else "TEXT"

        # Time check
        if time_ratio > 0.7 or (column_suggests_time and time_ratio > 0.5):
            return "TIME"

        # US-style date check
        if us_date_ratio > 0.7:
            return "TIMESTAMP"

        # Decimal check
        if decimal_ratio > 0.7:
            return "DOUBLE PRECISION"

        # Short date check
        if short_date_ratio > 0.7:
            return "TIMESTAMP"

        # Scientific notation check
        if sci_notation_ratio > 0.2:
            return "DOUBLE PRECISION"

        # YYYYMMDD format date check
        if yyyymmdd_ratio > 0.7:
            return "TIMESTAMP"

        # ISO8601 date check
        if iso_date_ratio > 0.7:
            return "TIMESTAMP"

        # Check for text values in full dataset
        has_any_text_in_full = False
        text_value_count = 0
        for value in non_null_values:
            if (
                re.search(r"[a-zA-Z]", value)
                and not re.search(r"[eE][-+]?\d+", value)
                and not DateTimeUtils.can_parse_date(value)
                and not DateTimeUtils.can_parse_time(value)
            ):
                has_any_text_in_full = True
                text_value_count += 1

        # If significant text values and not date/time column, use TEXT
        if (
            has_any_text_in_full
            and not (column_suggests_date or column_suggests_time)
            and (text_value_count / len(non_null_values)) > 0.05
        ):
            return "TEXT"

        # If obvious text values, prefer TEXT
        if (has_obvious_text or has_any_text_in_full) and not (
            numeric_ratio > 0.95
            or date_ratio > 0.95
            or time_ratio > 0.95
            or column_suggests_date
            or column_suggests_time
        ):
            return "TEXT"

        # Special case for year columns
        if (
            column_name
            and (
                column_name.lower() == "year"
                or re.match(r"^(fiscal_|calendar_)?years?(_\d+)?$", column_name.lower())
                or "year" in column_name.lower()
            )
            and numeric_ratio > 0.8
        ):

            # Check if values appear to be years
            are_years = all(
                val is None or (val.is_integer() and 1000 <= val <= 2100)
                for val in float_parsed
                if val is not None
            )

            if are_years and any(float_parsed):
                return "BIGINT"

        # Time columns with confirmed time values
        if column_suggests_time and time_ratio > 0.7:
            return "TIME"

        # Date columns with confirmed date values
        if column_suggests_date and date_ratio > 0.7:
            # Check for month name columns
            month_names = [
                "jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec",
                "january", "february", "march", "april", "may", "june", "july", "august",
                "september", "october", "november", "december"
            ]

            month_name_count = sum(
                1 for val in sampled_values if str(val).lower().strip() in month_names
            )

            month_ratio = month_name_count / total_samples

            # If only month names, they should be TEXT
            if month_ratio > 0.7 and month_name_count == total_samples:
                return "TEXT"

            # Check for "invalid date" text
            invalid_text_ratio = (
                sum(
                    1
                    for v in sampled_values
                    if re.search(r"invalid|not\s+a\s+date", str(v).lower())
                )
                / total_samples
            )

            if invalid_text_ratio > 0.25 and column_name != "created_date":
                return "TEXT"

            # Otherwise, use TIMESTAMP
            return "TIMESTAMP"

        # Check if enough values are numeric
        numeric_threshold = 0.7 if column_suggests_numeric else 0.8
        if numeric_ratio >= numeric_threshold:
            # Check if all numeric values are integers
            are_ints = [val is not None and val.is_integer() for val in float_parsed]

            if all(are_ints) and are_ints:
                # Date or time column check with numeric values
                if column_suggests_date and "year" not in str(column_name).lower():
                    if (
                        sum(
                            1 for v in sampled_values if DateTimeUtils.can_parse_date(v)
                        )
                        / total_samples
                        > 0.6
                    ):
                        return "TIMESTAMP"

                if column_suggests_time:
                    if (
                        sum(
                            1 for v in sampled_values if DateTimeUtils.can_parse_time(v)
                        )
                        / total_samples
                        > 0.6
                    ):
                        return "TIME"

                # Short date patterns check
                if short_date_count > 0 and short_date_ratio > 0.5:
                    return "TIMESTAMP"

                # Final text check
                if any(
                    re.search(r"[a-zA-Z]", val) and not re.search(r"[eE][-+]?\d+", val)
                    for val in non_null_values
                ):
                    return "TEXT"

                return "BIGINT"
            else:
                return "DOUBLE PRECISION"

        # Lower threshold checks
        if time_ratio > 0.6:
            return "TIME"

        if date_ratio > 0.7:
            return "TIMESTAMP"

        # Default to TEXT
        return "TEXT"

    @staticmethod
    def convert_values_to_postgres_type(value, target_type: str):
        """
        Convert a value to the appropriate Python object for insertion into Postgres.

        Args:
            value: Value to convert
            target_type: PostgreSQL type string

        Returns:
            Converted value appropriate for the target type, or None if conversion fails
        """
        import datetime
        from dateutil import parser
        import pandas as pd
        
        # Handle Pandas Series objects
        if isinstance(value, pd.Series):
            return value.apply(
                lambda x: TypeUtils.convert_values_to_postgres_type(x, target_type)
            )

        # Handle None and NaN values
        if (
            value is None
            or (isinstance(value, float) and pd.isna(value))
            or pd.isna(value)
        ):
            return None

        val_str = str(value).strip()

        # Handle common NULL-like string values
        if val_str.lower() in ("", "null", "none", "nan", "   "):
            return None

        if target_type == "TIME":
            if not DateTimeUtils.can_parse_time(val_str):
                return None

            # Parse military time format directly
            if re.match(r"^([01]\d|2[0-3])([0-5]\d)$", val_str):
                hour = int(val_str[:2])
                minute = int(val_str[2:])
                return datetime.time(hour, minute)

            try:
                # Try various time parsing approaches
                parsed_time = parser.parse(val_str).time()
                return parsed_time
            except Exception:
                try:
                    # HH:MM(:SS) format
                    if re.match(
                        r"^([01]?\d|2[0-3]):([0-5]\d)(?::([0-5]\d))?$", val_str
                    ):
                        parts = val_str.split(":")
                        hour = int(parts[0])
                        minute = int(parts[1])
                        second = int(parts[2]) if len(parts) > 2 else 0
                        return datetime.time(hour, minute, second)

                    # AM/PM times
                    if re.match(
                        r"^([0-9]|1[0-2]):([0-5][0-9])(?::([0-5][0-9]))?\s*([AaPp][Mm])$",
                        val_str,
                    ):
                        is_pm = val_str.lower().endswith("pm")
                        time_part = val_str[:-2].strip()
                        parts = time_part.split(":")
                        hour = int(parts[0])
                        minute = int(parts[1])
                        second = int(parts[2]) if len(parts) > 2 else 0

                        if is_pm and hour < 12:
                            hour += 12
                        elif not is_pm and hour == 12:
                            hour = 0

                        return datetime.time(hour, minute, second)
                except:
                    pass
                return None

        elif target_type == "TIMESTAMP":
            # Don't parse scientific notation as dates
            if re.search(r"^-?\d*\.?\d+[eE][+-]?\d+$", val_str.strip()):
                return None

            # Check if it can be parsed as a date
            if not DateTimeUtils.can_parse_date(val_str):
                return None

            # Check for invalid date patterns
            if re.search(r"(\d{4}-\d{2}-\d{2})-[a-zA-Z]", val_str):
                return None

            try:
                parsed_date = parser.parse(val_str)
                # Verify the year is reasonable
                if 1900 <= parsed_date.year <= 2100:
                    return parsed_date
                return None
            except Exception:
                return None

        elif target_type in ("BIGINT", "DOUBLE PRECISION"):
            # Handle accounting negative numbers (123.45) -> -123.45
            if val_str.startswith("(") and val_str.endswith(")"):
                val_str = "-" + val_str[1:-1].strip("$").strip()

            # Handle percentage values
            if val_str.endswith("%"):
                val_str = val_str.rstrip("%").strip()
                try:
                    return float(re.sub(r"[^\d.\-+eE]", "", val_str)) / 100
                except:
                    return None

            # Handle currency codes
            if re.search(r"\s+[A-Za-z]{3}$", val_str):
                val_str = re.sub(r"\s+[A-Za-z]{3}$", "", val_str)
            elif re.search(r"^[A-Za-z]{3}\s+", val_str):
                val_str = re.sub(r"^[A-Za-z]{3}\s+", "", val_str)

            # Skip processing for values with letters (except scientific notation)
            if re.search(r"[a-zA-Z]", val_str) and not re.search(
                r"[eE][-+]?\d+", val_str
            ):
                return None

            # Scientific notation handling
            if re.search(r"^-?\d*\.?\d+[eE][+-]?\d+$", val_str.strip()):
                try:
                    float_val = float(val_str)
                    if target_type == "BIGINT":
                        if pd.isna(float_val) or float_val in (
                            float("inf"),
                            float("-inf"),
                        ):
                            return None
                        # Check PostgreSQL BIGINT range
                        if (
                            float_val < -9223372036854775808
                            or float_val > 9223372036854775807
                        ):
                            return None
                        return int(float_val)
                    else:  # DOUBLE PRECISION
                        return float_val
                except:
                    return None

            # Clean the value
            cleaned_val = re.sub(r"[^\d.\-+eE]", "", val_str)
            if cleaned_val in ("", ".", "-", "+"):
                return None

            # Validate numeric format
            if (
                cleaned_val.count(".") > 1
                or cleaned_val.count("-") > 1
                or cleaned_val.count("+") > 1
                or re.search(r"\d,\d,\d", val_str)
                or "/" in val_str
                or "+" in val_str[1:]
                or (target_type == "BIGINT" and re.search(r"[a-df-zA-DF-Z]", val_str))
            ):
                return None

            try:
                if target_type == "BIGINT":
                    float_val = float(cleaned_val)
                    if pd.isna(float_val) or float_val in (float("inf"), float("-inf")):
                        return None
                    # Check PostgreSQL BIGINT range
                    if (
                        float_val < -9223372036854775808
                        or float_val > 9223372036854775807
                    ):
                        return None
                    return int(float_val)
                else:  # DOUBLE PRECISION
                    return float(cleaned_val)
            except:
                return None

        else:
            # TEXT or fallback
            return str(value)