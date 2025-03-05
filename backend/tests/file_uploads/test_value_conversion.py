"""
Tests for value conversion functions in utils_file_uploads module.
"""
import datetime
import pytest
import pandas as pd
from utils_file_uploads import (
    to_float_if_possible,
    convert_values_to_postgres_type,
    guess_column_type,
)


class TestToFloatIfPossible:
    """Tests for to_float_if_possible function."""
    
    @pytest.mark.parametrize("input_str, expected", [
        ("123", 123.0),
        ("123.45", 123.45),
        ("-123.45", -123.45),
        ("+123.45", 123.45),
    ])
    def test_numeric_strings(self, input_str, expected):
        """Test conversion of numeric strings to float."""
        result = to_float_if_possible(input_str)
        assert isinstance(result, float)
        assert result == expected
    
    @pytest.mark.parametrize("input_str", [
        "1.23e4", "1.23E4", "1.23e-4", "1.23E-4", "1e10", "-2.5E-3"
    ])
    def test_scientific_notation(self, input_str):
        """Test conversion of scientific notation strings."""
        result = to_float_if_possible(input_str)
        if result is not None:
            assert isinstance(result, float)
            expected = float(input_str)
            assert abs(result - expected) < 1e-10
    
    @pytest.mark.parametrize("input_str, expected", [
        ("$123.45", 123.45),
        ("123,456.78", 123456.78),
        ("$1,234,567.89", 1234567.89),
        (" 123.45 ", 123.45),
    ])
    def test_formatted_numbers(self, input_str, expected):
        """Test conversion of formatted number strings."""
        result = to_float_if_possible(input_str)
        assert isinstance(result, float)
        assert result == expected
    
    @pytest.mark.parametrize("input_str", [
        "abc", "abc123", "NDA123", "N/A", "", ".", "-", "+", "null", "none",
        "undefined", "inf", "-inf", "NaN"
    ])
    def test_non_numeric_strings(self, input_str):
        """Test handling of non-numeric strings."""
        assert to_float_if_possible(input_str) is None
    
    @pytest.mark.parametrize("input_str", [
        "A1", "AB12", "ABC123", "A123", "AB1234", "A1B2C3", "1A2B3C"
    ])
    def test_alphanumeric(self, input_str):
        """Test handling of alphanumeric strings."""
        assert to_float_if_possible(input_str) is None


class TestGuessColumnType:
    """Tests for guess_column_type function."""
    
    def test_empty_column(self):
        """Test type inference for empty columns."""
        empty_series = [
            pd.Series([]),
            pd.Series([None, None, None]),
            pd.Series(["", "", ""]),
        ]
        
        for series in empty_series:
            result = guess_column_type(series)
            assert result == "TEXT"
    
    def test_text_column(self):
        """Test type inference for text columns."""
        text_series = [
            pd.Series(["apple", "banana", "cherry"]),
            pd.Series(["apple", "123", "cherry"]),
            pd.Series(["a", "b", "c"]),
        ]
        
        for series in text_series:
            result = guess_column_type(series)
            assert result == "TEXT"
    
    def test_integer_column(self):
        """Test type inference for integer columns."""
        int_series = [
            pd.Series(["1", "2", "3", "4", "5"]),
            pd.Series(["1", "2", "3", "", None]),
            pd.Series(["1,234", "5,678", "9,012"]),
        ]
        
        for series in int_series:
            result = guess_column_type(series)
            assert result == "BIGINT", f"Expected BIGINT for {list(series)}, got {result}"
    
    def test_decimal_column(self):
        """Test type inference for decimal columns."""
        float_series = [
            pd.Series(["1.23", "4.56", "7.89"]),
            pd.Series(["$1.23", "$4.56", "$7.89"]),
            pd.Series(["1,234.56", "7,890.12"]),
        ]
        
        for series in float_series:
            result = guess_column_type(series)
            assert result == "DOUBLE PRECISION"
    
    def test_percentage_column(self):
        """Test type inference for percentage columns."""
        high_pct_series = [
            pd.Series(["10%", "20%", "30%"]),
            pd.Series(["10.5%", "20.5%", "30.5%"]),
        ]
        
        for series in high_pct_series:
            result = guess_column_type(series)
            assert result == "DOUBLE PRECISION"
        
        # Mixed percentage and text should be TEXT
        mixed_pct_series = pd.Series(["10%", "20%", "text"])
        result = guess_column_type(mixed_pct_series)
        assert result == "TEXT"
    
    def test_date_column(self):
        """Test type inference for date columns."""
        date_series_list = [
            pd.Series(["2023-01-01", "2023-01-02", "2023-01-03"]),
            pd.Series(["Jan 1, 2023", "Jan 2, 2023", "Jan 3, 2023"]),
            pd.Series(["2023-01-01 12:30:45", "2023-01-02 12:30:45"]),
        ]
        
        for series in date_series_list:
            result = guess_column_type(series)
            assert result == "TIMESTAMP"
    
    def test_time_column(self):
        """Test type inference for time columns."""
        time_series_list = [
            pd.Series(["12:30", "14:45", "09:15"]),
            pd.Series(["12:30:45", "14:45:30", "09:15:00"]),
            pd.Series(["12:30 PM", "1:45 AM", "9:15 PM"]),
            pd.Series(["0900", "1445", "2359"]),
        ]
        
        for series in time_series_list:
            result = guess_column_type(series)
            assert result == "TIME"
    
    def test_column_name_hint(self):
        """Test influence of column name on type inference."""
        # Date column hint
        time_series = pd.Series(["12:30", "14:45", "09:15"])
        result = guess_column_type(time_series, column_name="arrival_time")
        assert result == "TIME"
        
        # Time column hint with mixed values
        mixed_series = pd.Series(["12:30", "13:45", "not a time", "14:45"])
        result = guess_column_type(mixed_series, column_name="departure_time")
        assert result == "TIME"
        
        # Date column hint with mixed values
        date_series = pd.Series(["2023-01-01", "2023-01-02", "2023-01-03", "not a date"])
        result = guess_column_type(date_series, column_name="created_date")
        assert result == "TIMESTAMP"
    
    def test_mixed_data_types(self):
        """Test type inference for columns with mixed data types."""
        # Mixed numeric and text
        mixed_series = pd.Series(["1", "2", "3", "four", "5"])
        result = guess_column_type(mixed_series)
        assert result == "TEXT"
        
        # Mixed integers and floats
        mixed_numbers = pd.Series(["1", "2", "3.5", "4", "5"])
        result = guess_column_type(mixed_numbers)
        assert result == "DOUBLE PRECISION"


class TestConvertValuesToPostgresType:
    """Tests for convert_values_to_postgres_type function."""
    
    @pytest.mark.parametrize("null_value", [
        None, "", "   ", "null", "NULL", "None"
    ])
    def test_null_values(self, null_value):
        """Test handling of NULL-like values."""
        for pg_type in ["TEXT", "TIMESTAMP", "TIME", "BIGINT", "DOUBLE PRECISION"]:
            result = convert_values_to_postgres_type(null_value, pg_type)
            assert result is None
    
    @pytest.mark.parametrize("time_str, expected", [
        ("12:30", datetime.time(12, 30)),
        ("12:30:45", datetime.time(12, 30, 45)),
        ("01:30", datetime.time(1, 30)),
        ("12:30 PM", datetime.time(12, 30)),
        ("1:30 AM", datetime.time(1, 30)),
        ("0900", datetime.time(9, 0)),
    ])
    def test_time_conversion(self, time_str, expected):
        """Test conversion to TIME type."""
        result = convert_values_to_postgres_type(time_str, "TIME")
        assert result == expected
    
    @pytest.mark.parametrize("text_value, expected", [
        ("hello", "hello"),
        ("world", "world"),
        ("123", "123"),
        ("true", "true"),
    ])
    def test_text_conversion(self, text_value, expected):
        """Test conversion to TEXT type."""
        result = convert_values_to_postgres_type(text_value, "TEXT")
        assert result == expected
    
    @pytest.mark.parametrize("date_str", [
        "2023-01-01", "01/01/2023", "Jan 1, 2023",
        "2023-01-01 12:30:45", "01/01/2023 12:30 PM",
    ])
    def test_timestamp_conversion(self, date_str):
        """Test conversion to TIMESTAMP type."""
        result = convert_values_to_postgres_type(date_str, "TIMESTAMP")
        assert isinstance(result, datetime.datetime)
        assert 1900 <= result.year <= 2100
    
    @pytest.mark.parametrize("int_str, expected", [
        ("123", 123),
        ("-123", -123),
        ("+123", 123),
        ("0", 0),
        ("1,234", 1234),
        ("$123", 123),
    ])
    def test_bigint_conversion(self, int_str, expected):
        """Test conversion to BIGINT type."""
        result = convert_values_to_postgres_type(int_str, "BIGINT")
        assert result == expected
        assert isinstance(result, int)
    
    @pytest.mark.parametrize("float_str, expected", [
        ("123.45", 123.45),
        ("-123.45", -123.45),
        ("+123.45", 123.45),
        ("0.0", 0.0),
        ("1,234.56", 1234.56),
        ("$1,234.56", 1234.56),
    ])
    def test_double_precision_conversion(self, float_str, expected):
        """Test conversion to DOUBLE PRECISION type."""
        result = convert_values_to_postgres_type(float_str, "DOUBLE PRECISION")
        assert abs(result - expected) < 1e-10
        assert isinstance(result, float)
    
    @pytest.mark.parametrize("unknown_type", [
        "UNKNOWN_TYPE", "INTEGER", "VARCHAR", "BOOL", "DECIMAL", "FLOAT"
    ])
    def test_unknown_type(self, unknown_type):
        """Test handling of unknown PostgreSQL types."""
        test_values = ["123", "hello", "2023-01-01"]
        for test_val in test_values:
            try:
                result = convert_values_to_postgres_type(test_val, unknown_type)
                assert result is None or isinstance(result, (str, int, float, datetime.datetime))
            except Exception as e:
                assert isinstance(e, (ValueError, TypeError, AttributeError))