"""
Unit tests for PDF processing status tracking.

These tests focus on the status tracking functionality for PDF processing.
"""
import pytest
from unittest.mock import patch, AsyncMock, MagicMock


@pytest.mark.asyncio
async def test_create_task_record():
    """Test creating a task record in the database"""
    try:
        from utils_pdf.task_status import create_task_record
        from db_models import PDFProcessingTask, PDFProcessingStatus
        
        # Mock async session
        with patch('utils_pdf.task_status.AsyncSession') as mock_async_session:
            # Set up session mock
            mock_session = AsyncMock()
            mock_session.__aenter__.return_value = mock_session
            mock_session.__aexit__.return_value = None
            mock_session.begin.return_value.__aenter__.return_value = None
            mock_session.begin.return_value.__aexit__.return_value = None
            mock_async_session.return_value = mock_session
            
            # Call the function
            task_id = "test-task-id"
            pdf_id = 123
            pdf_name = "test.pdf"
            await create_task_record(task_id, pdf_id, pdf_name)
            
            # Verify session operations
            mock_session.add.assert_called_once()
            
            # Check the task record was created with correct values
            task_record = mock_session.add.call_args[0][0]
            assert isinstance(task_record, PDFProcessingTask)
            assert task_record.task_id == task_id
            assert task_record.pdf_id == pdf_id
            assert task_record.pdf_name == pdf_name
            assert task_record.status == PDFProcessingStatus.PENDING
    
    except Exception as e:
        pytest.fail(f"Test failed with exception: {str(e)}")


@pytest.mark.asyncio
async def test_get_pdf_processing_status():
    """Test retrieving PDF processing status"""
    try:
        from utils_pdf.task_status import get_pdf_processing_status
        from db_models import PDFProcessingTask, PDFProcessingStatus
        
        # Mock database query
        with patch('utils_pdf.task_status.AsyncSession') as mock_async_session:
            # Set up session mock
            mock_session = AsyncMock()
            mock_session.__aenter__.return_value = mock_session
            mock_async_session.return_value = mock_session
            
            # Create mock task
            mock_task = MagicMock()
            mock_task.task_id = "test-task-id"
            mock_task.pdf_id = 123
            mock_task.pdf_name = "test.pdf"
            mock_task.status = PDFProcessingStatus.PROCESSING
            mock_task.created_at = MagicMock()
            mock_task.created_at.isoformat.return_value = "2023-01-01T12:00:00"
            mock_task.updated_at = MagicMock()
            mock_task.updated_at.isoformat.return_value = "2023-01-01T12:05:00"
            mock_task.error_message = None
            
            # Set up query result
            mock_result = AsyncMock()
            mock_result.scalar_one_or_none.return_value = mock_task
            mock_session.execute.return_value = mock_result
            
            # Call the function
            status = await get_pdf_processing_status(pdf_id=123)
            
            # Verify result
            assert status["pdf_id"] == 123
            assert status["pdf_name"] == "test.pdf"
            assert status["task_id"] == "test-task-id"
            assert status["status"] == "PROCESSING"  # Should be the enum value
            assert status["created_at"] == "2023-01-01T12:00:00"
            assert status["updated_at"] == "2023-01-01T12:05:00"
            
            # Test with non-existent PDF
            mock_result.scalar_one_or_none.return_value = None
            status = await get_pdf_processing_status(pdf_id=999)
            
            # Verify default response
            assert status["pdf_id"] == 999
            assert status["status"] == "UNKNOWN"
            assert "No processing task found" in status["message"]
    
    except Exception as e:
        pytest.fail(f"Test failed with exception: {str(e)}")


@pytest.mark.asyncio
async def test_get_all_pdf_processing_statuses():
    """Test retrieving all PDF processing statuses"""
    try:
        from utils_pdf.task_status import get_all_pdf_processing_statuses
        from db_models import PDFFiles, PDFProcessingTask, PDFProcessingStatus
        
        # Mock database queries
        with patch('utils_pdf.task_status.AsyncSession') as mock_async_session:
            # Set up session mock
            mock_session = AsyncMock()
            mock_session.__aenter__.return_value = mock_session
            mock_async_session.return_value = mock_session
            
            # Mock PDF files query result
            mock_pdf1 = MagicMock(file_id=123, file_name="test1.pdf")
            mock_pdf2 = MagicMock(file_id=456, file_name="test2.pdf")
            mock_pdf_result = AsyncMock()
            mock_pdf_result.scalars.return_value.all.return_value = [mock_pdf1, mock_pdf2]
            
            # Mock task query results
            mock_task1 = MagicMock()
            mock_task1.task_id = "task-123"
            mock_task1.status = PDFProcessingStatus.COMPLETED
            mock_task1.created_at.isoformat.return_value = "2023-01-01T12:00:00"
            mock_task1.updated_at.isoformat.return_value = "2023-01-01T12:10:00"
            mock_task1.error_message = None
            
            mock_task_result1 = AsyncMock()
            mock_task_result1.scalar_one_or_none.return_value = mock_task1
            
            mock_task_result2 = AsyncMock()
            mock_task_result2.scalar_one_or_none.return_value = None  # No task for second PDF
            
            # Configure session.execute to return different results for different queries
            def mock_execute_side_effect(query):
                if "pdf_files" in str(query).lower():
                    return mock_pdf_result
                elif "pdf_id = 123" in str(query).lower():
                    return mock_task_result1
                elif "pdf_id = 456" in str(query).lower():
                    return mock_task_result2
            
            mock_session.execute.side_effect = mock_execute_side_effect
            
            # Call the function
            results = await get_all_pdf_processing_statuses()
            
            # Verify results
            assert len(results) == 2
            
            # First PDF has a task
            assert results[0]["pdf_id"] == 123
            assert results[0]["pdf_name"] == "test1.pdf"
            assert results[0]["task_id"] == "task-123"
            assert results[0]["status"] == "COMPLETED"
            
            # Second PDF has no task
            assert results[1]["pdf_id"] == 456
            assert results[1]["pdf_name"] == "test2.pdf"
            assert results[1]["status"] == "UNKNOWN"
            assert "No processing information" in results[1]["message"]
    
    except Exception as e:
        pytest.fail(f"Test failed with exception: {str(e)}")