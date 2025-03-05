# Database Upload Utilities Test Suite

This test suite covers the `utils_file_uploads` module, which provides utilities for uploading and processing data into PostgreSQL databases.

## Refactoring Approach

The original monolithic test file was refactored to improve:

1. **Organization**: Tests are now grouped by functionality
2. **Readability**: Better docstrings and clearer test structure
3. **Maintainability**: Smaller, focused test modules
4. **Efficiency**: Shared fixtures and parameterized tests

## Directory Structure

```
tests/
├── __init__.py
├── conftest.py                       # Shared fixtures and utilities
├── test_column_detection.py          # Tests for column name detection
├── test_date_time_parsing.py         # Tests for date/time parsing utilities
├── test_value_conversion.py          # Tests for data type conversion
├── test_sql_generation.py            # Tests for SQL generation
└── test_postgres_export.py           # Integration tests for DB export
```

## Main Components Tested

The test suite covers these main utilities:

1. **Column Name Detection**:
   - `is_date_column_name` - Detects if a column name suggests date data
   - `is_time_column_name` - Detects if a column name suggests time data
   - `sanitize_column_name` - Sanitizes column names for PostgreSQL

2. **Date/Time Parsing**:
   - `can_parse_date` - Tests if a string can be parsed as a date
   - `can_parse_time` - Tests if a string can be parsed as a time

3. **Value Conversion**:
   - `to_float_if_possible` - Converts strings to floats when possible
   - `convert_values_to_postgres_type` - Converts values to appropriate PostgreSQL types
   - `guess_column_type` - Infers the appropriate PostgreSQL data type

4. **SQL Generation**:
   - `clean_table_name` - Cleans table names for PostgreSQL
   - `create_table_sql` - Generates SQL for table creation

5. **Database Export**:
   - `export_df_to_postgres` - Exports a pandas DataFrame to PostgreSQL

## Running Tests

### Prerequisites

Make sure you have these dependencies installed:

```bash
pip install pytest pytest-asyncio pandas numpy
```

### Running All Tests

```bash
pytest tests/
```

### Running Specific Test Modules

```bash
pytest tests/test_column_detection.py
pytest tests/test_date_time_parsing.py
pytest tests/test_value_conversion.py
pytest tests/test_sql_generation.py
pytest tests/test_postgres_export.py
```

### Running Tests With Coverage

```bash
pytest --cov=utils_file_uploads tests/
```

## Key Testing Patterns

1. **Parameterized Tests**: Used to test multiple inputs with the same logic
   ```python
   @pytest.mark.parametrize("input_str, expected", [
       ("123", 123.0),
       ("123.45", 123.45),
   ])
   def test_example(input_str, expected):
       result = some_function(input_str)
       assert result == expected
   ```

2. **Fixtures**: Used to share test data
   ```python
   @pytest.fixture
   def sample_data():
       return {"key": "value"}
       
   def test_with_fixture(sample_data):
       assert sample_data["key"] == "value"
   ```

3. **Async Testing**: For testing async database functions
   ```python
   @pytest.mark.asyncio
   async def test_async_function():
       result = await some_async_function()
       assert result == expected
   ```

## Mocking Strategy

Database interactions are mocked using:

1. **SQLAlchemy Engine Mock**: To avoid real database connections
2. **Connection Mock**: To capture executed SQL statements
3. **Execute Mock**: To simulate SQL execution and track parameters

This allows testing database interactions without a real database.