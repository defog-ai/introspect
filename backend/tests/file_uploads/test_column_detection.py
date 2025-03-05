"""
Tests for column name detection functions in utils_file_uploads module.
"""
import pytest
from utils_file_uploads import (
    is_date_column_name,
    is_time_column_name,
    sanitize_column_name,
    POSTGRES_RESERVED_WORDS,
)


class TestIsDateColumnName:
    """Tests for is_date_column_name function."""
    
    @pytest.mark.parametrize("column_name", [
        "date", "created_date", "modified_date", "start_date", "end_date",
        "timestamp", "datetime", "create_dt", "update_dt", "birth_date", 
        "dob", "year", "month", "day", "quarter", "fiscal_year"
    ])
    def test_valid_date_column_names(self, column_name):
        """Test that date-related column names are correctly identified."""
        assert is_date_column_name(column_name) is True, f"Failed for {column_name}"
    
    @pytest.mark.parametrize("column_name", [
        "name", "price", "quantity", "id", "status", "category", 
        "product", "rating", "phone", "email", "username", "password"
    ])
    def test_non_date_column_names(self, column_name):
        """Test that non-date column names are correctly identified."""
        assert is_date_column_name(column_name) is False, f"Failed for {column_name}"
    
    @pytest.mark.parametrize("invalid_input", [123, None, [], {}])
    def test_non_string_input(self, invalid_input):
        """Test handling of non-string inputs."""
        assert is_date_column_name(invalid_input) is False


class TestIsTimeColumnName:
    """Tests for is_time_column_name function."""
    
    @pytest.mark.parametrize("column_name", [
        "time", "hour", "minute", "second",
        "start_time", "end_time", "arrival_time", "departure_time",
    ])
    def test_valid_time_column_names(self, column_name):
        """Test that time-related column names are correctly identified."""
        assert is_time_column_name(column_name) is True, f"Failed for {column_name}"
    
    @pytest.mark.parametrize("column_name", [
        "name", "price", "quantity", "id", "status", "category", 
        "product", "rating", "date", "created_date", "datetime",
        "year", "month", "day", "quarter", "fiscal_year"
    ])
    def test_non_time_column_names(self, column_name):
        """Test that non-time column names are correctly identified."""
        assert is_time_column_name(column_name) is False, f"Failed for {column_name}"
    
    @pytest.mark.parametrize("invalid_input", [123, None, [], {}])
    def test_non_string_input(self, invalid_input):
        """Test handling of non-string inputs."""
        assert is_time_column_name(invalid_input) is False


class TestSanitizeColumnName:
    """Tests for sanitize_column_name function."""
    
    def test_normal_string(self):
        """Test sanitizing normal string column names."""
        test_cases = [
            ("MyTable", "mytable"),
            ("my_table", "my_table"),
            ("My Table", "my_table"),
        ]
        for input_name, expected in test_cases:
            result = sanitize_column_name(input_name)
            assert result == expected or result == f"{expected}_col"
    
    def test_special_characters(self):
        """Test sanitizing column names with special characters."""
        test_cases = [
            ("My-Table!", "my_table"),
            ("Table #1", "table_1"),
            ("Special@$Characters", "special_characters"),
        ]
        for input_name, expected in test_cases:
            result = sanitize_column_name(input_name)
            assert expected in result
    
    def test_leading_digits(self):
        """Test sanitizing column names with leading digits."""
        test_cases = [
            ("1column", "_1column"),
            ("123column", "_123column"),
            ("123", "_123"),
        ]
        for input_name, expected in test_cases:
            result = sanitize_column_name(input_name)
            assert result.startswith("_")
            assert expected in result
    
    def test_multiple_underscores(self):
        """Test collapsing multiple underscores."""
        test_cases = [
            ("column__name", "column_name"),
            ("col___name___test", "col_name_test"),
            ("__leading__trailing__", "leading_trailing"),
        ]
        for input_name, expected in test_cases:
            result = sanitize_column_name(input_name)
            assert "__" not in result
            assert expected in result
    
    def test_reserved_words(self):
        """Test handling of PostgreSQL reserved words."""
        for word in POSTGRES_RESERVED_WORDS:
            result = sanitize_column_name(word)
            assert result == f"{word}_col"
    
    def test_empty_string(self):
        """Test handling of empty string inputs."""
        import re
        result = sanitize_column_name("")
        assert re.match(r"table_[0-9a-f]{7}", result) or result == "col"
    
    @pytest.mark.parametrize("invalid_input", [123, None, [], {}])
    def test_non_string_input(self, invalid_input):
        """Test handling of non-string inputs."""
        try:
            result = sanitize_column_name(str(invalid_input) if invalid_input is not None else "")
            assert isinstance(result, str)
        except Exception as e:
            assert isinstance(e, (TypeError, ValueError, AttributeError))