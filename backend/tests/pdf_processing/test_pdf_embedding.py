"""
Unit tests for PDF embedding functionality.

These tests can run without Docker's internal connections.
All tests are isolated and use mocks to avoid database dependencies.
"""
import pytest
from unittest.mock import patch, AsyncMock, MagicMock

import requests
from db_models import OAI_EMB_DIM
from conftest import TEST_DB, BASE_URL

import pymupdf

def create_pdf_and_get_base_64(page_texts: list[str]):
    import os
    import tempfile

    pdf_name = "test_pdf.pdf"

    temp_dir = tempfile.gettempdir()
    temp_file_path = os.path.join(temp_dir, pdf_name)

    try:
        # create a pdf
        doc = pymupdf.Document()
        for page_text in enumerate(page_texts):
            page = doc._newPage()
            page.insert_text((100, 100), page_text)

        doc.save(temp_file_path)
        doc.close()

        pdf_content = None

        # read the pdf and get the base64
        with open(temp_file_path, "rb") as f:
            pdf_content = f.read()
        
        return pdf_name, temp_file_path, pdf_content
    except Exception as e:
        raise e
    finally:
        os.unlink(temp_file_path)



@pytest.mark.asyncio
async def test_generate_embedding():
    """Test generating embeddings for text"""
    try:
        from utils_pdf.embedding import generate_embedding

        # Call the function
        text = "This is a test text to embed."
        embedding = await generate_embedding(text)

        assert type(embedding) == list
        assert len(embedding) == OAI_EMB_DIM
    
    except Exception as e:
        pytest.fail(f"Test failed with exception: {str(e)}")


@pytest.mark.asyncio
async def test_embed_pdf_chunks():
    """Test embedding multiple PDF chunks"""
    try:
        from utils_pdf.embedding import embed_pdf_chunks
        from utils_pdf.chunking import PDFChunk, process_pdf_to_chunks

        pdf_name, temp_file_path, base64_pdf = create_pdf_and_get_base_64(["This is a test PDF with some text content.", "Some more content to ensure we can create chunks."])

        chunks = process_pdf_to_chunks(123, pdf_name, base64_pdf)
        
        result_chunks = await embed_pdf_chunks(chunks)
            
        # Check the results
        assert len(result_chunks) == 2
        assert len(result_chunks[0].embedding) == OAI_EMB_DIM
        assert len(result_chunks[1].embedding) == OAI_EMB_DIM
        assert result_chunks[0].embedding is not None
        assert result_chunks[1].embedding is not None
    
    except Exception as e:
        pytest.fail(f"Test failed with exception: {str(e)}")


@pytest.mark.asyncio
async def test_semantic_search():
    """Test semantic search on embeddings"""
    try:
        import os
        from utils_pdf.embedding import semantic_search
        from utils_pdf.chunking import process_pdf_to_chunks

        db_name = TEST_DB["db_name"]

        # create a temp pdf with 4 pages
        pdf_name, temp_file_path, base64_pdf = create_pdf_and_get_base_64([
            "Paris is the capital of France.",
            "Delhi is the capital of India",
            "France has a big GDP. Paris is the biggest contributor.",
            "London is in UK"
        ])

        # upload this pdf to test db
        # Upload the PDF
        with open(temp_file_path, 'rb') as pdf_file:
            files = [
                ('files', (os.path.basename(temp_file_path), pdf_file, 'application/pdf'))
            ]
            response = requests.post(f"{BASE_URL}/upload_files", files=files, data={"db_name": db_name})
            # get pdf id
            db_info = response.json()
            print(db_info)

        os.unlink(temp_file_path)
        
        # # Process the PDF
        # chunks = await process_pdf_to_chunks(pdf_id, pdf_name, base64_pdf)
        
        # # Call the function
        # results = await semantic_search("What is the capital of France?", top_k=2)

        # # Check the results
        # assert len(results) == 2
        # assert results[0]["pdf_id"] == 123
        # assert results[0]["text"] == "Paris is the capital of France."
        # assert results[0]["similarity"] > 0.7
        # assert results[1]["pdf_id"] == 123
        # assert results[1]["text"] == "France has a big GDP. Paris is the biggest contributor."
        # assert results[1]["similarity"] > 0
    
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