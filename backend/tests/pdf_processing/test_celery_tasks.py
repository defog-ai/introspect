"""
Unit tests for Celery PDF processing tasks.

These tests focus on the Celery tasks that process PDFs in the background.
"""
import pytest
from unittest.mock import patch, MagicMock


def test_pdf_processing_task():
    """Test the core PDF processing Celery task"""
    try:
        from celery_tasks.pdf_tasks import process_pdf
        from db_models import PDFProcessingStatus
        
        # Create a mock task instance
        mock_task = MagicMock()
        mock_task.request.id = "test-task-id"
        
        # Mock the SQLAlchemy Session
        with patch('sqlalchemy.orm.Session') as mock_session_class:
            # Setup session context manager
            mock_session = MagicMock()
            mock_session_class.return_value.__enter__.return_value = mock_session
            
            # Mock process_pdf_to_chunks
            with patch('celery_tasks.pdf_tasks.process_pdf_to_chunks') as mock_process_chunks:
                # Setup mock chunks
                mock_chunks = [
                    {"pdf_id": 123, "pdf_name": "test.pdf", "text_chunk": "Chunk 1", "page_number": 1, "chunk_index": 0},
                    {"pdf_id": 123, "pdf_name": "test.pdf", "text_chunk": "Chunk 2", "page_number": 1, "chunk_index": 1}
                ]
                mock_process_chunks.return_value = mock_chunks
                
                # Mock generate_embedding_sync
                with patch('celery_tasks.pdf_tasks.generate_embedding_sync') as mock_embedding:
                    mock_embedding.return_value = [0.1, 0.2, 0.3]
                    
                    # Call the task
                    pdf_id = 123
                    pdf_name = "test.pdf"
                    base64_pdf = "base64_encoded_content"
                    result = process_pdf(mock_task, pdf_id, pdf_name, base64_pdf)
                    
                    # Verify the task processes the PDF correctly
                    assert result["success"] is True
                    assert result["pdf_id"] == pdf_id
                    assert result["pdf_name"] == pdf_name
                    assert result["chunks_processed"] == 2
                    
                    # Verify process_pdf_to_chunks was called
                    mock_process_chunks.assert_called_once_with(pdf_id, pdf_name, base64_pdf)
                    
                    # Verify generate_embedding_sync was called for each chunk
                    assert mock_embedding.call_count == 2
                    mock_embedding.assert_any_call("Chunk 1")
                    mock_embedding.assert_any_call("Chunk 2")
                    
                    # Verify PDFEmbeddings were added to the session
                    assert mock_session.add.call_count == 2
                    
                    # Verify task status was updated to COMPLETED
                    update_calls = [call for call in mock_session.execute.call_args_list 
                                   if "status" in str(call) and "COMPLETED" in str(call)]
                    assert len(update_calls) > 0
    
    except Exception as e:
        pytest.fail(f"Test failed with exception: {str(e)}")


def test_pdf_processing_task_failure():
    """Test error handling in the PDF processing task"""
    try:
        from celery_tasks.pdf_tasks import process_pdf, PDFProcessingTask
        from db_models import PDFProcessingStatus
        
        # Create a mock task
        mock_task = MagicMock(spec=PDFProcessingTask)
        mock_task.request.id = "test-task-id"
        
        # Test the on_failure method
        with patch('sqlalchemy.orm.Session') as mock_session_class:
            # Setup session mock
            mock_session = MagicMock()
            mock_session_class.return_value.__enter__.return_value = mock_session
            
            # Create an exception
            test_exception = Exception("Test error during processing")
            
            # Call on_failure
            mock_task.on_failure(
                exc=test_exception,
                task_id="test-task-id",
                args=[123, "test.pdf", "base64_content"],
                kwargs={},
                einfo=None
            )
            
            # Verify that the task status was updated to FAILED
            update_calls = [call for call in mock_session.execute.call_args_list 
                           if "status" in str(call) and "FAILED" in str(call)]
            assert len(update_calls) > 0
            
            # Test with process_pdf_to_chunks raising an exception
            with patch('celery_tasks.pdf_tasks.process_pdf_to_chunks') as mock_process_chunks:
                mock_process_chunks.side_effect = Exception("Chunking failed")
                
                # Need to reset session mock for this test
                mock_session.reset_mock()
                
                # Call the function and expect it to raise the exception
                with pytest.raises(Exception):
                    process_pdf(mock_task, 123, "test.pdf", "base64_content")
                
                # Verify the status was not explicitly set to COMPLETED
                # (The on_failure handler would set it to FAILED)
                completed_calls = [call for call in mock_session.execute.call_args_list 
                                  if "status" in str(call) and "COMPLETED" in str(call)]
                assert len(completed_calls) == 0
    
    except Exception as e:
        pytest.fail(f"Test failed with exception: {str(e)}")