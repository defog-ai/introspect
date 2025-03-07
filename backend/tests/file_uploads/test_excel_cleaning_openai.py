"""
Tests for Excel file cleaning with OpenAI functionality in utils_file_uploads module.
"""
import pytest
import pandas as pd
from unittest.mock import patch
from utils_file_uploads import ExcelUtils


class TestExcelCleaningOpenAI:
    """Tests for OpenAI-based Excel cleaning functionality."""

    @pytest.mark.asyncio
    async def test_clean_excel_openai_basic(self):
        """Test the OpenAI cleaning function with basic input that needs cleaning."""
        # Create a dataframe that will be detected as "dirty" - with a repeated header row
        df = pd.DataFrame([
            ['Company Report', 'Company Report', 'Company Report'],  # Repeated header
            ['ID', 'Name', 'Price'], 
            [1, 'Item A', 10.5],
            [2, 'Item B', 20.75],
            [3, 'Item C', 15.25]
        ])
        
        # Ensure cleaning is performed using the real is_table_dirty function
        # Call the function with the real OpenAI client
        result = await ExcelUtils.clean_excel_openai("test_table", df)
        
        # Check that the data was processed
        assert isinstance(result, pd.DataFrame)
        # The cleaned dataframe should not have the "Company Report" row
        assert 'Company Report' not in result.values.flatten()

    @pytest.mark.asyncio
    async def test_clean_excel_openai_skip_cleaning(self):
        """Test that the function skips cleaning when the dataframe is clean."""
        # Create a clean dataframe
        clean_df = pd.DataFrame({
            'ID': [1, 2, 3, 4, 5],
            'Name': ['Product A', 'Product B', 'Product C', 'Product D', 'Product E'],
            'Price': [10.5, 20.75, 15.25, 30.00, 25.50]
        })
        
        # Mock is_table_dirty to return False to skip cleaning
        with patch('utils_file_uploads.ExcelUtils.is_table_dirty', return_value=False):
            # Call the function
            result = await ExcelUtils.clean_excel_openai("clean_table", clean_df)
            
            # Should return the original dataframe without cleaning
            assert result is clean_df

    @pytest.mark.asyncio
    async def test_clean_excel_openai_wide_format(self):
        """Test cleaning of wide format data."""
        # Create a dataframe in wide format that would need cleaning
        df = pd.DataFrame({
            'Product': ['Item A', 'Item B', 'Item C'],
            'Q1 Sales': [100, 200, 300],
            'Q2 Sales': [150, 250, 350],
            'Q3 Sales': [120, 220, 320],
            'Q4 Sales': [180, 280, 380]
        })
        
        # Call the function with the real OpenAI client
        result = await ExcelUtils.clean_excel_openai("wide_format_table", df)
        
        # Check that the data was processed
        assert isinstance(result, pd.DataFrame)
        
        # The result should either be the original dataframe (if dirty check failed) 
        # or a cleaned dataframe (if OpenAI processing was successful)
        # We can't guarantee the exact transformation, but we can check it's a valid dataframe
        assert result.shape[0] > 0
        assert result.shape[1] > 0
        
    @pytest.mark.asyncio
    async def test_clean_excel_openai_with_totals(self):
        """Test cleaning of data with Total rows."""
        # Create a dataframe with a Total row that would need cleaning
        df = pd.DataFrame([
            ['Quarterly Results', 'Quarterly Results', 'Quarterly Results'],  # Repeated header
            ['ID', 'Product', 'Price'],
            [1, 'Item A', 10.5],
            [2, 'Item B', 20.5],
            [3, 'Item C', 30.5],
            ['Total', '', 61.5]  # Total row
        ])
        
        # Call the function with the real OpenAI client
        result = await ExcelUtils.clean_excel_openai("table_with_totals", df)
        
        # Check that the data was processed
        assert isinstance(result, pd.DataFrame)
        
        # The cleaned dataframe should either not have the "Total" row or be restructured
        # If processing was successful, "Total" shouldn't be in the index anymore
        if result.shape[0] < df.shape[0]:  # If rows were removed
            assert 'Total' not in result.iloc[:, 0].values
            
    @pytest.mark.asyncio
    async def test_temporary_file_removal(self):
        """Test that temporary files are properly created and removed."""
        import tempfile
        import os
        
        # Create a dataframe that would need cleaning
        df = pd.DataFrame([
            ['Quarterly Report', 'Quarterly Report', 'Quarterly Report'],  # Repeated header
            ['ID', 'Name', 'Price'],
            [1, 'Item A', 10.5],
            [2, 'Item B', 20.5],
            ['Total', '', 31.0]  # Total row
        ])
        
        # Track created temporary files
        created_temp_files = []
        
        # Mock the NamedTemporaryFile to track the created file path
        original_named_temp_file = tempfile.NamedTemporaryFile
        
        def mock_named_temp_file(**kwargs):
            temp_file = original_named_temp_file(**kwargs)
            created_temp_files.append(temp_file.name)
            return temp_file
        
        # Mock is_table_dirty to ensure cleaning is attempted
        with patch('utils_file_uploads.ExcelUtils.is_table_dirty', return_value=True), \
             patch('tempfile.NamedTemporaryFile', side_effect=mock_named_temp_file):
            
            # Call the function that creates and should remove the temp file
            await ExcelUtils.clean_excel_openai("test_table", df)
            
            # Verify that the temporary file was created
            assert len(created_temp_files) == 1
            temp_file_path = created_temp_files[0]
            
            # Verify that the temporary file was removed
            assert not os.path.exists(temp_file_path), f"Temporary file {temp_file_path} was not removed"
        
    @pytest.mark.asyncio
    async def test_excel_sheet_count_preserved(self):
        """Test that the number of tables/sheets is preserved after OpenAI cleaning."""
        import asyncio
        
        # Create a test case with multiple dataframes representing multiple Excel sheets
        # Sheet 1 with repeated headers that needs cleaning
        sheet1_df = pd.DataFrame([
            ['Monthly Report', 'Monthly Report', 'Monthly Report'],  # Repeated header
            ['ID', 'Product', 'Price'],
            [1, 'Item A', 10.5],
            [2, 'Item B', 20.5],
            [3, 'Item C', 30.5]
        ])
        
        # Sheet 2 is clean and doesn't need cleaning
        sheet2_df = pd.DataFrame({
            'ID': [1, 2, 3],
            'Category': ['X', 'Y', 'Z'],
            'Count': [10, 20, 30],
        })
        
        # Sheet 3 in wide format that needs cleaning
        sheet3_df = pd.DataFrame({
            'Product': ['A', 'B', 'C'],
            'Q1 Value': [100, 200, 300],
            'Q2 Value': [150, 250, 350],
        })
        
        # Original tables dictionary with multiple sheets
        original_tables = {
            'sheet1': sheet1_df,
            'sheet2': sheet2_df,
            'sheet3': sheet3_df
        }
        
        # For deterministic testing, we'll mock is_table_dirty
        # This way we control which sheets get cleaned
        async def mock_is_dirty(table_name, df):
            # Only sheets 1 and 3 need cleaning
            return table_name in ['sheet1', 'sheet3']
            
        # Create tasks for each table (similar to file_upload_routes.py)
        with patch('utils_file_uploads.ExcelUtils.is_table_dirty', side_effect=mock_is_dirty):
            tasks = []
            table_names = []
            for table_name, df in original_tables.items():
                tasks.append(ExcelUtils.clean_excel_openai(table_name, df))
                table_names.append(table_name)
                
            # Gather results and recreate dictionary
            cleaned_tables = dict(zip(table_names, await asyncio.gather(*tasks)))
            
            # Test that the number of tables is preserved
            assert len(cleaned_tables) == len(original_tables)
            
            # Test that all original table names are present
            for table_name in original_tables.keys():
                assert table_name in cleaned_tables
                
            # All tables should have data
            for table_name, df in cleaned_tables.items():
                assert isinstance(df, pd.DataFrame)
                assert df.shape[0] > 0
                assert df.shape[1] > 0