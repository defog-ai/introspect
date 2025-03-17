"""
Utilities for database operations.
"""

import numpy as np
import pandas as pd
import os
import json
import tempfile
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
    def create_table_sql(table_name: str, columns: dict[str, str], db_type: str = "postgres"):
        """
        Build a CREATE TABLE statement based on database type.

        Args:
            table_name: Name of the table to create
            columns: Dictionary mapping column names to data types
            db_type: Type of database (postgres, mysql, sqlserver, redshift, snowflake, bigquery, etc.)

        Returns:
            SQL statement for creating the table
        """
        cols = []
        for col_name, col_type in columns.items():
            safe_col_name = NameUtils.sanitize_column_name(col_name)
            
            # Convert PostgreSQL types to target database types if needed
            target_type = col_type
            
            # Database-specific type mappings
            if db_type == "bigquery":
                # Map PostgreSQL types to BigQuery types
                if col_type == "TEXT":
                    target_type = "STRING"
                elif col_type in ["BIGINT", "INTEGER"]:
                    target_type = "INT64"
                elif col_type == "DOUBLE PRECISION":
                    target_type = "FLOAT64"
                elif "TIMESTAMP" in col_type:
                    target_type = "TIMESTAMP"
                elif "TIME" in col_type:
                    target_type = "TIME"
            elif db_type == "snowflake":
                # Map PostgreSQL types to Snowflake types
                if col_type == "DOUBLE PRECISION":
                    target_type = "FLOAT"
                # Snowflake compatible with most PostgreSQL types
            elif db_type == "redshift":
                # Redshift uses similar types to PostgreSQL
                pass
            
            # Handle different database identifier quoting styles
            if db_type == "mysql":
                # MySQL uses backticks
                cols.append(f'`{safe_col_name}` {target_type}')
            elif db_type == "sqlserver":
                # SQL Server uses square brackets
                cols.append(f'[{safe_col_name}] {target_type}')
            elif db_type == "bigquery":
                # BigQuery doesn't require quotes for standard identifiers
                cols.append(f'{safe_col_name} {target_type}')
            elif db_type == "snowflake":
                # Snowflake uses double quotes but uppercase identifiers by default
                cols.append(f'"{safe_col_name}" {target_type}')
            else:
                # Default to PostgreSQL style with double quotes (works for Redshift too)
                cols.append(f'"{safe_col_name}" {target_type}')

        cols_str = ", ".join(cols)
        
        # Generate CREATE TABLE statement with appropriate identifier quoting and syntax
        if db_type == "mysql":
            return f'CREATE TABLE `{table_name}` ({cols_str});'
        elif db_type == "sqlserver":
            return f'CREATE TABLE [{table_name}] ({cols_str});'
        elif db_type == "bigquery":
            return f'CREATE TABLE {table_name} ({cols_str});'
        elif db_type == "snowflake":
            return f'CREATE OR REPLACE TABLE "{table_name}" ({cols_str});'
        else:
            # Default PostgreSQL/Redshift style
            return f'CREATE TABLE "{table_name}" ({cols_str});'

    @staticmethod
    async def export_df_to_db(
        df: pd.DataFrame,
        table_name: str,
        db_connection_string: str,
        db_type: str = "postgres",
        chunksize: int = 5000,
        db_creds: dict = None,
    ):
        """
        Export a pandas DataFrame to a database.

        Args:
            df: DataFrame to export
            table_name: Name of the target table
            db_connection_string: Database connection string
            db_type: Type of database (postgres, mysql, sqlserver, redshift, snowflake, bigquery, etc.)
            chunksize: Number of rows to insert at once
            db_creds: Additional credentials needed for some DB types (like BigQuery)

        Returns:
            Dictionary with success status and inferred types
        """
        # Make a copy and handle NaN values
        df = df.copy().fillna(value="")

        # Store original column names for type inference
        original_cols = list(df.columns)

        # Get appropriate column name max length for the database type
        max_col_length = 59  # Default for PostgreSQL
        if db_type == "mysql":
            max_col_length = 64
        elif db_type == "sqlserver":
            max_col_length = 128
        elif db_type == "bigquery":
            max_col_length = -1  # BigQuery has no practical limit
        elif db_type == "snowflake":
            max_col_length = 255
        
        # Deduplicate column names with appropriate length limit
        unique_cols = DbUtils.deduplicate_column_names(df.columns, max_col_length)
        df.columns = unique_cols
        
        # Sanitize column names for SQL use
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

        # Special handling for BigQuery, which uses different approach
        if db_type == "bigquery" and db_creds:
            try:
                return await DbUtils._export_df_to_bigquery(
                    df, table_name, db_creds, col_name_mapping
                )
            except Exception as e:
                raise Exception(f"Failed to export to BigQuery: {str(e)}")
        
        # Special handling for Snowflake, which may have additional parameters
        if db_type == "snowflake" and db_creds:
            try:
                return await DbUtils._export_df_to_snowflake(
                    df, table_name, db_connection_string, db_creds, col_name_mapping
                )
            except Exception as e:
                raise Exception(f"Failed to export to Snowflake: {str(e)}")

        # For SQL databases (PostgreSQL, MySQL, SQL Server, Redshift)
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

        # Convert values based on database type
        converted_df = df.copy()
        for col in df.columns:
            try:
                # PostgreSQL conversion is the base for most SQL databases
                # We could implement specific conversions for each DB type if needed
                converted_df[col] = df[col].map(
                    lambda value: TypeUtils.convert_values_to_postgres_type(
                        value, target_type=inferred_types[col]
                    )
                )
            except Exception as e:
                raise Exception(
                    f"Failed to convert values for column {col} in table {table_name}: {e}"
                )

        # Create table SQL
        try:
            create_stmt = DbUtils.create_table_sql(table_name, inferred_types, db_type)
        except Exception as e:
            raise Exception(
                f"Failed to create CREATE TABLE statement for {table_name}: {e}"
            )
            
        # Database-specific SQL handling for DROP and CREATE
        if db_type == "mysql":
            # MySQL uses backticks for identifiers
            drop_sql = f"DROP TABLE IF EXISTS `{table_name}`;"
        elif db_type == "sqlserver":
            # SQL Server uses square brackets and different DROP syntax
            drop_sql = f"IF OBJECT_ID('{table_name}', 'U') IS NOT NULL DROP TABLE [{table_name}];"
        elif db_type == "redshift":
            # Redshift similar to PostgreSQL
            drop_sql = f'DROP TABLE IF EXISTS "{table_name}";'
        else:
            # Default PostgreSQL style 
            drop_sql = f'DROP TABLE IF EXISTS "{table_name}";'

        # Execute DROP and CREATE statements
        try:
            async with engine.begin() as conn:
                await conn.execute(text(drop_sql))
                await conn.execute(text(create_stmt))
        except Exception as e:
            raise Exception(f"Failed to create table: {str(e)}")

        # Prepare INSERT statement based on DB type
        if db_type == "mysql":
            # MySQL uses backticks
            insert_cols = ", ".join(f"`{c}`" for c in safe_col_list)
            placeholders = ", ".join([f":{c}" for c in safe_col_list])
            insert_sql = f"INSERT INTO `{table_name}` ({insert_cols}) VALUES ({placeholders})"
        elif db_type == "sqlserver":
            # SQL Server uses square brackets
            insert_cols = ", ".join(f"[{c}]" for c in safe_col_list)
            placeholders = ", ".join([f":{c}" for c in safe_col_list])
            insert_sql = f"INSERT INTO [{table_name}] ({insert_cols}) VALUES ({placeholders})"
        elif db_type == "redshift":
            # Redshift similar to PostgreSQL
            insert_cols = ", ".join(f'"{c}"' for c in safe_col_list)
            placeholders = ", ".join([f":{c}" for c in safe_col_list])
            insert_sql = f'INSERT INTO "{table_name}" ({insert_cols}) VALUES ({placeholders})'
        else:
            # Default PostgreSQL style
            insert_cols = ", ".join(f'"{c}"' for c in safe_col_list)
            placeholders = ", ".join([f":{c}" for c in safe_col_list])
            insert_sql = f'INSERT INTO "{table_name}" ({insert_cols}) VALUES ({placeholders})'

        # Execute INSERT statements
        try:
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
        except Exception as e:
            raise Exception(f"Failed to insert data: {str(e)}")

        LOGGER.info(f"Successfully imported {len(df)} rows into table '{table_name}'.")
        return {"success": True, "inferred_types": inferred_types}
    
    @staticmethod
    async def _export_df_to_bigquery(
        df: pd.DataFrame, 
        table_name: str, 
        db_creds: dict, 
        col_name_mapping: dict
    ):
        """
        Export a DataFrame to BigQuery.
        This method handles the special case for BigQuery which uses the Google Cloud SDK.
        
        Args:
            df: DataFrame to export
            table_name: Name of the target table
            db_creds: BigQuery credentials
            col_name_mapping: Mapping between sanitized and original column names
            
        Returns:
            Dictionary with success status and inferred types
        """
        try:
            from google.cloud import bigquery
            from google.oauth2 import service_account
        except ImportError:
            raise Exception("Google Cloud BigQuery libraries not installed. Install with: pip install google-cloud-bigquery")
            
        # Extract credentials from db_creds
        if 'json_key_path' in db_creds:
            credentials = service_account.Credentials.from_service_account_file(
                db_creds['json_key_path']
            )
        elif 'credentials_file_content' in db_creds:
            # Write the credentials content to a temporary file
            with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.json') as temp_file:
                json.dump(db_creds['credentials_file_content'], temp_file)
                temp_path = temp_file.name
            
            credentials = service_account.Credentials.from_service_account_file(temp_path)
            # Clean up the temporary file
            os.unlink(temp_path)
        else:
            raise Exception("BigQuery credentials missing. Need either json_key_path or credentials_file_content.")
            
        # Get project_id from credentials or credentials_content
        project_id = credentials.project_id
        if not project_id and 'project_id' in db_creds:
            project_id = db_creds['project_id']
            
        if not project_id:
            raise Exception("Could not determine BigQuery project_id from credentials.")
        
        # Initialize BigQuery client
        client = bigquery.Client(credentials=credentials, project=project_id)
        
        # Set dataset if provided, otherwise use default
        dataset_id = db_creds.get('dataset', 'default_dataset')
        table_ref = f"{project_id}.{dataset_id}.{table_name}"
        
        # Infer schema from DataFrame
        inferred_types = {}
        schema = []
        
        for col in df.columns:
            original_name = col_name_mapping.get(col, col)
            # Try to infer the BigQuery data type
            try:
                pg_type = TypeUtils.guess_column_type(df[col], column_name=original_name)
                
                # Map PostgreSQL types to BigQuery types
                if pg_type == "TEXT":
                    bq_type = "STRING"
                elif pg_type in ["BIGINT", "INTEGER"]:
                    bq_type = "INT64"
                elif pg_type == "DOUBLE PRECISION":
                    bq_type = "FLOAT64"
                elif "TIMESTAMP" in pg_type:
                    bq_type = "TIMESTAMP"
                elif "TIME" in pg_type:
                    bq_type = "TIME"
                elif pg_type == "BOOLEAN":
                    bq_type = "BOOL"
                else:
                    # Default to string for unknown types
                    bq_type = "STRING"
                
                inferred_types[col] = bq_type
                schema.append(bigquery.SchemaField(col, bq_type))
            except Exception as e:
                LOGGER.error(f"Error inferring type for {col}: {str(e)}")
                # Default to STRING for problematic columns
                inferred_types[col] = "STRING"
                schema.append(bigquery.SchemaField(col, "STRING"))
        
        # Configure table with schema
        table = bigquery.Table(table_ref, schema=schema)
        
        # Delete table if it exists
        try:
            client.delete_table(table_ref, not_found_ok=True)
            LOGGER.info(f"Table {table_ref} deleted if it existed.")
        except Exception as e:
            LOGGER.warning(f"Error deleting table {table_ref}: {str(e)}")
        
        # Create the table
        try:
            table = client.create_table(table)
            LOGGER.info(f"Created table {table_ref}")
        except Exception as e:
            raise Exception(f"Failed to create BigQuery table: {str(e)}")
        
        # Load data
        try:
            # Convert to records
            records = df.replace({np.nan: None}).to_dict("records")
            
            # Insert data in chunks
            chunk_size = 5000
            for i in range(0, len(records), chunk_size):
                chunk = records[i:i + chunk_size]
                errors = client.insert_rows_json(table, chunk)
                if errors:
                    raise Exception(f"Error loading data to BigQuery: {errors}")
                
            LOGGER.info(f"Successfully loaded {len(df)} rows to BigQuery table {table_ref}")
        except Exception as e:
            raise Exception(f"Failed to insert data into BigQuery: {str(e)}")
            
        return {"success": True, "inferred_types": inferred_types}
    
    @staticmethod
    async def _export_df_to_snowflake(
        df: pd.DataFrame, 
        table_name: str, 
        db_connection_string: str,
        db_creds: dict, 
        col_name_mapping: dict
    ):
        """
        Export a DataFrame to Snowflake.
        This method handles the special case for Snowflake which may require additional parameters.
        
        Args:
            df: DataFrame to export
            table_name: Name of the target table
            db_connection_string: Database connection string
            db_creds: Snowflake credentials
            col_name_mapping: Mapping between sanitized and original column names
            
        Returns:
            Dictionary with success status and inferred types
        """
        # Create a SQLAlchemy engine using connection string
        engine = create_async_engine(db_connection_string)
        
        # Infer data types using original column names
        inferred_types = {}
        for col in df.columns:
            original_name = col_name_mapping.get(col, col)
            try:
                pg_type = TypeUtils.guess_column_type(df[col], column_name=original_name)
                
                # Map PostgreSQL types to Snowflake types
                if pg_type == "DOUBLE PRECISION":
                    sf_type = "FLOAT"
                elif pg_type == "BIGINT":
                    sf_type = "NUMBER"
                else:
                    # Most PostgreSQL types map well to Snowflake
                    sf_type = pg_type
                    
                inferred_types[col] = sf_type
            except Exception as e:
                raise Exception(f"Failed to infer type for column {original_name}: {e}")
        
        # Create table schema
        try:
            create_stmt = DbUtils.create_table_sql(table_name, inferred_types, "snowflake")
        except Exception as e:
            raise Exception(f"Failed to create Snowflake table schema: {str(e)}")
            
        # Convert values (using postgres converter as a base)
        converted_df = df.copy()
        for col in df.columns:
            try:
                converted_df[col] = df[col].map(
                    lambda value: TypeUtils.convert_values_to_postgres_type(
                        value, target_type=inferred_types[col]
                    )
                )
            except Exception as e:
                raise Exception(f"Failed to convert values for column {col}: {e}")
                
        # Execute DROP and CREATE
        try:
            async with engine.begin() as conn:
                # Snowflake uses double quotes for identifiers
                await conn.execute(text(f'DROP TABLE IF EXISTS "{table_name}";'))
                await conn.execute(text(create_stmt))
        except Exception as e:
            raise Exception(f"Failed to create Snowflake table: {str(e)}")
            
        # Prepare and execute INSERT
        try:
            insert_cols = ", ".join(f'"{c}"' for c in df.columns)
            placeholders = ", ".join([f":{c}" for c in df.columns])
            insert_sql = f'INSERT INTO "{table_name}" ({insert_cols}) VALUES ({placeholders})'
            
            async with engine.begin() as conn:
                rows_to_insert = []
                chunk_size = 5000
                
                for idx, row in enumerate(
                    converted_df.replace({np.nan: None}).to_dict("records")
                ):
                    rows_to_insert.append(row)
                    
                    # Batch insert when chunk size reached or at the end
                    if len(rows_to_insert) == chunk_size or idx == len(converted_df) - 1:
                        await conn.execute(text(insert_sql), rows_to_insert)
                        rows_to_insert = []
        except Exception as e:
            raise Exception(f"Failed to insert data into Snowflake: {str(e)}")
            
        LOGGER.info(f"Successfully imported {len(df)} rows into Snowflake table '{table_name}'.")
        return {"success": True, "inferred_types": inferred_types}
        
    @staticmethod
    async def export_df_to_postgres(
        df: pd.DataFrame,
        table_name: str,
        db_connection_string: str,
        chunksize: int = 5000,
    ):
        """
        Export a pandas DataFrame to PostgreSQL (legacy method).
        This method is maintained for backward compatibility.
        
        Args:
            df: DataFrame to export
            table_name: Name of the target table
            db_connection_string: Database connection string
            chunksize: Number of rows to insert at once

        Returns:
            Dictionary with success status and inferred types
        """
        return await DbUtils.export_df_to_db(
            df, table_name, db_connection_string, "postgres", chunksize
        )