"""
Tests for PDF API functionality
"""

import pytest
from unittest.mock import patch, AsyncMock, MagicMock

from utils_pdf.api import (
    get_relevant_pdf_data,
    extract_data_from_chunks,
    PDFDataResponse
)


@pytest.mark.asyncio
@patch('utils_pdf.api.extract_data_from_chunks')
@patch('utils_pdf.api.semantic_search')
@patch('utils_pdf.api.get_project_pdf_files')
@patch('utils_pdf.api.AsyncSession')
async def test_get_relevant_pdf_data(mock_session, mock_get_pdf_files, mock_semantic_search, mock_extract_data):
    """Test retrieving relevant PDF data for an analysis"""
    # Mock session and analysis data
    session_instance = AsyncMock()
    mock_session.return_value.__aenter__.return_value = session_instance
    
    # Mock analysis query result
    mock_analysis = MagicMock(
        db_name="test_db",
        user_question="What is the revenue?",
        data={
            "output": "CSV content here with revenue data"
        }
    )
    mock_execute = AsyncMock()
    mock_execute.scalar_one_or_none.return_value = mock_analysis
    session_instance.execute.return_value = mock_execute
    
    # Mock PDF file IDs
    mock_get_pdf_files.return_value = [123, 456]
    
    # Mock semantic search results
    mock_semantic_search.return_value = [
        {
            "pdf_id": 123,
            "pdf_name": "Financial Report 2023.pdf",
            "page_number": 5,
            "text": "The revenue was $1.2M in 2023.",
            "similarity": 0.92
        },
        {
            "pdf_id": 456,
            "pdf_name": "Q4 Analysis.pdf",
            "page_number": 2,
            "text": "Q4 revenue increased by 15%.",
            "similarity": 0.85
        }
    ]
    
    # Mock extracted data
    mock_extract_data.return_value = "## Revenue Analysis\n\nBased on the PDF documents, the revenue was $1.2M in 2023 with a 15% increase in Q4."
    
    # Call the function
    result = await get_relevant_pdf_data(analysis_id="analysis123")
    
    # Verify results
    assert isinstance(result, PDFDataResponse)
    assert "Revenue Analysis" in result.content
    assert len(result.source_pdfs) == 2
    assert result.source_pdfs[0]["pdf_id"] == 123
    assert result.source_pdfs[0]["pdf_name"] == "Financial Report 2023.pdf"
    assert result.source_pdfs[1]["pdf_id"] == 456
    assert result.source_pdfs[1]["pdf_name"] == "Q4 Analysis.pdf"
    
    # Verify mock calls
    mock_get_pdf_files.assert_called_once_with("test_db")
    mock_semantic_search.assert_called_once()
    mock_extract_data.assert_called_once()


@pytest.mark.asyncio
@patch('utils_pdf.api.AsyncAnthropic')
async def test_extract_data_from_chunks(mock_anthropic):
    """Test extracting structured data from PDF chunks using an LLM"""
    # Mock Anthropic client
    mock_client = AsyncMock()
    mock_anthropic.return_value = mock_client
    
    # Mock Anthropic message response
    mock_message = MagicMock()
    mock_message.content = [MagicMock(text="## Revenue Analysis\n\nThe revenue was $1.2M in 2023.")]
    mock_client.messages.create.return_value = mock_message
    
    # Sample chunks for testing
    relevant_chunks = [
        {
            "pdf_id": 123,
            "pdf_name": "Financial Report 2023.pdf",
            "page_number": 5,
            "text": "The revenue was $1.2M in 2023.",
            "similarity": 0.92
        },
        {
            "pdf_id": 456,
            "pdf_name": "Q4 Analysis.pdf",
            "page_number": 2,
            "text": "Q4 revenue increased by 15%.",
            "similarity": 0.85
        }
    ]
    
    # Call the function
    result = await extract_data_from_chunks(
        user_question="What is the revenue?",
        sql_output="Revenue data from SQL",
        relevant_chunks=relevant_chunks
    )
    
    # Verify result
    assert "Revenue Analysis" in result
    assert "The revenue was $1.2M in 2023." in result
    
    # Verify Claude was called correctly
    mock_client.messages.create.assert_called_once()
    assert "What is the revenue?" in mock_client.messages.create.call_args[1]["messages"][0]["content"]
    assert "Revenue data from SQL" in mock_client.messages.create.call_args[1]["messages"][0]["content"]
    assert "Financial Report 2023.pdf" in mock_client.messages.create.call_args[1]["messages"][0]["content"]
    assert "Q4 Analysis.pdf" in mock_client.messages.create.call_args[1]["messages"][0]["content"]


@pytest.mark.asyncio
@patch('utils_pdf.api.AsyncAnthropic')
async def test_extract_data_from_chunks_no_relevant_data(mock_anthropic):
    """Test extracting data when no relevant content is found"""
    # Mock Anthropic client
    mock_client = AsyncMock()
    mock_anthropic.return_value = mock_client
    
    # Mock Anthropic message response with no relevant data
    mock_message = MagicMock()
    mock_message.content = [MagicMock(text="NO_RELEVANT_DATA_FOUND")]
    mock_client.messages.create.return_value = mock_message
    
    # Sample chunks for testing
    relevant_chunks = [
        {
            "pdf_id": 123,
            "pdf_name": "Unrelated Document.pdf",
            "page_number": 5,
            "text": "This has nothing to do with revenue.",
            "similarity": 0.4
        }
    ]
    
    # Call the function
    result = await extract_data_from_chunks(
        user_question="What is the revenue?",
        sql_output="Revenue data from SQL",
        relevant_chunks=relevant_chunks
    )
    
    # Verify result is None when no relevant data is found
    assert result is None