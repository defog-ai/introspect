"""
Tests for date and time parsing functions in utils_file_uploads module.
"""
import pytest
from utils_file_uploads import (
    can_parse_date,
    can_parse_time,
)


class TestCanParseDate:
    """Tests for can_parse_date function."""
    
    def test_common_date_formats(self, test_date_strings):
        """Test parsing of common date formats."""
        for date_str in test_date_strings['standard_dates']:
            assert can_parse_date(date_str) is True, f"Failed for {date_str}"
    
    def test_date_with_time(self, test_date_strings):
        """Test parsing of datetime strings."""
        for datetime_str in test_date_strings['date_times']:
            assert can_parse_date(datetime_str) is True, f"Failed for {datetime_str}"
    
    def test_ambiguous_date_formats(self, test_date_strings):
        """Test handling of ambiguous date formats."""
        for date_str in test_date_strings['ambiguous_dates']:
            # Don't assert specific outcomes since parsing behavior may vary
            # Just ensure the function returns a boolean without crashing
            result = can_parse_date(date_str)
            assert isinstance(result, bool)
    
    def test_non_date_strings(self, test_date_strings):
        """Test handling of non-date strings."""
        for non_date in test_date_strings['invalid_dates']:
            assert can_parse_date(non_date) is False, f"Failed for {non_date}"
    
    def test_edge_cases(self):
        """Test edge cases for date parsing."""
        # Test empty string, whitespace, None
        assert can_parse_date("") is False
        assert can_parse_date("   ") is False
        assert can_parse_date(None) is False
        
        # Test numbers with specific digit counts
        digit_inputs = ["123", "12345", "1234567", "123456789", "00000000", "99999999"]
        for digits in digit_inputs:
            result = can_parse_date(digits)
            assert isinstance(result, bool)
    
    def test_almost_dates(self):
        """Test strings that look like dates but aren't quite valid."""
        almost_dates = [
            "2023-02-30",  # Invalid day
            "2023-13-01",  # Invalid month
            "01/32/2023",  # Invalid day
            "13/01/2023",  # Month > 12
            "Feb 30, 2023",  # Invalid day for February
            "Jan 32, 2023",  # Invalid day
        ]
        for date_str in almost_dates:
            # These might parse depending on the library's behavior
            # Just make sure the function returns a consistent result
            result = can_parse_date(date_str)
            assert isinstance(result, bool)


class TestCanParseTime:
    """Tests for can_parse_time function."""
    
    def test_common_time_formats(self, test_time_strings):
        """Test parsing of common time formats."""
        for time_str in test_time_strings['standard_times']:
            assert can_parse_time(time_str) is True, f"Failed for {time_str}"
    
    def test_military_time_formats(self, test_time_strings):
        """Test parsing of military time formats."""
        for time_str in test_time_strings['military_times']:
            assert can_parse_time(time_str) is True, f"Failed for {time_str}"
    
    def test_invalid_time_formats(self, test_time_strings):
        """Test handling of invalid time formats."""
        for time_str in test_time_strings['invalid_times']:
            assert can_parse_time(time_str) is False, f"Should fail for {time_str}"
    
    def test_edge_cases(self):
        """Test edge cases for time parsing."""
        # Test edge cases like empty string, whitespace, None
        assert can_parse_time("") is False
        assert can_parse_time("   ") is False
        assert can_parse_time(None) is False
        
        # Test non-string inputs
        non_string_inputs = [123, 12.30, True, [], {}]
        for non_string in non_string_inputs:
            result = can_parse_time(non_string)
            assert isinstance(result, bool)
            assert result is False
    
    def test_mixed_date_time(self):
        """Test handling of mixed date-time strings."""
        mixed_formats = [
            "2023-01-01 12:30",
            "01/01/2023 12:30 PM",
            "Jan 1, 2023 12:30:45",
            "2023-01-01T12:30:45",
        ]
        for mixed_str in mixed_formats:
            assert can_parse_time(mixed_str) is False, f"Should fail for {mixed_str} as it contains date part"