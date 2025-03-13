"""
Tests for PDF chunking functionality
"""

import base64
import os
import pytest
import tempfile

from utils_pdf.chunking import (
    clean_pdf_text,
    chunk_text,
    extract_text_from_pdf,
    process_pdf_to_chunks
)

# Sample text for chunking tests
SAMPLE_TEXT = """
This is the first paragraph with some content.
It has multiple sentences for testing purposes.

This is the second paragraph.
It also has multiple sentences to test.

Third paragraph comes here.
More sentences for testing chunking.

Fourth paragraph will add even more content.
This should be enough to create multiple chunks.

Here is the fifth paragraph with some more text.
Let's make sure we have enough content for testing the chunker.
"""


def test_clean_pdf_text():
    """Test cleaning of PDF text"""
    # Test with normal text
    text = "This is \n\n some text  with   extra spaces \f and form feeds"
    cleaned = clean_pdf_text(text)
    assert cleaned == "This is \n some text with extra spaces and form feeds"
    
    # Test with empty text
    assert clean_pdf_text("") == ""
    assert clean_pdf_text(None) == ""


def test_chunk_text():
    """Test chunking of text"""
    # Test with small chunk size to ensure multiple chunks
    chunks = chunk_text(SAMPLE_TEXT, chunk_size=100, chunk_overlap=20)
    
    # Verify we got multiple chunks
    assert len(chunks) > 1
    
    # Verify each chunk is within the specified size
    for chunk in chunks:
        assert len(chunk) <= 100
        
    # Test with empty text
    assert chunk_text("") == []
    assert chunk_text(None) == []
    
    # Test with chunk size larger than text
    big_chunks = chunk_text(SAMPLE_TEXT, chunk_size=10000)
    assert len(big_chunks) == 1
    assert big_chunks[0] == SAMPLE_TEXT.strip()


def create_simple_pdf():
    """Create a simple PDF file for testing"""
    try:
        import fitz  # PyMuPDF
        
        # Create a temp PDF file
        handle, pdf_path = tempfile.mkstemp(suffix=".pdf")
        os.close(handle)
        
        # Create a simple PDF
        doc = fitz.new_document()
        page = doc.new_page()
        
        # Add some text to the page
        text_rect = fitz.Rect(50, 50, 500, 800)
        page.insert_text(text_rect.tl, SAMPLE_TEXT)
        
        # Save the PDF
        doc.save(pdf_path)
        doc.close()
        
        # Read the PDF as base64
        with open(pdf_path, "rb") as f:
            pdf_bytes = f.read()
        
        base64_pdf = base64.b64encode(pdf_bytes).decode("utf-8")
        
        return base64_pdf, pdf_path
    except ImportError:
        pytest.skip("PyMuPDF not installed")


@pytest.mark.asyncio
async def test_extract_text_from_pdf():
    """Test extraction of text from PDF"""
    try:
        base64_pdf, pdf_path = create_simple_pdf()
        
        # Extract text from the PDF
        pages = extract_text_from_pdf(base64_pdf)
        
        # There should be at least one page
        assert len(pages) >= 1
        
        # The text should contain parts of the sample text
        # Note: PDF text extraction might not preserve exact formatting
        assert any(sample_part in pages[0] for sample_part in ["paragraph", "sentences", "testing"])
        
        # Clean up
        os.unlink(pdf_path)
    except (ImportError, ModuleNotFoundError):
        pytest.skip("PyMuPDF not installed")


@pytest.mark.asyncio
async def test_process_pdf_to_chunks():
    """Test processing a PDF into chunks"""
    try:
        base64_pdf, pdf_path = create_simple_pdf()
        
        # Process the PDF into chunks
        chunks = process_pdf_to_chunks(
            pdf_id=123,
            pdf_name="test.pdf",
            base64_pdf=base64_pdf
        )
        
        # There should be at least one chunk
        assert len(chunks) >= 1
        
        # Check structure of chunks
        for chunk in chunks:
            assert "pdf_id" in chunk
            assert "text_chunk" in chunk
            assert "page_number" in chunk
            assert "chunk_index" in chunk
            
            assert chunk["pdf_id"] == 123
            assert isinstance(chunk["text_chunk"], str)
            assert len(chunk["text_chunk"]) > 0
        
        # Clean up
        os.unlink(pdf_path)
    except (ImportError, ModuleNotFoundError):
        pytest.skip("PyMuPDF not installed")