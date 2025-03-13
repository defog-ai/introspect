"""
Utilities for database operations.
"""

import numpy as np
import pandas as pd
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

from .name_utils import NameUtils
from .type_utils import TypeUtils
from utils_logging import LOGGER


class DbUtils:
    """Utilities for database operations."""

    @staticmethod
    def deduplicate_column_names(column_names, max_length=59):
        """
        Ensures all column names are unique by appending a counter if needed.
        Also truncates column names to fit PostgreSQL's limit.
        
        Args:
            column_names: List or array of column names
            max_length: Maximum allowed length for column names
            
        Returns:
            List of unique column names that fit within the max_length constraint
        """
        # Convert all column names to strings and handle empty values
        safe_cols = []
        seen = set()
        
        for i, col_name in enumerate(column_names):
            # Convert to string and sanitize
            col_name = str(col_name).strip()
            if not col_name:
                col_name = f"col_{i+1}"
            
            # Truncate long column names to fit PostgreSQL's limit
            # But keep the last part which usually contains the most specific information
            if len(col_name) > max_length - 3:
                # For names with underscores (like those from multi-level headers),
                # try to keep the last parts which are most specific
                parts = col_name.split('_')
                if len(parts) > 1 and len(parts[-1]) < max_length - 10:  # If last part is reasonably short
                    # Start with the most specific part (last one)
                    preserved_parts = [parts[-1]]
                    remaining_length = max_length - 3 - len(parts[-1])
                    
                    # Try to include as many preceding parts as possible, from right to left
                    for part in reversed(parts[:-1]):
                        # +1 for the underscore
                        if len(part) + 1 <= remaining_length:
                            preserved_parts.insert(0, part)
                            remaining_length -= (len(part) + 1)
                        else:
                            # If we can't fit the whole part, add a prefix indicator
                            if remaining_length > 3:
                                preserved_parts.insert(0, "...")
                            break
                    
                    col_name = "_".join(preserved_parts)
                else:
                    # Simple case - just keep the rightmost characters which tend to be most specific
                    col_name = "..." + col_name[-(max_length - 6):]
                
            # Start with potentially truncated name
            safe_name = col_name
            
            # If it's already seen, add numbers until unique
            counter = 1
            while safe_name in seen:
                safe_name = f"{col_name[:max_length - len(str(counter)) - 1]}_{counter}"
                counter += 1
                
            safe_cols.append(safe_name)
            seen.add(safe_name)
        
        return safe_cols

    @staticmethod
    def create_table_sql(table_name: str, columns: dict[str, str]):
        """
        Build a CREATE TABLE statement.

        Args:
            table_name: Name of the table to create
            columns: Dictionary mapping column names to data types

        Returns:
            SQL statement for creating the table
        """
        cols = []
        for col_name, col_type in columns.items():
            safe_col_name = NameUtils.sanitize_column_name(col_name)
            cols.append(f'"{safe_col_name}" {col_type}')

        cols_str = ", ".join(cols)
        return f'CREATE TABLE "{table_name}" ({cols_str});'

    @staticmethod
    async def export_df_to_postgres(
        df: pd.DataFrame,
        table_name: str,
        db_connection_string: str,
        chunksize: int = 5000,
    ):
        """
        Export a pandas DataFrame to PostgreSQL.

        Args:
            df: DataFrame to export
            table_name: Name of the target table
            db_connection_string: Database connection string
            chunksize: Number of rows to insert at once

        Returns:
            Dictionary with success status and inferred types
        """
        # Make a copy and handle NaN values
        df = df.copy().fillna(value="")

        # Store original column names for type inference
        original_cols = list(df.columns)

        # First ensure we have unique column names using our dedicated function
        unique_cols = DbUtils.deduplicate_column_names(df.columns)
        df.columns = unique_cols
        
        # Then sanitize column names for SQL use
        safe_col_list = []
        seen_names = set()

        for col in df.columns:
            safe_name = NameUtils.sanitize_column_name(col)

            # Handle duplicate sanitized names
            if safe_name in seen_names:
                counter = 1
                while f"{safe_name}_{counter}" in seen_names:
                    counter += 1
                safe_name = f"{safe_name}_{counter}"

            safe_col_list.append(safe_name)
            seen_names.add(safe_name)

        # Create mapping between sanitized and original names
        col_name_mapping = dict(zip(safe_col_list, original_cols))

        # Update dataframe with sanitized column names
        df.columns = safe_col_list

        # Create a SQLAlchemy engine
        engine = create_async_engine(db_connection_string)

        # Infer data types using original column names
        inferred_types = {}
        for col in df.columns:
            original_name = col_name_mapping.get(col, col)
            try:
                inferred_types[col] = TypeUtils.guess_column_type(
                    df[col], column_name=original_name
                )
            except Exception as e:
                raise Exception(
                    f"Failed to infer type for column {original_name} in table {table_name}: {e}"
                )

        LOGGER.info(inferred_types)

        # Convert values to appropriate PostgreSQL types
        converted_df = df.copy()
        for col in df.columns:
            try:
                converted_df[col] = df[col].map(
                    lambda value: TypeUtils.convert_values_to_postgres_type(
                        value, target_type=inferred_types[col]
                    )
                )
            except Exception as e:
                raise Exception(
                    f"Failed to convert values to PostgreSQL type for column {col} in table {table_name}: {e}"
                )

        # Create table in PostgreSQL
        try:
            create_stmt = DbUtils.create_table_sql(table_name, inferred_types)
        except Exception as e:
            raise Exception(
                f"Failed to create CREATE TABLE statements for {table_name}: {e}"
            )
        async with engine.begin() as conn:
            await conn.execute(text(f'DROP TABLE IF EXISTS "{table_name}";'))
            await conn.execute(text(create_stmt))

        # Prepare and execute INSERT statements
        insert_cols = ", ".join(f'"{c}"' for c in safe_col_list)
        placeholders = ", ".join([f":{c}" for c in safe_col_list])
        insert_sql = (
            f'INSERT INTO "{table_name}" ({insert_cols}) VALUES ({placeholders})'
        )

        async with engine.begin() as conn:
            rows_to_insert = []
            for idx, row in enumerate(
                converted_df.replace({np.nan: None}).to_dict("records")
            ):
                rows_to_insert.append(row)

                # Batch insert when chunk size reached or at the end
                if len(rows_to_insert) == chunksize or idx == len(converted_df) - 1:
                    await conn.execute(text(insert_sql), rows_to_insert)
                    rows_to_insert = []

        print(f"Successfully imported {len(df)} rows into table '{table_name}'.")
        return {"success": True, "inferred_types": inferred_types}