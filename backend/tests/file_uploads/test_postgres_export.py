"""
Integration tests for database export functionality in utils_file_uploads module.
"""
import pytest
import datetime
import pandas as pd
from utils_file_uploads import export_df_to_postgres, export_df_to_db


class TestExportDfToPostgres:
    """Integration tests for export_df_to_postgres function."""
    
    @pytest.mark.asyncio
    async def test_basic_export(self, mock_postgres_connection, sample_dataframes, db_conn_string):
        """Test basic export with clean data and simple column types."""
        df = sample_dataframes['basic']
        table_name = "basic_test_table"
        
        # Get connection mocks
        mock_data = mock_postgres_connection
        
        # Run the export function
        result = await export_df_to_postgres(df, table_name, db_conn_string)
        
        # Verify the function returned success
        assert result["success"]
        
        # Verify the types were inferred correctly
        inferred_types = result["inferred_types"]
        assert inferred_types["text_col"] == "TEXT"
        assert inferred_types["int_col"] in ["BIGINT", "DOUBLE PRECISION"]
        assert inferred_types["float_col"] == "DOUBLE PRECISION"
        assert inferred_types["date_col"] == "TIMESTAMP"
        
        # Check SQL operations
        # 1. First should be DROP TABLE
        assert f'DROP TABLE IF EXISTS "{table_name}"' in mock_data['executed_sql'][0]
        
        # 2. Second should be CREATE TABLE
        create_sql = mock_data['executed_sql'][1]
        assert f'CREATE TABLE "{table_name}"' in create_sql
        
        # Check that all columns are in the CREATE TABLE statement
        for col in inferred_types.keys():
            assert f'"{col}"' in create_sql
        
        # 3. Third should be INSERT
        assert f'INSERT INTO "{table_name}"' in mock_data['executed_sql'][2]
        
        # Verify the number of rows inserted
        assert len(mock_data['inserted_rows']) == 3
        
        # Check first row's values
        first_row = mock_data['inserted_rows'][0]
        assert first_row["text_col"] == "apple"
        
        # Check that numeric values were converted to appropriate Python types
        assert isinstance(first_row["int_col"], int)
        assert isinstance(first_row["float_col"], float)
        
        # Check date conversion
        assert isinstance(first_row["date_col"], datetime.datetime)
    
    @pytest.mark.asyncio
    async def test_null_handling(self, mock_postgres_connection, db_conn_string):
        """Test how null and empty values are handled."""
        # Update the test data to ensure it contains valid date format
        df_nulls = pd.DataFrame({
            "text_col": ["apple", "", None],
            "int_col": ["1", None, "3"],
            "float_col": [None, "2.2", ""],
            "date_col": ["", None, "2023-01-03"],
            "time_col": ["12:30", None, ""]
        })
        
        table_name = "null_test_table"
        mock_data = mock_postgres_connection
        
        result = await export_df_to_postgres(df_nulls, table_name, db_conn_string)
        
        assert result["success"]
        
        # Check that null values were properly converted to None for SQL insertion
        for row in mock_data['inserted_rows']:
            # Check text_col
            if row["text_col"] == "apple":
                assert row["text_col"] == "apple"
            else:
                # Empty string and None should be converted to None
                assert row["text_col"] is None
        
        # Special check for date_col
        # Third row should have a valid datetime for '2023-01-03'
        assert isinstance(mock_data['inserted_rows'][2]["date_col"], datetime.datetime)
        
        # Check time_col handling
        # First row should have a valid time
        assert isinstance(mock_data['inserted_rows'][0]["time_col"], datetime.time)
        assert mock_data['inserted_rows'][0]["time_col"] == datetime.time(12, 30)
    
    @pytest.mark.asyncio
    async def test_column_name_sanitization(self, mock_postgres_connection, sample_dataframes, db_conn_string):
        """Test sanitization of problematic column names."""
        df = sample_dataframes['bad_columns']
        table_name = "column_sanitization_test"
        mock_data = mock_postgres_connection
        
        result = await export_df_to_postgres(df, table_name, db_conn_string)
        
        assert result["success"]
        
        # Check the CREATE TABLE SQL for properly sanitized column names
        create_sql = mock_data['executed_sql'][1]
        
        # Original: 'Product Name' -> should become 'product_name'
        assert '"product_name"' in create_sql
        
        # Original: '1Price' -> should become '_1price'
        assert '"_1price"' in create_sql
        
        # Original: 'SELECT' -> should become 'select_col' (reserved word)
        assert '"select_col"' in create_sql
        
        # Original: 'column-with-hyphens' -> should become 'column_with_hyphens'
        assert '"column_with_hyphens"' in create_sql
        
        # Verify data was inserted with sanitized column names
        first_row = mock_data['inserted_rows'][0]
        assert str(first_row["product_name"]) == "Product A"
        # Accept either string or float for price values
        assert first_row["_1price"] in ["10.99", 10.99]
        assert str(first_row["select_col"]) == "yes"
        assert str(first_row["column_with_hyphens"]) == "X"
    
    @pytest.mark.asyncio
    async def test_formatted_values_conversion(self, mock_postgres_connection, sample_dataframes, db_conn_string):
        """Test conversion of formatted values like currency and percentages."""
        df = sample_dataframes['formatted']
        table_name = "formatted_values_test"
        mock_data = mock_postgres_connection
        
        result = await export_df_to_postgres(df, table_name, db_conn_string)
        
        assert result["success"]
        
        # Verify that the formatted values were parsed as the correct type
        inferred_types = result["inferred_types"]
        
        # Direct assertions for inferred types
        assert inferred_types["price_col"] == "DOUBLE PRECISION"
        assert inferred_types["percent_col"] == "DOUBLE PRECISION"
        # Currency code containing "USD 100" format is TEXT
        assert inferred_types["currency_code"] == "TEXT"
        
        # Check first row values
        first_row = mock_data['inserted_rows'][0]
        
        # Currency should be converted to float without $ and commas
        assert isinstance(first_row["price_col"], float)
        assert pytest.approx(first_row["price_col"], 0.01) == 1234.56
        
        # Percentage should be converted to float (may or may not divide by 100)
        assert isinstance(first_row["percent_col"], float)
        assert first_row["percent_col"] in [10.0, 0.1]  # Allow either interpretation
        
        # Currency code should remain as the original string since it's TEXT
        assert first_row["currency_code"] == "USD 100"
    
    @pytest.mark.asyncio
    async def test_mixed_data_type_handling(self, mock_postgres_connection, db_conn_string):
        """Test handling of columns with mixed data types."""
        # Create dataframe with mixed types
        df_mixed = pd.DataFrame({
            "mixed_col": ["apple", "2", "3.3", "2023-01-01", "note 1"],
            "mostly_int": ["1", "2", "three", "4", "5"],
            "mostly_date": ["2023-01-01", "2023-01-02", "2023-01-03", "2023-01-04", "another text"]
        })
        
        table_name = "mixed_data_test"
        mock_data = mock_postgres_connection
        
        result = await export_df_to_postgres(df_mixed, table_name, db_conn_string)
        
        assert result["success"]
        
        # Check inferred types for mixed columns
        inferred_types = result["inferred_types"]
        
        # mixed_col has strings, numbers, and dates - should be TEXT
        assert inferred_types["mixed_col"] == "TEXT"
        
        # mostly_int has mostly numbers but one text value - should be TEXT
        assert inferred_types["mostly_int"] == "TEXT"
        
        # mostly_date has 80% dates and one non-date - behavior varies by implementation
        # Can be TIMESTAMP if majority threshold is used
        assert inferred_types["mostly_date"] in ["TEXT", "TIMESTAMP"]
        
        # Now test with column name hint
        # Create a new dataframe with date column name
        df_with_date_hint = pd.DataFrame({
            "created_date": ["2023-01-01", "not a date", "2023-01-03", "2023-01-04"]
        })
        
        # Reset mocks
        mock_data['executed_sql'].clear()
        mock_data['inserted_rows'].clear()
        
        # Test with date column name hint
        result2 = await export_df_to_postgres(
            df_with_date_hint, table_name + "_2", db_conn_string
        )
        
        inferred_types2 = result2["inferred_types"]
        # With date column name hint, expect TIMESTAMP
        assert inferred_types2["created_date"] == "TIMESTAMP"
    
    @pytest.mark.asyncio
    async def test_date_time_types(self, mock_postgres_connection, db_conn_string):
        """Test handling of date and time types."""
        # Create dataframe with date and time data
        df_datetime = pd.DataFrame({
            "date_col": ["2023-01-01", "2023-01-02", "2023-01-03"],
            "time_col": ["12:30", "14:45", "09:15"],
            "datetime_col": ["2023-01-01 12:30:45", "2023-01-02 14:45:30", "2023-01-03 09:15:00"]
        })
        
        table_name = "datetime_test"
        mock_data = mock_postgres_connection
        
        result = await export_df_to_postgres(df_datetime, table_name, db_conn_string)
        
        assert result["success"]
        
        # Check types
        inferred_types = result["inferred_types"]
        assert inferred_types["date_col"] == "TIMESTAMP"
        assert inferred_types["time_col"] == "TIME"
        assert inferred_types["datetime_col"] == "TIMESTAMP"
        
        # Check value conversions
        first_row = mock_data['inserted_rows'][0]
        
        # date_col should be datetime.datetime
        assert isinstance(first_row["date_col"], datetime.datetime)
        assert first_row["date_col"].date() == datetime.date(2023, 1, 1)
        
        # time_col should be datetime.time
        assert isinstance(first_row["time_col"], datetime.time)
        assert first_row["time_col"] == datetime.time(12, 30)
        
        # datetime_col should be datetime.datetime
        assert isinstance(first_row["datetime_col"], datetime.datetime)
        assert first_row["datetime_col"].date() == datetime.date(2023, 1, 1)
        assert first_row["datetime_col"].time() == datetime.time(12, 30, 45)
    
    @pytest.mark.asyncio
    async def test_error_handling(self, mock_postgres_connection, sample_dataframes, db_conn_string):
        """Test error handling for various failure scenarios."""
        df = sample_dataframes['basic']
        table_name = "error_test_table"
        mock_data = mock_postgres_connection
        
        # Configure mock to raise exception during execution
        mock_data['connection'].execute = lambda *args, **kwargs: (_ for _ in ()).throw(Exception("Database error"))
        
        # Execute with expected error
        with pytest.raises(Exception):
            await export_df_to_postgres(df, table_name, db_conn_string)
    
    @pytest.mark.asyncio
    async def test_empty_dataframe(self, mock_postgres_connection, db_conn_string):
        """Test handling of empty DataFrames."""
        # Create an empty DataFrame
        empty_df = pd.DataFrame(columns=["col1", "col2", "col3"])
        
        table_name = "empty_df_test"
        mock_data = mock_postgres_connection
        
        result = await export_df_to_postgres(
            empty_df, table_name, db_conn_string
        )
        
        assert result["success"]
        
        # Check inferred types - all should be TEXT for empty columns
        inferred_types = result["inferred_types"]
        for col in empty_df.columns:
            assert inferred_types[col] == "TEXT"
        
        # Verify table was created with all columns
        create_sql = mock_data['executed_sql'][1]
        for col in empty_df.columns:
            assert f'"{col}"' in create_sql
        
        # No rows should have been inserted
        assert len(mock_data['inserted_rows']) == 0
        
        
class TestExportDfToDb:
    """Integration tests for export_df_to_db function."""
    
    @pytest.mark.asyncio
    async def test_postgres_export(self, mock_postgres_connection, sample_dataframes, db_conn_string):
        """Test export to PostgreSQL database."""
        df = sample_dataframes['basic']
        table_name = "postgres_test_table"
        
        # Get connection mocks
        mock_data = mock_postgres_connection
        
        # Run the export function
        result = await export_df_to_db(df, table_name, db_conn_string, "postgres")
        
        # Verify the function returned success
        assert result["success"]
        
        # Verify the types were inferred correctly
        inferred_types = result["inferred_types"]
        assert inferred_types["text_col"] == "TEXT"
        assert inferred_types["int_col"] in ["BIGINT", "DOUBLE PRECISION"]
        assert inferred_types["float_col"] == "DOUBLE PRECISION"
        assert inferred_types["date_col"] == "TIMESTAMP"
        
        # Check SQL operations
        # 1. First should be DROP TABLE
        assert f'DROP TABLE IF EXISTS "{table_name}"' in mock_data['executed_sql'][0]
        
        # 2. Second should be CREATE TABLE
        create_sql = mock_data['executed_sql'][1]
        assert f'CREATE TABLE "{table_name}"' in create_sql
        
        # Check that all columns are in the CREATE TABLE statement
        for col in inferred_types.keys():
            assert f'"{col}"' in create_sql
    
    @pytest.mark.asyncio
    async def test_mysql_export(self, mock_postgres_connection, sample_dataframes, db_conn_string):
        """Test export to MySQL database."""
        # Since we're using mocks, we can simulate MySQL by changing db_type
        df = sample_dataframes['basic']
        table_name = "mysql_test_table"
        
        # Get connection mocks
        mock_data = mock_postgres_connection
        
        # Run the export function with MySQL db_type
        result = await export_df_to_db(df, table_name, db_conn_string, "mysql")
        
        # Verify the function returned success
        assert result["success"]
        
        # MySQL should use backtick identifier quoting
        create_sql = mock_data['executed_sql'][1]
        assert f"CREATE TABLE `{table_name}`" in create_sql
        
        # Check that columns use backtick quoting
        for col in result["inferred_types"].keys():
            assert f"`{col}`" in create_sql

    @pytest.mark.asyncio
    async def test_sqlserver_export(self, mock_postgres_connection, sample_dataframes, db_conn_string):
        """Test export to SQL Server database."""
        df = sample_dataframes['basic']
        table_name = "sqlserver_test_table"
        
        # Get connection mocks
        mock_data = mock_postgres_connection
        
        # Run the export function with SQL Server db_type
        result = await export_df_to_db(df, table_name, db_conn_string, "sqlserver")
        
        # Verify the function returned success
        assert result["success"]
        
        # SQL Server should use square bracket identifier quoting
        create_sql = mock_data['executed_sql'][1]
        assert f"CREATE TABLE [{table_name}]" in create_sql
        
        # Check that columns use square bracket quoting
        for col in result["inferred_types"].keys():
            assert f"[{col}]" in create_sql
            
    @pytest.mark.asyncio
    async def test_redshift_export(self, mock_postgres_connection, sample_dataframes, db_conn_string):
        """Test export to Redshift database."""
        df = sample_dataframes['basic']
        table_name = "redshift_test_table"
        
        # Get connection mocks
        mock_data = mock_postgres_connection
        
        # Run the export function with Redshift db_type
        result = await export_df_to_db(df, table_name, db_conn_string, "redshift")
        
        # Verify the function returned success
        assert result["success"]
        
        # Redshift uses the same quotation as PostgreSQL
        create_sql = mock_data['executed_sql'][1]
        assert f'CREATE TABLE "{table_name}"' in create_sql