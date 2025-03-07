"""
Tests for CSV file cleaning functionality in utils_file_uploads module.
"""
import pytest
import pandas as pd
import io
from unittest.mock import patch, AsyncMock, MagicMock
from utils_file_uploads import CSVUtils
from utils_file_uploads.excel_utils import ExcelUtils

class TestCSVCleaning:
    """Tests for CSV cleaning functionality."""

    @pytest.fixture
    def sample_csv_data(self):
        """Create sample CSV data."""
        return """ID,Name,Value
1,Item 1,10.5
2,Item 2,20.5

3,Item 3,30.5
"""
        
    @pytest.fixture
    def sample_csv_with_null_values(self):
        """Create sample CSV data with various null value representations."""
        return """ID,Name,Value,Status
1,Item 1,10.5,Active
2,Item 2,NULL,N/A
3,N/A,30.5,Inactive
4,Item 4,-,Active
5,--,50.5,Pending
"""

    @pytest.fixture
    def sample_csv_with_trailing_spaces(self):
        """Create sample CSV data with trailing spaces in text fields."""
        return """ID,Name,Value,Category
1,Product A  ,10.5,Electronics  
2,Product B,20.5,  Office Supplies
3,Product C   ,30.5,Furniture
"""


    @pytest.fixture
    def sample_dirty_csv_data(self):
        """Create sample CSV data that needs OpenAI cleaning."""
        return """Quarterly Report,Quarterly Report,Quarterly Report
ID,Name,Price
1,Item 1,10.5
2,Item 2,20.5
3,Item 3,30.5
Total,,61.5
Note:,All prices in USD,
"""

    @pytest.mark.asyncio
    async def test_clean_csv_pd(self, sample_csv_data):
        """Test cleaning CSV with pandas."""
        # Call the function
        result = await CSVUtils.clean_csv_pd(sample_csv_data)
        
        # Check that empty rows were removed
        assert len(result) == 3  # 3 data rows, empty row removed
        
        # Check data integrity
        assert result.iloc[0, 0] == 1
        assert result.iloc[0, 1] == "Item 1"
        assert result.iloc[0, 2] == 10.5
        
        # Check that NaN values were replaced with empty strings
        assert result.isnull().sum().sum() == 0
        
    @pytest.mark.asyncio
    async def test_clean_csv_pd_null_values(self, sample_csv_with_null_values):
        """Test cleaning CSV with various NULL value representations."""
        # Call the function
        result = await CSVUtils.clean_csv_pd(sample_csv_with_null_values)
        
        # Check the original dimensions - all rows present since none are completely empty
        assert len(result) == 5
        assert result.shape[1] == 4
        
        # The NULL values should have been replaced with empty strings
        # Check specific cells
        assert result.iloc[1, 2] == ""  # Value column, row 2 (NULL)
        assert result.iloc[1, 3] == ""  # Status column, row 2 (N/A)
        assert result.iloc[2, 1] == ""  # Name column, row 3 (N/A)
        assert result.iloc[3, 2] == ""  # Value column, row 4 (-)
        assert result.iloc[4, 1] == ""  # Name column, row 5 (--)
        
        # Non-null values should be preserved
        assert result.iloc[0, 0] == 1
        assert result.iloc[0, 1] == "Item 1"
        assert result.iloc[0, 2] == "10.5" # Note that the type is changed to string since reading it as a csv infers the whole column as string
        assert result.iloc[0, 3] == "Active"
        
    @pytest.mark.asyncio
    async def test_clean_csv_pd_trailing_spaces(self, sample_csv_with_trailing_spaces):
        """Test cleaning CSV with trailing spaces in text fields."""
        # Call the function
        result = await CSVUtils.clean_csv_pd(sample_csv_with_trailing_spaces)
        
        # Check that trailing spaces were removed
        assert result.iloc[0, 1] == "Product A"  # Was "Product A  "
        assert result.iloc[0, 3] == "Electronics"  # Was "Electronics  "
        assert result.iloc[1, 3] == "Office Supplies"  # Was "  Office Supplies"
        assert result.iloc[2, 1] == "Product C"  # Was "Product C   "
        
        # Number values should remain unchanged
        assert result.iloc[0, 2] == 10.5
        assert result.iloc[1, 2] == 20.5
        assert result.iloc[2, 2] == 30.5

            
    @pytest.mark.asyncio
    async def test_clean_csv_openai_delegates(self):
        """Test that clean_csv_openai properly delegates to ExcelUtils.clean_excel_openai."""
        # Create sample dataframe
        df = pd.DataFrame({
            'ID': [1, 2, 3],
            'Name': ['Item A', 'Item B', 'Item C'],
            'Price': [10.5, 20.75, 15.25]
        })
        
        # Create mock cleaned dataframe
        mock_cleaned_df = pd.DataFrame({
            'ID': [1, 2, 3],
            'Name': ['Item A', 'Item B', 'Item C'],
            'Price': [10.5, 20.75, 15.25],
            'Cleaned': [True, True, True]  # To show it was cleaned
        })
        
        # Mock ExcelUtils.clean_excel_openai
        with patch('utils_file_uploads.excel_utils.ExcelUtils.clean_excel_openai', return_value=mock_cleaned_df):
            # Test delegation 
            result = await CSVUtils.clean_csv_openai("test_table", df)
            
            # Verify delegation worked
            assert 'Cleaned' in result.columns
            assert result.equals(mock_cleaned_df)