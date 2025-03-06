"""
Shared fixtures and utilities for testing utils_file_uploads module.
"""
import pytest
import pandas as pd
import numpy as np
from unittest.mock import patch, MagicMock, AsyncMock


@pytest.fixture
def sample_dataframes():
    """Provides sample dataframes for testing type inference and conversion."""
    # Basic dataframe with different data types
    df_basic = pd.DataFrame({
        'text_col': ['apple', 'banana', 'cherry'],
        'int_col': ['1', '2', '3'],
        'float_col': ['1.1', '2.2', '3.3'],
        'date_col': ['2023-01-01', '2023-01-02', '2023-01-03'],
        'time_col': ['12:30', '14:45', '09:15']
    })
    
    # Dataframe with null values
    df_nulls = pd.DataFrame({
        'text_col': ['apple', '', None],
        'int_col': ['1', None, '3'],
        'float_col': [None, '2.2', ''],
        'date_col': ['', None, '2023-01-03'],
        'time_col': ['12:30', None, '']
    })
    
    # Dataframe with problematic column names
    df_bad_columns = pd.DataFrame({
        'Product Name': ['Product A', 'Product B', 'Product C'],
        '1Price': ['10.99', '20.99', '30.99'],
        'SELECT': ['yes', 'no', 'maybe'],  # SQL reserved keyword
        'column-with-hyphens': ['X', 'Y', 'Z']
    })
    
    # Dataframe with formatted values
    df_formatted = pd.DataFrame({
        'price_col': ['$1,234.56', '$2,345.67', '$3,456.78'],
        'percent_col': ['10%', '20%', '30%'],
        'currency_code': ['USD 100', 'EUR 200', 'GBP 300']
    })
    
    # Dataframe with mixed data types
    df_mixed = pd.DataFrame({
        'mixed_col': ['apple', '2', '3.3', '2023-01-01'],
        'mostly_int': ['1', '2', 'three', '4'],
        'mostly_date': ['2023-01-01', 'not a date', '2023-01-03', '2023-01-04']
    })
    
    # DataFrame with date-suggesting column names
    df_date_cols = pd.DataFrame({
        'created_date': ['001', '002', '003'],
        'modified_at': ['2023-01-01', '2023-01-02', '2023-01-03'],
        'year': ['2020', '2021', '2022']
    })
    
    # DataFrame with extreme values
    df_extreme = pd.DataFrame({
        'big_numbers': ['9' * 18, '-' + '9' * 18, '0'],
        'scientific': ['1.23e+20', '4.56e-20', '7.89e+0'],
        'long_text': ['a' * 1000, 'b' * 1000, 'c' * 1000]
    })
    
    return {
        'basic': df_basic,
        'nulls': df_nulls,
        'bad_columns': df_bad_columns,
        'formatted': df_formatted,
        'mixed': df_mixed,
        'date_cols': df_date_cols,
        'extreme': df_extreme
    }


@pytest.fixture
def mock_postgres_connection():
    """Sets up a mock PostgreSQL connection for testing."""
    with patch('utils_file_uploads.create_async_engine') as mock_engine:
        # Configure the mock connection and execution
        mock_engine_instance = MagicMock()
        mock_conn = AsyncMock()
        
        # Track executed SQL and parameters
        executed_sql = []
        inserted_rows = []
        
        async def mock_execute(sql, params=None):
            sql_str = str(sql)
            executed_sql.append(sql_str)
            if params and isinstance(params, list) and len(params) > 0:
                inserted_rows.extend(params)
            return None
        
        mock_conn.execute = mock_execute
        mock_engine_instance.begin.return_value.__aenter__.return_value = mock_conn
        mock_engine.return_value = mock_engine_instance
        
        yield {
            'engine': mock_engine,
            'connection': mock_conn,
            'executed_sql': executed_sql,
            'inserted_rows': inserted_rows
        }


@pytest.fixture
def db_conn_string():
    """Provides a mock database connection string."""
    return "postgresql+asyncpg://postgres:postgres@agents-postgres:5432/testdb"


@pytest.fixture
def date_column_names():
    """Returns a list of column names that suggest date data."""
    return [
        "date", "created_date", "modified_date", "start_date", "end_date",
        "time", "timestamp", "created_time", "datetime",
        "year", "month", "day", "quarter", "fiscal_year",
        "create_dt", "update_dt", "birth_date", "dob",
        "period", "calendar_date", "fiscal_period",
        "dtm", "dt", "ymd", "mdy", "dmy",
    ]


@pytest.fixture
def time_column_names():
    """Returns a list of column names that suggest time data."""
    return [
        "time", "hour", "minute", "second",
        "start_time", "end_time", "arrival_time", "departure_time",
    ]


@pytest.fixture
def test_date_strings():
    """Provides various date string formats for testing."""
    return {
        'standard_dates': [
            "2023-01-01", "01/01/2023", "1/1/2023",
            "2023/01/01", "2023.01.01", "01-01-2023",
            "Jan 1, 2023", "January 1, 2023", "01-Jan-2023",
        ],
        'date_times': [
            "2023-01-01 12:30:45", "01/01/2023 12:30:45",
            "2023/01/01 12:30", "2023-01-01T12:30:45",
            "Jan 1, 2023 12:30 PM", "01-Jan-2023 12:30:45",
        ],
        'ambiguous_dates': [
            "2023", "20230101", "01Jan2023", "210131", "13-14-2023",
        ],
        'invalid_dates': [
            "not a date", "hello world", "abc123", "$1,234.56", "N/A", "",
        ]
    }


@pytest.fixture
def test_time_strings():
    """Provides various time string formats for testing."""
    return {
        'standard_times': [
            "12:30", "12:30:45", "1:30", "01:30",
            "12:30 PM", "1:30 AM", "12:30:45 PM", "01:30:45 AM",
        ],
        'military_times': [
            "0900", "1430", "2359", "0000",
        ],
        'invalid_times': [
            "25:00", "12:60", "12:30:60", "1234567",
            "123", "12-30", "12/30", "12.30",
            "not a time", "2023-01-01", "January",
        ]
    }


@pytest.fixture
def run_async():
    """Helper to run async tests in a synchronous test method."""
    import asyncio
    
    def _run_async(coro):
        return asyncio.run(coro)
    
    return _run_async