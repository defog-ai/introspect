"""
Unit tests for PDF embedding functionality.

These tests can run without Docker's internal connections.
All tests are isolated and use mocks to avoid database dependencies.
"""
import pytest
from unittest.mock import patch, AsyncMock, MagicMock


@pytest.mark.asyncio
async def test_generate_embedding():
    """Test generating embeddings for text"""
    try:
        from utils_pdf.embedding import generate_embedding
        
        # Mock the OpenAI API client
        with patch('openai.AsyncOpenAI') as mock_openai:
            # Create a mock response
            mock_client = AsyncMock()
            mock_response = MagicMock()
            mock_response.data = [MagicMock(embedding=[0.1, 0.2, 0.3, 0.4])]
            mock_client.embeddings.create.return_value = mock_response
            mock_openai.return_value = mock_client
            
            # Call the function
            text = "This is a test text to embed."
            embedding = await generate_embedding(text)
            
            # Check the results
            assert embedding == [0.1, 0.2, 0.3, 0.4]
            
            # Verify the API was called with the correct parameters
            mock_client.embeddings.create.assert_called_once()
            call_kwargs = mock_client.embeddings.create.call_args.kwargs
            assert call_kwargs["model"] == "text-embedding-3-small"
            assert call_kwargs["input"] == text
    
    except Exception as e:
        pytest.fail(f"Test failed with exception: {str(e)}")


@pytest.mark.asyncio
async def test_embed_pdf_chunks():
    """Test embedding multiple PDF chunks"""
    try:
        from utils_pdf.embedding import embed_pdf_chunks
        from utils_pdf.chunking import PDFChunk
        
        # Create test chunks
        chunks = [
            PDFChunk("First chunk text", 123, "test.pdf", 1, 0),
            PDFChunk("Second chunk text", 123, "test.pdf", 1, 1)
        ]
        
        # Mock the generate_embedding function
        with patch('utils_pdf.embedding.generate_embedding') as mock_generate_embedding:
            # Set up mock embeddings
            mock_generate_embedding.side_effect = [
                [0.1, 0.2, 0.3],  # First chunk embedding
                [0.4, 0.5, 0.6]   # Second chunk embedding
            ]
            
            # Call the function
            result_chunks = await embed_pdf_chunks(chunks)
            
            # Check the results
            assert len(result_chunks) == 2
            assert result_chunks[0].embedding == [0.1, 0.2, 0.3]
            assert result_chunks[1].embedding == [0.4, 0.5, 0.6]
            
            # Verify generate_embedding was called twice with correct texts
            assert mock_generate_embedding.call_count == 2
            mock_generate_embedding.assert_any_call("First chunk text")
            mock_generate_embedding.assert_any_call("Second chunk text")
    
    except Exception as e:
        pytest.fail(f"Test failed with exception: {str(e)}")


@pytest.mark.asyncio
async def test_semantic_search():
    """Test semantic search on embeddings"""
    try:
        from utils_pdf.embedding import semantic_search
        
        # Mock the database session and execution
        with patch('utils_pdf.embedding.AsyncSession') as mock_async_session:
            # Set up mock session
            mock_session = AsyncMock()
            mock_session.__aenter__.return_value = mock_session
            mock_async_session.return_value = mock_session
            
            # Mock the query result
            mock_result = AsyncMock()
            mock_matches = [
                (MagicMock(pdf_id=123, pdf_name="test.pdf", page_number=1, text_chunk="Relevant chunk 1"), 0.95),
                (MagicMock(pdf_id=123, pdf_name="test.pdf", page_number=2, text_chunk="Relevant chunk 2"), 0.85)
            ]
            mock_result.all.return_value = mock_matches
            mock_session.execute.return_value = mock_result
            
            # Mock generate_embedding
            with patch('utils_pdf.embedding.generate_embedding') as mock_generate_embedding:
                mock_generate_embedding.return_value = [0.1, 0.2, 0.3]
                
                # Call the function
                results = await semantic_search("test query", top_k=2)
                
                # Check the results
                assert len(results) == 2
                assert results[0]["pdf_id"] == 123
                assert results[0]["text"] == "Relevant chunk 1"
                assert results[0]["similarity"] == 0.95
                assert results[1]["pdf_id"] == 123
                assert results[1]["text"] == "Relevant chunk 2"
                assert results[1]["similarity"] == 0.85
                
                # Verify query embedding was generated
                mock_generate_embedding.assert_called_once_with("test query")
    
    except Exception as e:
        pytest.fail(f"Test failed with exception: {str(e)}")


def test_generate_embedding_sync():
    """Test the synchronous version of embedding generation used by Celery"""
    try:
        from celery_tasks.pdf_tasks import generate_embedding_sync
        
        # Mock the OpenAI client
        with patch('openai.OpenAI') as mock_openai:
            # Create mock response
            mock_client = MagicMock()
            mock_response = MagicMock()
            mock_response.data = [MagicMock(embedding=[0.1, 0.2, 0.3])]
            mock_client.embeddings.create.return_value = mock_response
            mock_openai.return_value = mock_client
            
            # Call the function
            text = "Test text for sync embedding"
            embedding = generate_embedding_sync(text)
            
            # Check the result
            assert embedding == [0.1, 0.2, 0.3]
            
            # Verify OpenAI was called correctly
            mock_client.embeddings.create.assert_called_once()
            call_kwargs = mock_client.embeddings.create.call_args.kwargs
            assert call_kwargs["model"] == "text-embedding-3-small"
            assert call_kwargs["input"] == text
    
    except Exception as e:
        pytest.fail(f"Test failed with exception: {str(e)}")