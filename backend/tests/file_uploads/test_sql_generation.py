"""
Tests for SQL generation functions in utils_file_uploads module.
"""
import re
import pytest
from utils_file_uploads import (
    create_table_sql,
    clean_table_name,
    sanitize_column_name,
    POSTGRES_RESERVED_WORDS,
)


class TestCleanTableName:
    """Tests for clean_table_name function."""
    
    @pytest.mark.parametrize("input_name, expected", [
        ("MyTable", "mytable"),
        ("my_table", "my_table"),
        ("My Table", "my_table"),
    ])
    def test_normal_string(self, input_name, expected):
        """Test cleaning normal table names."""
        assert clean_table_name(input_name) == expected
    
    @pytest.mark.parametrize("input_name, expected", [
        ("My-Table!", "my_table_"),
        ("Table #1", "table__1"),
        ("Special@$Characters", "special__characters"),
    ])
    def test_special_characters(self, input_name, expected):
        """Test cleaning table names with special characters."""
        assert clean_table_name(input_name) == expected
    
    def test_empty_string(self):
        """Test handling of empty string input."""
        result = clean_table_name("")
        assert re.match(r"table_[0-9a-f]{7}", result)
    
    @pytest.mark.parametrize("invalid_input", [123, None, [], {}])
    def test_non_string_input(self, invalid_input):
        """Test handling of non-string inputs."""
        with pytest.raises(ValueError):
            clean_table_name(invalid_input)


class TestCreateTableSql:
    """Tests for create_table_sql function."""
    
    def test_basic_table(self):
        """Test creating SQL for a basic table with different data types."""
        test_cases = [
            {
                "table_name": "test_table",
                "columns": {"id": "BIGINT", "name": "TEXT", "price": "DOUBLE PRECISION"},
                "expected_pattern": r'CREATE TABLE "test_table" \("id" BIGINT, "name" TEXT, "price" DOUBLE PRECISION\);'
            },
            {
                "table_name": "single_column_table",
                "columns": {"id": "BIGINT"},
                "expected_pattern": r'CREATE TABLE "single_column_table" \("id" BIGINT\);'
            },
        ]
        
        for tc in test_cases:
            result = create_table_sql(tc["table_name"], tc["columns"])
            assert re.search(tc["expected_pattern"], result, re.DOTALL)
            
            # Check that the SQL has the expected structure
            assert result.startswith('CREATE TABLE')
            assert result.endswith(');')
            
            # Check that all column names are in the SQL
            for col_name in tc["columns"].keys():
                safe_col_name = sanitize_column_name(col_name)
                assert f'"{safe_col_name}"' in result
                
            # Check that all column types are in the SQL
            for col_type in tc["columns"].values():
                assert col_type in result
    
    def test_sanitized_column_names(self):
        """Test that column names are properly sanitized in SQL."""
        problematic_columns = {
            "id": "BIGINT",
            "product name": "TEXT",  # Space
            "1price": "DOUBLE PRECISION",  # Leading digit
            "user-email": "TEXT",  # Hyphen
            "account.number": "TEXT",  # Period
            "special!@#chars": "TEXT",  # Special chars
            "ORDER": "BIGINT",  # Uppercase & reserved word
        }
        
        result = create_table_sql("test_table", problematic_columns)
        
        # Check the basic structure
        assert result.startswith('CREATE TABLE "test_table" (')
        assert result.endswith(');')
        
        # Verify each column was sanitized correctly
        expected_sanitized = {
            "id": "id",
            "product name": "product_name",
            "1price": "_1price",
            "user-email": "user_email",
            "account.number": "account_number",
            "special!@#chars": lambda x: re.search(r"special.*chars", x) is not None,
            "ORDER": "order_col",  # Reserved word gets suffix
        }
        
        for orig_name, expected in expected_sanitized.items():
            if callable(expected):
                # Handle regex matcher
                column_found = False
                for col_part in re.findall(r'"([^"]+)"', result):
                    if expected(col_part):
                        column_found = True
                        break
                assert column_found, f"Sanitized pattern for '{orig_name}' not found in SQL"
            else:
                assert f'"{expected}"' in result
    
    def test_reserved_word_columns(self):
        """Test that reserved words are properly handled."""
        reserved_columns = {
            "id": "BIGINT",
            "select": "TEXT",
            "from": "TEXT",
            "where": "TEXT",
            "order": "TEXT",
        }
        
        result = create_table_sql("test_table", reserved_columns)
        
        # Non-reserved words should remain unchanged
        assert '"id"' in result
        
        # Reserved words should get _col suffix
        for reserved_word in ["select", "from", "where", "order"]:
            assert f'"{reserved_word}_col"' in result
            assert f'"{reserved_word}"' not in result
    
    def test_empty_columns(self):
        """Test creating a table with no columns."""
        columns = {}
        result = create_table_sql("test_table", columns)
        expected_sql = 'CREATE TABLE "test_table" ();'
        assert result == expected_sql
    
    def test_complex_real_world_example(self):
        """Test a more complex, real-world example."""
        complex_columns = {
            "user_id": "BIGINT",
            "first name": "TEXT",
            "last name": "TEXT",
            "email_address": "TEXT",
            "date_of_birth": "TIMESTAMP",
            "is_active": "TEXT",
            "login_count": "BIGINT",
            "avg_session_time": "DOUBLE PRECISION",
            "select": "TEXT",  # Reserved word
            "from": "TEXT",    # Reserved word
            "___internal_id___": "TEXT",  # Multiple underscores
            "special!@#$characters": "TEXT"  # Special characters
        }
        
        result = create_table_sql("customer_profiles", complex_columns)
        
        # Basic structure check
        assert result.startswith('CREATE TABLE "customer_profiles" (')
        assert result.endswith(');')
        
        # Check for expected column name sanitization patterns
        expected_patterns = [
            "user_id",
            "first_name",  # Space converted to underscore
            "last_name",   # Space converted to underscore
            "email_address",
            "date_of_birth",
            "is_active",
            "login_count",
            "avg_session_time",
            "select_col",  # Reserved word gets _col suffix
            "from_col",    # Reserved word gets _col suffix
            "internal_id",  # Multiple underscores collapsed
            lambda x: re.search(r"special.*characters", x) is not None  # Special chars
        ]
        
        for pattern in expected_patterns:
            if callable(pattern):
                # Handle regex matcher
                column_found = False
                for col_part in re.findall(r'"([^"]+)"', result):
                    if pattern(col_part):
                        column_found = True
                        break
                assert column_found, f"Sanitized pattern not found in SQL"
            else:
                assert f'"{pattern}"' in result