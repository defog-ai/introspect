"""
PDF data API functions

This module contains functions that are used by the PDF API endpoints:
1. Searching for relevant PDF content based on an analysis
2. Extracting structured data from PDF content using LLMs
"""

import logging
from typing import List, Dict, Any, Optional

import os
from anthropic import AsyncAnthropic
from pydantic import BaseModel

from db_models import Analyses
from db_config import engine
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from utils_oracle import get_project_pdf_files
from utils_pdf.embedding import semantic_search

LOGGER = logging.getLogger("server")

class PDFDataResponse(BaseModel):
    """Response model for PDF data"""
    content: str
    source_pdfs: List[Dict[str, Any]]


async def get_relevant_pdf_data(
    analysis_id: str,
    top_k_chunks: int = 5
) -> Optional[PDFDataResponse]:
    """
    Get relevant data from PDFs based on the analysis:
    1. Retrieve the analysis details
    2. Get the question and results
    3. Find relevant PDF chunks using semantic search
    4. Extract structured data from the chunks using LLM
    
    Args:
        analysis_id: ID of the analysis
        top_k_chunks: Number of most relevant chunks to consider
        
    Returns:
        Structured data extracted from PDFs, or None if not applicable
    """
    try:
        # Get analysis details
        async with AsyncSession(engine) as session:
            analysis_result = await session.execute(
                select(Analyses).where(Analyses.analysis_id == analysis_id)
            )
            analysis = analysis_result.scalar_one_or_none()
            
            if not analysis:
                LOGGER.warning(f"Analysis {analysis_id} not found")
                return None
                
            # Extract question and database name
            db_name = analysis.db_name
            user_question = analysis.user_question
            
            # Get analysis data if available
            if not analysis.data:
                LOGGER.warning(f"Analysis {analysis_id} has no data")
                return None
                
            analysis_data = analysis.data
            
        # Check if there's any SQL output to use as context
        sql_output = None
        if analysis_data.get("output"):
            sql_output = analysis_data.get("output")[:1000]  # Use first 1000 chars of output as context
            
        # Get PDF IDs for this project
        file_ids = await get_project_pdf_files(db_name)
        if not file_ids:
            LOGGER.info(f"No PDF files found for project {db_name}")
            return None
            
        # Create a search query that combines the user question and SQL output
        search_context = user_question
        if sql_output:
            search_context += f"\n\nSQL results: {sql_output}"
            
        # Search for relevant chunks
        relevant_chunks = await semantic_search(
            query=search_context,
            top_k=top_k_chunks,
            file_ids=file_ids
        )
        
        if not relevant_chunks:
            LOGGER.info(f"No relevant PDF chunks found for analysis {analysis_id}")
            return None
            
        # Extract structured data from the chunks using LLM
        pdf_data = await extract_data_from_chunks(
            user_question=user_question,
            sql_output=sql_output,
            relevant_chunks=relevant_chunks
        )
        
        if not pdf_data:
            LOGGER.info(f"No relevant data could be extracted from PDF chunks for analysis {analysis_id}")
            return None
            
        # Create a response with the content and sources
        source_pdfs = []
        pdf_names = set()
        for chunk in relevant_chunks:
            if chunk["pdf_name"] not in pdf_names:
                source_pdfs.append({
                    "file_id": chunk["file_id"],
                    "pdf_name": chunk["pdf_name"]
                })
                pdf_names.add(chunk["pdf_name"])
        
        return PDFDataResponse(
            content=pdf_data,
            source_pdfs=source_pdfs
        )
    except Exception as e:
        LOGGER.error(f"Error getting relevant PDF data for analysis {analysis_id}: {str(e)}")
        return None


async def extract_data_from_chunks(
    user_question: str,
    sql_output: Optional[str],
    relevant_chunks: List[Dict[str, Any]]
) -> Optional[str]:
    """
    Extract structured data from PDF chunks using an LLM
    
    Args:
        user_question: The original user question
        sql_output: Optional SQL query results as context
        relevant_chunks: List of relevant PDF chunks with metadata
        
    Returns:
        Structured data as extracted by the LLM, or None if no relevant data found
    """
    try:
        client = AsyncAnthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))
        
        # Combine chunks into context
        pdf_context = ""
        for i, chunk in enumerate(relevant_chunks):
            pdf_context += f"\nPDF {i+1}: {chunk['pdf_name']} (Page {chunk['page_number']})\n"
            pdf_context += f"Content: {chunk['text']}\n"
            pdf_context += f"Relevance Score: {chunk['similarity']:.2f}\n"
            pdf_context += "-" * 40 + "\n"
        
        # Create prompt for LLM
        prompt = f"""I need you to extract structured data from PDF content related to this question: 
        
{user_question}

"""
        
        if sql_output:
            prompt += f"""
I already have some SQL query results:

{sql_output}

"""
        
        prompt += f"""
Here are relevant sections from PDFs that may contain additional information:

{pdf_context}

Please extract any relevant structured data from these PDF sections that would augment the SQL results and help answer the original question. 

Format your response as Markdown with:
1. A brief summary of what information you found in the PDFs
2. Structured data in table format if appropriate
3. Citations to specific PDFs and page numbers

If the PDFs don't contain any relevant information to augment the SQL data, reply with 'NO_RELEVANT_DATA_FOUND'.
"""
        
        messages = [{"role": "user", "content": prompt}]
        
        response = await client.messages.create(
            model="claude-3-5-sonnet-20240620",
            messages=messages,
            max_tokens=2000,
        )
        
        extracted_data = response.content[0].text
        
        # Only return content if something relevant was found
        if "NO_RELEVANT_DATA_FOUND" in extracted_data:
            return None
        
        return extracted_data
    except Exception as e:
        LOGGER.error(f"Error extracting data from PDF chunks: {str(e)}")
        return None