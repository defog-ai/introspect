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
from typing import List, Dict, Any, Optional

from openai import AsyncOpenAI
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from db_config import engine
from db_models import PDFEmbeddings
from utils_pdf.chunking import PDFChunk

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
            stmt = select(
                PDFEmbeddings
            )
            
            if pdf_ids:
                stmt = stmt.filter(PDFEmbeddings.pdf_id.in_(pdf_ids))
            
            # Order by similarity (highest first) and limit results
            stmt = stmt.order_by(PDFEmbeddings.embedding.cosine_distance(query_embedding))
            stmt = stmt.limit(top_k)
            
            result = await session.execute(stmt)
            matches = result.scalars().all()
            
            results = []
            for row in matches:
                results.append({
                    "pdf_id": row.pdf_id,
                    "pdf_name": row.pdf_name,
                    "text": row.text,
                    "page_number": row.page_number,
                })
            
            return results
    except Exception as e:
        traceback.print_exc()
        LOGGER.error(f"Error performing semantic search: {str(e)}")
        return []