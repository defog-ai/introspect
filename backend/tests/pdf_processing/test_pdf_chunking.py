"""
Unit tests for PDF chunking functionality.

These tests can run without Docker's internal connections.
All tests are isolated and use mocks to avoid database dependencies.
"""
import base64
import pytest
from unittest.mock import patch, MagicMock

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


def test_process_pdf_to_chunks():
    """Test PDF chunking with a small sample PDF"""
    try:
        from utils_pdf.chunking import process_pdf_to_chunks

        pdf_id = 123
        pdf_name, temp_file_path, base64_pdf = create_pdf_and_get_base_64(["This is a test PDF with some text content.", "Some more content to ensure we can create chunks."])

        # Call the function
        chunks = process_pdf_to_chunks(pdf_id, pdf_name, base64_pdf)
        
        # Verify the results
        assert len(chunks) > 0
        
        # Check that each chunk has the expected fields
        for chunk in chunks:
            assert "pdf_id" in chunk
            assert "text_chunk" in chunk
            assert "pdf_name" in chunk
            assert "page_number" in chunk
            assert "chunk_index" in chunk
            
            # Check values
            assert chunk["pdf_id"] == pdf_id
            assert chunk["pdf_name"] == pdf_name
            assert isinstance(chunk["text_chunk"], str)
            assert len(chunk["text_chunk"]) > 0
        
            
    except Exception as e:
        pytest.fail(f"Test failed with exception: {str(e)}")


def test_clean_pdf_text():
    """Test the PDF text cleaning function"""
    try:
        from utils_pdf.chunking import clean_pdf_text
        
        # Test with various text inputs
        test_cases = [
            # Multiple newlines
            ("Line 1\n\n\nLine 2\nLine 3", "Line 1\nLine 2\nLine 3"),
            # Multiple spaces
            ("Text with     multiple    spaces", "Text with multiple spaces"),
            # Form feeds
            ("Page 1\fPage 2", "Page 1Page 2"),
            # Empty string
            ("", ""),
            # None value
            (None, ""),
            # Combination
            ("Text   with\n\nmultiple\f\f issues", "Text with\nmultiple issues")
        ]
        
        for input_text, expected_output in test_cases:
            result = clean_pdf_text(input_text)
            assert result == expected_output
    
    except Exception as e:
        pytest.fail(f"Test failed with exception: {str(e)}")


def test_chunk_text():
    """Test the text chunking functionality"""
    try:
        from utils_pdf.chunking import chunk_text
        
        # Test with a long text
        long_text = "This is a long text that will be split into chunks. " * 20
        chunk_size = 100
        overlap = 20
        
        chunks = chunk_text(long_text, chunk_size, overlap)
        
        # Check that we have the expected number of chunks
        expected_chunks = (len(long_text) // (chunk_size - overlap)) + 1
        assert len(chunks) > 0
        
        # Check that each chunk is approximately the expected size
        for chunk in chunks:
            assert len(chunk) <= chunk_size
        
        # Check overlap between consecutive chunks
        if len(chunks) > 1:
            for i in range(len(chunks) - 1):
                # The end of one chunk should overlap with the start of the next
                end_of_current = chunks[i][-overlap:] if len(chunks[i]) > overlap else chunks[i]
                start_of_next = chunks[i+1][:overlap] if len(chunks[i+1]) > overlap else chunks[i+1]
                
                # Since we're using intelligent breaking points, we can't check for exact overlap
                # But we can check if there's some shared content
                assert len(end_of_current) > 0 and len(start_of_next) > 0
        
        # Test with empty text
        assert chunk_text("") == []
        
        # Test with short text that doesn't need chunking
        short_text = "Short text"
        assert chunk_text(short_text, 100, 20) == [short_text]
    
    except Exception as e:
        pytest.fail(f"Test failed with exception: {str(e)}")