"""
Unit tests for PDF embedding functionality.
"""

import os
import pytest

from db_models import OAI_EMB_DIM
from conftest import create_pdf_and_get_base_64

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

    pdf_name, temp_file_path, base64_pdf = create_pdf_and_get_base_64(["This is a test PDF with some text content.", "Some more content to ensure we can create chunks."])

    try:
        from utils_pdf.embedding import embed_pdf_chunks
        from utils_pdf.chunking import process_pdf_to_chunks

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
    finally:
        os.unlink(temp_file_path)