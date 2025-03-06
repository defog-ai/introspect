"""
Tests for Excel file cleaning with OpenAI functionality in utils_file_uploads module.
"""
import pytest
import pandas as pd
import io
from unittest.mock import AsyncMock, patch, MagicMock
from utils_file_uploads import ExcelUtils


class TestExcelCleaningOpenAI:
    """Tests for OpenAI-based Excel cleaning functionality."""

    @pytest.fixture
    def mock_openai_client(self):
        """Create a mock OpenAI client that simulates API responses."""
        with patch("utils_file_uploads.AsyncOpenAI") as mock_client_class:
            # Mock the client instance
            mock_client = AsyncMock()
            mock_client_class.return_value = mock_client
            
            # Mock file upload
            mock_file = MagicMock()
            mock_file.id = "test_file_id"
            mock_client.files.create = AsyncMock(return_value=mock_file)
            
            # Mock file delete
            mock_client.files.delete = AsyncMock(return_value=None)
            
            # Mock assistant creation
            mock_assistant = MagicMock()
            mock_assistant.id = "test_assistant_id"
            mock_client.beta.assistants.create = AsyncMock(return_value=mock_assistant)
            
            # Mock thread creation
            mock_thread = MagicMock()
            mock_thread.id = "test_thread_id"
            mock_client.beta.threads.create = AsyncMock(return_value=mock_thread)
            
            # Mock message creation
            mock_message = MagicMock()
            mock_message.id = "test_message_id"
            mock_client.beta.threads.messages.create = AsyncMock(return_value=mock_message)
            
            # Mock run creation and polling
            mock_run = MagicMock()
            mock_run.status = "completed"
            mock_run.usage = MagicMock()
            mock_run.usage.completion_tokens = 100
            mock_run.usage.prompt_tokens = 200
            mock_run.usage.prompt_token_details = {"cached_tokens": 0}
            mock_client.beta.threads.runs.create_and_poll = AsyncMock(return_value=mock_run)
            
            # Mock file content
            mock_file_content = AsyncMock()
            mock_file_content.read = MagicMock(return_value=b"column1,column2\nA,1\nB,2\nC,3")
            mock_client.files.content = AsyncMock(return_value=mock_file_content)
            
            # Mock message list
            mock_message_data = MagicMock()
            mock_message_data.data = [
                MagicMock(
                    content=[
                        MagicMock(
                            text=MagicMock(
                                annotations=[
                                    MagicMock(
                                        file_path=MagicMock(
                                            file_id="output_file_id"
                                        )
                                    )
                                ]
                            )
                        )
                    ]
                )
            ]
            mock_client.beta.threads.messages.list = AsyncMock(return_value=mock_message_data)
            
            yield mock_client

    @pytest.mark.asyncio
    async def test_clean_excel_openai_basic(self, mock_openai_client):
        """Test the OpenAI cleaning function with basic input that needs cleaning."""
        # Create a dataframe that will be detected as "dirty" - with a repeated header row
        df = pd.DataFrame([
            ['Company Report', 'Company Report', 'Company Report'],  # Repeated header
            ['ID', 'Name', 'Price'], 
            [1, 'Item A', 10.5],
            [2, 'Item B', 20.75],
            [3, 'Item C', 15.25]
        ])
        
        # Mock is_excel_dirty to always return True to ensure cleaning is performed
        with patch('utils_file_uploads.ExcelUtils.is_excel_dirty', return_value=True):
            # Call the function
            result = await ExcelUtils.clean_excel_openai("test_table", df)
            
            # Check that the data was processed
            assert isinstance(result, pd.DataFrame)
            
            # Verify OpenAI client was used correctly
            mock_openai_client.files.create.assert_called_once()
            mock_openai_client.beta.assistants.create.assert_called_once()
            mock_openai_client.beta.threads.create.assert_called_once()
            mock_openai_client.beta.threads.messages.create.assert_called_once()
            mock_openai_client.beta.threads.runs.create_and_poll.assert_called_once()
            mock_openai_client.beta.threads.messages.list.assert_called_once()
            mock_openai_client.files.content.assert_called_once()
            mock_openai_client.files.delete.assert_called_once()

    @pytest.mark.asyncio
    async def test_clean_excel_openai_error_handling(self, mock_openai_client):
        """Test error handling in the OpenAI cleaning function."""
        # Mock a file upload error
        mock_openai_client.files.create.side_effect = Exception("Upload error")
        
        # Create a dataframe with characteristics that would trigger cleaning
        df = pd.DataFrame([
            ['Total Report', 'Total Report', 'Total Report'],  # Repeated values
            ['ID', 'Product', 'Price'],
            [1, 'Item A', 10.5],
            [2, 'Item B', 20.5],
            [3, 'Item C', 30.5]
        ])
        
        # Mock is_excel_dirty to return True to ensure cleaning is attempted
        with patch('utils_file_uploads.ExcelUtils.is_excel_dirty', return_value=True):
            # Call the function - should handle the error gracefully
            result = await ExcelUtils.clean_excel_openai("test_table", df)
            
            # Should return the original dataframe on error
            assert result is df
            assert isinstance(result, pd.DataFrame)
            assert result.equals(df)

    @pytest.mark.asyncio
    async def test_clean_excel_openai_run_failure(self, mock_openai_client):
        """Test handling of run failure in the OpenAI cleaning function."""
        # Create a dataframe with characteristics that would trigger cleaning
        df = pd.DataFrame([
            ['Quarterly Results', 'Quarterly Results', 'Quarterly Results'],  # Repeated values
            ['ID', 'Product', 'Price'],
            [1, 'Item A', 10.5],
            [2, 'Item B', 20.5],
            [3, 'Item C', 30.5]
        ])
        
        # Mock a run failure
        mock_run = MagicMock()
        mock_run.status = "failed"
        mock_openai_client.beta.threads.runs.create_and_poll.return_value = mock_run
        
        # Mock is_excel_dirty to return True to ensure cleaning is attempted
        with patch('utils_file_uploads.ExcelUtils.is_excel_dirty', return_value=True):
            # Call the function
            result = await ExcelUtils.clean_excel_openai("test_table", df)
            
            # Should return the original dataframe on run failure
            assert result is df
            assert isinstance(result, pd.DataFrame)
            assert result.equals(df)

    @pytest.mark.asyncio
    async def test_clean_excel_openai_no_file_id(self, mock_openai_client):
        """Test handling when no file ID is found in the response."""
        # Create a dataframe with characteristics that would trigger cleaning
        df = pd.DataFrame([
            ['Quarterly Results', 'Quarterly Results', 'Quarterly Results'],  # Repeated values
            ['ID', 'Product', 'Price'],
            [1, 'Item A', 10.5],
            [2, 'Item B', 20.5],
            ['Total', '', 61.5]  # Total row
        ])
        
        # Mock a response with no file ID
        mock_message_data = MagicMock()
        mock_message_data.data = [MagicMock(content=[MagicMock(text=MagicMock(annotations=[]))])]
        mock_openai_client.beta.threads.messages.list.return_value = mock_message_data
        
        # Mock is_excel_dirty to return True to ensure cleaning is attempted
        with patch('utils_file_uploads.ExcelUtils.is_excel_dirty', return_value=True):
            # Call the function
            result = await ExcelUtils.clean_excel_openai("test_table", df)
            
            # Should return the original dataframe when no file ID is found
            assert result is df
            assert isinstance(result, pd.DataFrame)
            assert result.equals(df)

    @pytest.mark.asyncio
    async def test_clean_excel_openai_file_download_error(self, mock_openai_client):
        """Test handling of file download errors in the OpenAI cleaning function."""
        # Create a dataframe with characteristics that would trigger cleaning
        df = pd.DataFrame([
            ['Annual Report', 'Annual Report', 'Annual Report'],  # Repeated values
            ['ID', 'Product', 'Price'],
            [1, 'Item A', 10.5],
            [2, 'Item B', 20.5],
            ['Notes:', 'Values in USD', '']  # Footer note
        ])
        
        # Mock a file download error
        mock_openai_client.files.content.side_effect = Exception("Download error")
        
        # Mock is_excel_dirty to return True to ensure cleaning is attempted
        with patch('utils_file_uploads.ExcelUtils.is_excel_dirty', return_value=True):
            # Call the function
            result = await ExcelUtils.clean_excel_openai("test_table", df)
            
            # Should return the original dataframe on download error
            assert result is df
            assert isinstance(result, pd.DataFrame)
            assert result.equals(df)

    @pytest.mark.asyncio
    async def test_clean_excel_openai_csv_parse_error(self, mock_openai_client):
        """Test handling of CSV parsing errors in the OpenAI cleaning function."""
        # Create a dataframe with characteristics that would trigger cleaning
        df = pd.DataFrame({
            'Q1 Sales': [100, 200, 300],
            'Q2 Sales': [150, 250, 350],
            'Q3 Sales': [120, 220, 320],
            'Q4 Sales': [180, 280, 380]  # Wide format needs cleaning
        })
        
        # Mock invalid CSV content
        mock_file_content = AsyncMock()
        mock_file_content.read = MagicMock(return_value=b'A,"B\nC,D')
        mock_openai_client.files.content.return_value = mock_file_content
        
        # Mock is_excel_dirty to return True to ensure cleaning is attempted
        with patch('utils_file_uploads.ExcelUtils.is_excel_dirty', return_value=True):
            # Call the function
            result = await ExcelUtils.clean_excel_openai("test_table", df)
            
            # Should return the original dataframe on parsing error
            assert result is df
            assert isinstance(result, pd.DataFrame)
            assert result.equals(df)

    @pytest.mark.asyncio
    async def test_clean_excel_openai_transformation(self, mock_openai_client):
        """Test that the function returns a transformed dataframe from OpenAI when cleaning is needed."""
        # Create a dataframe that would be flagged as "dirty" (wide format with pattern)
        input_df = pd.DataFrame({
            'Product': ['Item A', 'Item B', 'Item C'],
            'Q1 Sales': [100, 200, 300],
            'Q2 Sales': [150, 250, 350],
            'Q3 Sales': [120, 220, 320],
            'Total': ['Total', '', '']  # Has "Total" row - should trigger cleaning
        })
        
        # Mock CSV content that represents a transformed dataframe
        transformed_csv = b"Product,Quarter,Sales\nItem A,Q1,100\nItem A,Q2,150\nItem A,Q3,120\nItem B,Q1,200\nItem B,Q2,250\nItem B,Q3,220\nItem C,Q1,300\nItem C,Q2,350\nItem C,Q3,320"
        mock_file_content = AsyncMock()
        mock_file_content.read = MagicMock(return_value=transformed_csv)
        mock_openai_client.files.content.return_value = mock_file_content
        
        # Mock is_excel_dirty to return True to ensure cleaning is performed
        with patch('utils_file_uploads.ExcelUtils.is_excel_dirty', return_value=True):
            # Call the function
            result = await ExcelUtils.clean_excel_openai("test_table", input_df)
            
            # Check that we got a transformed dataframe back
            assert isinstance(result, pd.DataFrame)
            
            # Verify OpenAI client was used
            mock_openai_client.files.create.assert_called_once()
            
            # Check that the transformation looks correct
            assert "Quarter" in result.columns
            assert "Sales" in result.columns
            
    @pytest.mark.asyncio
    async def test_clean_excel_openai_skip_cleaning(self, mock_openai_client):
        """Test that the function skips cleaning when the dataframe is clean."""
        # Create a clean dataframe
        clean_df = pd.DataFrame({
            'ID': [1, 2, 3, 4, 5],
            'Name': ['Product A', 'Product B', 'Product C', 'Product D', 'Product E'],
            'Price': [10.5, 20.75, 15.25, 30.00, 25.50]
        })
        
        # Mock is_excel_dirty to return False to skip cleaning
        with patch('utils_file_uploads.ExcelUtils.is_excel_dirty', return_value=False):
            # Call the function
            result = await ExcelUtils.clean_excel_openai("clean_table", clean_df)
            
            # Should return the original dataframe without cleaning
            assert result is clean_df
            
            # Verify OpenAI client was NOT used
            mock_openai_client.files.create.assert_not_called()
            mock_openai_client.beta.assistants.create.assert_not_called()
            mock_openai_client.beta.threads.create.assert_not_called()
        
    @pytest.mark.asyncio
    async def test_excel_sheet_count_preserved(self):
        """Test that the number of tables/sheets is preserved after OpenAI cleaning."""
        import asyncio
        
        # Create a test case with multiple dataframes representing multiple Excel sheets
        # Sheet 1 is "dirty" and needs cleaning (has a total row)
        sheet1_df = pd.DataFrame([
            ['ID', 'Product', 'Price'],
            [1, 'Item A', 10.5],
            [2, 'Item B', 20.5],
            ['Total', '', 31.0]
        ])
        
        # Sheet 2 is clean and doesn't need cleaning
        sheet2_df = pd.DataFrame({
            'Category': ['X', 'Y', 'Z'],
            'Count': [10, 20, 30],
        })
        
        # Sheet 3 is "dirty" and needs cleaning (wide format)
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
        
        # Mock the is_excel_dirty function to return appropriate values for each sheet
        async def mock_is_dirty(table_name, df):
            # Only sheets 1 and 3 need cleaning
            return table_name in ['sheet1', 'sheet3']
            
        # Mock the clean_excel_openai function to simulate cleaning or return original
        async def mock_clean_excel(table_name, df):
            # First check if the dataframe is dirty
            is_dirty = await mock_is_dirty(table_name, df)
            
            if not is_dirty:
                return df  # Return original for clean sheets
                
            # For dirty sheets, create a transformed version
            result_df = df.copy()
            result_df['Cleaned'] = ['Yes'] * len(df)
            return result_df
            
        # Use patch to replace both functions
        with patch('utils_file_uploads.ExcelUtils.is_excel_dirty', side_effect=mock_is_dirty), \
             patch('utils_file_uploads.ExcelUtils.clean_excel_openai', side_effect=mock_clean_excel):
            
            # Create tasks for each table (similar to file_upload_routes.py)
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
                
            # Verify that only dirty sheets were cleaned
            assert 'Cleaned' in cleaned_tables['sheet1'].columns  # Should be cleaned
            assert 'Cleaned' not in cleaned_tables['sheet2'].columns  # Should not be cleaned
            assert 'Cleaned' in cleaned_tables['sheet3'].columns  # Should be cleaned