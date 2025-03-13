"""
PDF embedding utilities

This module contains functions to:
1. Generate embeddings for PDF chunks
2. Store embeddings in the database
3. Perform semantic search on embeddings
"""

import logging
import os
import traceback
from typing import List, Dict, Any, Optional, Tuple

import numpy as np
from openai import AsyncOpenAI
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.sql import func

from db_config import engine
from db_models import PDFFiles, PDFEmbeddings
from utils_pdf.chunking import PDFChunk, process_pdf_to_chunks

LOGGER = logging.getLogger("server")


async def generate_embedding(text: str) -> List[float]:
    """
    Generate an embedding for a text string using OpenAI's API
    
    Args:
        text: Text to embed
        
    Returns:
        Embedding vector as a list of floats
    """
    try:
        client = AsyncOpenAI(api_key=os.environ.get("OPENAI_API_KEY"))
        response = await client.embeddings.create(
            model="text-embedding-3-small",
            input=text
        )
        return response.data[0].embedding
    except Exception as e:
        LOGGER.error(f"Error generating embedding: {str(e)}")
        raise


async def embed_pdf_chunks(chunks: List[PDFChunk]) -> List[PDFChunk]:
    """
    Generate embeddings for a list of PDF chunks
    
    Args:
        chunks: List of PDFChunk objects
        
    Returns:
        Same chunks with embeddings populated
    """
    try:
        for chunk in chunks:
            embedding = await generate_embedding(chunk.text)
            chunk.embedding = embedding
        return chunks
    except Exception as e:
        LOGGER.error(f"Error embedding PDF chunks: {str(e)}")
        raise


async def store_pdf_chunk_embeddings(chunks: List[PDFChunk]) -> None:
    """
    Store PDF chunk embeddings in the database
    
    Args:
        chunks: List of PDFChunk objects with embeddings
    """
    async with AsyncSession(engine) as session:
        async with session.begin():
            for chunk in chunks:
                if chunk.embedding is None:
                    LOGGER.warning(f"Chunk for PDF {chunk.pdf_id}, page {chunk.page_number} has no embedding")
                    continue
                    
                chunk_embedding = PDFEmbeddings(
                    pdf_id=chunk.pdf_id,
                    pdf_name=chunk.pdf_name,
                    text_chunk=chunk.text,
                    page_number=chunk.page_number,
                    chunk_index=chunk.chunk_index,
                    embedding=chunk.embedding
                )
                session.add(chunk_embedding)


async def semantic_search(
    query: str,
    top_k: int = 5,
    pdf_ids: Optional[List[int]] = None
) -> List[Dict[str, Any]]:
    """
    Perform semantic search on PDF chunks
    
    Args:
        query: The search query
        top_k: Number of results to return
        pdf_ids: Optional list of PDF IDs to restrict search to
        
    Returns:
        List of chunks with similarity scores
    """
    try:
        query_embedding = await generate_embedding(query)
        
        async with AsyncSession(engine) as session:
            # Calculate cosine similarity
            # This is more efficient than L2 distance for this case
            stmt = select(
                PDFEmbeddings,
                func.cosine_similarity(PDFEmbeddings.embedding, query_embedding).label("similarity")
            )
            
            if pdf_ids:
                stmt = stmt.filter(PDFEmbeddings.pdf_id.in_(pdf_ids))
            
            # Order by similarity (highest first) and limit results
            stmt = stmt.order_by(func.cosine_similarity(PDFEmbeddings.embedding, query_embedding).desc())
            stmt = stmt.limit(top_k)
            
            result = await session.execute(stmt)
            matches = result.all()
            
            results = []
            for row in matches:
                chunk = row[0]  # The PDFEmbeddings object
                similarity = row[1]  # The similarity score
                
                # Use the pdf_name directly from the PDFEmbeddings table
                results.append({
                    "pdf_id": chunk.pdf_id,
                    "pdf_name": chunk.pdf_name,
                    "page_number": chunk.page_number,
                    "text": chunk.text_chunk,
                    "similarity": float(similarity)  # Convert to Python float for JSON serialization
                })
            
            return results
    except Exception as e:
        LOGGER.error(f"Error performing semantic search: {str(e)}")
        return []


async def process_pdf_for_embedding(pdf_id: int, pdf_name: str, base64_pdf: str) -> bool:
    """
    Process a single PDF file:
    1. Chunk the PDF
    2. Generate embeddings for each chunk
    3. Store the chunks and embeddings in the database
    
    Args:
        pdf_id: ID of the PDF file
        pdf_name: Name of the PDF file
        base64_pdf: Base64-encoded PDF content
        
    Returns:
        True if successful, False otherwise
    """
    try:
        # Check if this PDF has already been processed
        async with AsyncSession(engine) as session:
            result = await session.execute(
                select(PDFEmbeddings).where(PDFEmbeddings.pdf_id == pdf_id).limit(1)
            )
            if result.scalar_one_or_none():
                LOGGER.info(f"PDF {pdf_id} ({pdf_name}) already processed for embedding")
                return True
        
        # Process PDF into chunks
        chunks = process_pdf_to_chunks(pdf_id, pdf_name, base64_pdf)
        LOGGER.info(f"Generated {len(chunks)} chunks for PDF {pdf_id} ({pdf_name})")
        
        # Generate embeddings and store in database
        async with AsyncSession(engine) as session:
            async with session.begin():
                for chunk in chunks:
                    # Generate embedding
                    embedding = await generate_embedding(chunk["text_chunk"])
                    
                    # Store in database
                    pdf_embedding = PDFEmbeddings(
                        pdf_id=chunk["pdf_id"],
                        pdf_name=pdf_name,  # Include the PDF name from the function parameter
                        text_chunk=chunk["text_chunk"],
                        page_number=chunk["page_number"],
                        chunk_index=chunk["chunk_index"],
                        embedding=embedding
                    )
                    session.add(pdf_embedding)
        
        LOGGER.info(f"Successfully processed PDF {pdf_id} ({pdf_name}) for embedding")
        return True
    except Exception as e:
        traceback.print_exc()
        LOGGER.error(f"Error processing PDF {pdf_id} for embedding: {str(e)}")
        return False


async def check_and_process_all_pdfs() -> Dict[str, Any]:
    """
    Check for any PDFs that haven't been processed for embedding and process them
    
    Returns:
        Dictionary with processing results
    """
    results = {
        "processed": 0,
        "errors": 0,
        "details": []
    }
    
    try:
        # Get all PDFs
        async with AsyncSession(engine) as session:
            pdf_result = await session.execute(select(PDFFiles))
            all_pdfs = pdf_result.all()
            
            # For each PDF, check if it has embeddings
            for pdf_row in all_pdfs:
                pdf = pdf_row[0]  # Unpack the row to get the actual model object
                
                # Check if PDF has embeddings
                embedding_result = await session.execute(
                    select(PDFEmbeddings).where(PDFEmbeddings.pdf_id == pdf.file_id).limit(1)
                )
                if embedding_result.scalar_one_or_none():
                    # Already processed
                    continue
                
                # Process this PDF
                success = await process_pdf_for_embedding(
                    pdf_id=pdf.file_id,
                    pdf_name=pdf.file_name,
                    base64_pdf=pdf.base64_data
                )
                
                result_details = {
                    "pdf_id": pdf.file_id,
                    "pdf_name": pdf.file_name,
                    "success": success
                }
                
                if success:
                    results["processed"] += 1
                else:
                    results["errors"] += 1
                
                results["details"].append(result_details)
        
        return results
    except Exception as e:
        LOGGER.error(f"Error checking and processing PDFs: {str(e)}")
        results["error"] = str(e)
        return results