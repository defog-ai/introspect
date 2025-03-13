"""
Tests for PDF embedding functionality
"""

import os
import pytest
from unittest.mock import patch, AsyncMock, MagicMock

from utils_pdf.embedding import (
    generate_embedding,
    process_pdf_for_embedding,
    semantic_search
)


@pytest.mark.asyncio
@patch('utils_pdf.embedding.AsyncOpenAI')
async def test_generate_embedding(mock_openai):
    """Test generating embeddings with OpenAI API"""
    # Mock the OpenAI client
    mock_client = AsyncMock()
    mock_openai.return_value = mock_client
    
    # Mock the embedding response
    mock_embedding = [0.1, 0.2, 0.3, 0.4, 0.5]
    mock_embedding_data = AsyncMock()
    mock_embedding_data.data = [MagicMock(embedding=mock_embedding)]
    mock_client.embeddings.create.return_value = mock_embedding_data
    
    # Call the function
    result = await generate_embedding("Test text")
    
    # Verify results
    assert result == mock_embedding
    mock_client.embeddings.create.assert_called_once()
    assert mock_client.embeddings.create.call_args[1]["input"] == "Test text"
    assert mock_client.embeddings.create.call_args[1]["model"] == "text-embedding-3-small"


@pytest.mark.asyncio
@patch('utils_pdf.embedding.process_pdf_to_chunks')
@patch('utils_pdf.embedding.generate_embedding')
@patch('utils_pdf.embedding.AsyncSession')
async def test_process_pdf_for_embedding(mock_session, mock_generate_embedding, mock_process_pdf_to_chunks):
    """Test processing a PDF for embedding"""
    # Mock session and query results
    session_instance = AsyncMock()
    mock_session.return_value.__aenter__.return_value = session_instance
    
    # First query returns None (PDF not processed yet)
    mock_execute = AsyncMock()
    mock_execute.scalar_one_or_none.return_value = None
    session_instance.execute.return_value = mock_execute
    
    # Mock PDF chunks
    mock_chunks = [
        {
            "pdf_id": 123,
            "text_chunk": "Sample text 1",
            "page_number": 1,
            "chunk_index": 0
        },
        {
            "pdf_id": 123,
            "text_chunk": "Sample text 2",
            "page_number": 1,
            "chunk_index": 1
        }
    ]
    mock_process_pdf_to_chunks.return_value = mock_chunks
    
    # Mock embeddings
    mock_generate_embedding.return_value = [0.1, 0.2, 0.3, 0.4, 0.5]
    
    # Call the function
    result = await process_pdf_for_embedding(
        pdf_id=123,
        pdf_name="test.pdf",
        base64_pdf="base64_content"
    )
    
    # Verify results
    assert result is True
    mock_process_pdf_to_chunks.assert_called_once_with(
        123, "test.pdf", "base64_content"
    )
    assert mock_generate_embedding.call_count == 2
    assert session_instance.add.call_count == 2


@pytest.mark.asyncio
@patch('utils_pdf.embedding.generate_embedding')
@patch('utils_pdf.embedding.AsyncSession')
async def test_semantic_search(mock_session, mock_generate_embedding):
    """Test semantic search functionality"""
    # Mock embedding generation
    mock_generate_embedding.return_value = [0.1, 0.2, 0.3, 0.4, 0.5]
    
    # Mock session and query results
    session_instance = AsyncMock()
    mock_session.return_value.__aenter__.return_value = session_instance
    
    # Mock search results (PDFEmbeddings objects with similarity scores)
    mock_chunk1 = MagicMock(
        pdf_id=123,
        page_number=1,
        text_chunk="Sample text 1"
    )
    mock_chunk2 = MagicMock(
        pdf_id=456,
        page_number=2,
        text_chunk="Sample text 2"
    )
    
    # Mock execute results (returns rows with chunk object and similarity score)
    mock_execute = AsyncMock()
    mock_execute.all.return_value = [
        (mock_chunk1, 0.9),
        (mock_chunk2, 0.7)
    ]
    session_instance.execute.return_value = mock_execute
    
    # Mock PDF name lookup
    pdf_name_execute = AsyncMock()
    pdf_name_execute.scalar_one_or_none.side_effect = ["PDF 1", "PDF 2"]
    session_instance.execute.side_effect = [mock_execute, pdf_name_execute, pdf_name_execute]
    
    # Call the function
    results = await semantic_search(
        query="test query",
        top_k=2,
        pdf_ids=[123, 456]
    )
    
    # Check structure of results
    assert len(results) == 2
    
    # Check content of results
    assert results[0]["pdf_id"] == 123
    assert results[0]["pdf_name"] == "PDF 1"
    assert results[0]["text"] == "Sample text 1"
    assert isinstance(results[0]["similarity"], float)
    
    assert results[1]["pdf_id"] == 456
    assert results[1]["pdf_name"] == "PDF 2"
    assert results[1]["text"] == "Sample text 2"
    assert isinstance(results[1]["similarity"], float)