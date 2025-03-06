"""
Utilities for handling table and column names.
"""

import re
from uuid import uuid4
from .constants import POSTGRES_RESERVED_WORDS


class NameUtils:
    """Utilities for handling table and column names."""

    @staticmethod
    def clean_table_name(table_name: str, existing=None):
        """
        Cleans a table name by snake casing it and making it lower case.

        Args:
            table_name: Table name to clean
            existing: List of existing table names to avoid duplicates

        Returns:
            Cleaned table name
        """
        if existing is None:
            existing = []

        if not isinstance(table_name, str):
            raise ValueError("Table name must be a string.")

        validated = str(table_name).strip().lower()
        validated = re.sub(r"[^a-zA-Z0-9_]", "_", validated)

        if validated in existing:
            validated = f"{validated}_{uuid4().hex[:7]}"

        if not validated:
            validated = f"table_{uuid4().hex[:7]}"

        return validated

    @staticmethod
    def sanitize_column_name(col_name: str):
        """
        Convert a column name into a "safe" Postgres identifier.

        Args:
            col_name: Column name to sanitize

        Returns:
            Sanitized column name
        """
        if not isinstance(col_name, str):
            col_name = str(col_name)

        col_name = col_name.strip().lower()

        # Replace special characters
        col_name = col_name.replace("%", "perc")
        col_name = col_name.replace("&", "and")

        # Replace invalid characters with underscores
        col_name = re.sub(r"[^a-z0-9_]", "_", col_name)

        # Collapse multiple underscores into single
        col_name = re.sub(r"_+", "_", col_name)

        # Strip leading/trailing underscores
        col_name = col_name.strip("_")

        # If empty after stripping, fallback
        if not col_name:
            col_name = "col"

        # If it starts with digit, prepend underscore
        if re.match(r"^\d", col_name):
            col_name = f"_{col_name}"

        # If it's a reserved keyword, add suffix
        if col_name in POSTGRES_RESERVED_WORDS:
            col_name = f"{col_name}_col"

        return col_name