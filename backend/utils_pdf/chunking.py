"""
PDF chunking utilities

This module contains functions to:
1. Extract text from PDFs
2. Chunk PDFs into smaller segments for embedding
3. Clean and process PDF text
"""

import base64
import io
import logging
import re
from typing import List, Dict, Any, Optional, Tuple

# We'll use PyMuPDF for PDF text extraction
import pymupdf

LOGGER = logging.getLogger("server")

class PDFChunk:
    """Represents a chunk of text from a PDF with metadata"""
    
    def __init__(
        self,
        text: str,
        pdf_id: int,
        pdf_name: str,
        page_number: int,
        chunk_index: int,
    ):
        self.text = text
        self.pdf_id = pdf_id
        self.pdf_name = pdf_name
        self.page_number = page_number
        self.chunk_index = chunk_index
        self.embedding = None  # Will be populated later
    
    def get_metadata(self) -> Dict[str, Any]:
        """Returns metadata about this chunk"""
        return {
            "pdf_id": self.pdf_id,
            "pdf_name": self.pdf_name,
            "page_number": self.page_number,
            "chunk_index": self.chunk_index,
        }
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for storage"""
        return {
            "text": self.text,
            "pdf_id": self.pdf_id,
            "pdf_name": self.pdf_name,
            "page_number": self.page_number,
            "chunk_index": self.chunk_index,
            "embedding": self.embedding,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'PDFChunk':
        """Create from dictionary"""
        chunk = cls(
            text=data["text"],
            pdf_id=data["pdf_id"],
            pdf_name=data["pdf_name"],
            page_number=data["page_number"],
            chunk_index=data["chunk_index"],
        )
        chunk.embedding = data.get("embedding")
        return chunk


def extract_text_from_pdf(base64_pdf: str) -> List[str]:
    """
    Extract text from a base64-encoded PDF, returning a list of strings
    with one element per page.
    
    Args:
        base64_pdf: Base64-encoded PDF content
        
    Returns:
        List of strings, one per page
    """
    pdf_bytes = base64.b64decode(base64_pdf)
    pdf_file = io.BytesIO(pdf_bytes)
    
    try:
        doc = pymupdf.open(stream=pdf_file, filetype="pdf")
        pages = []
        
        for page_num in range(len(doc)):
            page = doc[page_num]
            page_text = page.get_text()
            
            # Clean the extracted text
            if page_text:
                page_text = clean_pdf_text(page_text)
                pages.append(page_text)
            else:
                pages.append("")
        
        doc.close()    
        return pages
    except Exception as e:
        LOGGER.error(f"Error extracting text from PDF: {str(e)}")
        return []


def clean_pdf_text(text: str) -> str:
    """
    Clean and normalize extracted PDF text
    
    Args:
        text: Raw text from PDF
        
    Returns:
        Cleaned text
    """
    if not text:
        return ""
    
    # Replace multiple newlines with a single one
    text = re.sub(r'\n+', '\n', text)
    
    # Replace multiple spaces with a single one
    text = re.sub(r' +', ' ', text)
    
    # Remove any form feeds or other control characters
    text = re.sub(r'\f', '', text)
    
    return text.strip()


def chunk_text(
    text: str,
    chunk_size: int = 1000,
    chunk_overlap: int = 200
) -> List[str]:
    """
    Split text into chunks of approximately chunk_size characters with overlap
    
    Args:
        text: Text to split
        chunk_size: Target size of each chunk in characters
        chunk_overlap: Number of characters to overlap between chunks
        
    Returns:
        List of text chunks
    """
    if not text:
        return []
    
    chunks = []
    start = 0
    text_length = len(text)

    LOGGER.info(f"Chunking text with length:: {text_length}")
    
    while start < text_length:
        # Find the end of this chunk
        end = min(start + chunk_size, text_length)

        # If we're not at the end of the text, try to find a good breaking point
        if end < text_length:
            # Look for paragraph or sentence breaks near the target end
            paragraph_break = text.rfind('\n\n', start, end)
            if paragraph_break != -1 and paragraph_break > start + chunk_size // 2:
                end = paragraph_break + 2
            else:
                # Try to find a sentence break
                sentence_breaks = [
                    text.rfind('. ', start, end),
                    text.rfind('? ', start, end),
                    text.rfind('! ', start, end),
                    text.rfind('\n', start, end)
                ]
                
                best_break = max(sentence_breaks)
                if best_break != -1 and best_break > start + chunk_size // 2:
                    end = best_break + 2
        
        # Get the chunk
        chunk = text[start:end].strip()
        if chunk:
            chunks.append(chunk)
        
        # Move to next chunk with overlap
        # if end is at text length
        # or if text_length < chunk_overlap
        # juts move to end instead of end - chunk_overlap
        start = max(start, end if (end - chunk_overlap) < 0 or end == text_length else (end - chunk_overlap))
    
    return chunks


def process_pdf_to_chunks(
    pdf_id: int,
    pdf_name: str,
    base64_pdf: str,
    chunk_size: int = 1000,
    chunk_overlap: int = 200
) -> List[Dict[str, Any]]:
    """
    Process a PDF into chunks ready for embedding
    
    Args:
        pdf_id: Database ID of the PDF
        pdf_name: Name of the PDF file
        base64_pdf: Base64-encoded PDF content
        chunk_size: Target size of each chunk in characters
        chunk_overlap: Number of characters to overlap between chunks
        
    Returns:
        List of dictionaries with chunk text and metadata
    """
    pdf_pages = extract_text_from_pdf(base64_pdf)
    chunks = []
    
    for page_number, page_text in enumerate(pdf_pages):
        page_chunks = chunk_text(page_text, chunk_size, chunk_overlap)

        LOGGER.info(f"Generated {len(page_chunks)} chunks for page {page_number + 1}")
        
        for i, text_chunk in enumerate(page_chunks):
            chunk = {
                "pdf_id": pdf_id,
                "text_chunk": text_chunk,
                "pdf_name": pdf_name,
                "page_number": page_number + 1,  # 1-indexed for human readability
                "chunk_index": i
            }
            chunks.append(chunk)
    
    return chunks