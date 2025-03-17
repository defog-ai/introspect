"""
Celery tasks for PDF processing
"""
import logging
import traceback
from datetime import datetime
from typing import Dict, Any, Optional

from celery import Task
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from celery_app import celery_app
from db_config import engine, get_sync_engine
from db_models import PDFFiles, PDFEmbeddings, PDFProcessingTask, PDFProcessingStatus
from utils_pdf.chunking import process_pdf_to_chunks
from utils_pdf.embedding import generate_embedding

LOGGER = logging.getLogger("server")

class PDFProcessingCeleryTask(Task):
    """Base task for PDF processing with error handling and status updates"""
    
    def on_failure(self, exc, task_id, args, kwargs, einfo):
        """Handle task failure by updating the status"""
        # Use a synchronous session for Celery context
        from sqlalchemy.orm import Session
        
        sync_engine = get_sync_engine()
        with Session(sync_engine) as session:
            pdf_id = kwargs.get('pdf_id') or args[0]
            
            # Update task status to FAILED
            stmt = update(PDFProcessingTask).where(
                PDFProcessingTask.task_id == task_id
            ).values(
                status=PDFProcessingStatus.FAILED,
                error_message=str(exc),
                updated_at=datetime.now()
            )
            session.execute(stmt)
            session.commit()
            
        LOGGER.error(f"PDF processing task {task_id} failed: {exc}")
        return super().on_failure(exc, task_id, args, kwargs, einfo)

@celery_app.task(bind=True, base=PDFProcessingCeleryTask)
def process_pdf(self, pdf_id: int, pdf_name: str, base64_pdf: str) -> Dict[str, Any]:
    """
    Process a PDF file for embedding:
    1. Extract text and create chunks
    2. Generate embeddings for each chunk
    3. Store embeddings in the database
    4. Update processing status
    
    Args:
        pdf_id: ID of the PDF file in the database
        pdf_name: Name of the PDF file
        base64_pdf: Base64-encoded PDF content
        
    Returns:
        Dictionary with processing results
    """
    # Get a synchronous database session for Celery worker
    from sqlalchemy.orm import Session
    
    task_id = self.request.id
    sync_engine = get_sync_engine()
    results = {
        "pdf_id": pdf_id,
        "pdf_name": pdf_name,
        "chunks_processed": 0,
        "success": False
    }
    
    try:
        # Update task status to PROCESSING
        with Session(sync_engine) as session:
            stmt = update(PDFProcessingTask).where(
                PDFProcessingTask.task_id == task_id
            ).values(
                status=PDFProcessingStatus.PROCESSING,
                updated_at=datetime.now()
            )
            session.execute(stmt)
            session.commit()
        
        # Step 1: Process PDF into chunks
        LOGGER.info(f"Processing PDF {pdf_id} ({pdf_name}) into chunks")
        chunks = process_pdf_to_chunks(pdf_id, pdf_name, base64_pdf)
        LOGGER.info(f"Generated {len(chunks)} chunks for PDF {pdf_id}")
        
        # Step 2 & 3: Generate embeddings and store in database
        with Session(sync_engine) as session:
            for chunk in chunks:
                # Generate embedding
                embedding = generate_embedding_sync(chunk.text)
                
                # Store in database
                pdf_embedding = PDFEmbeddings(
                    pdf_id=chunk.pdf_id,
                    pdf_name=pdf_name,
                    text=chunk.text,
                    page_number=chunk.page_number,
                    chunk_index=chunk.chunk_index,
                    embedding=embedding
                )
                session.add(pdf_embedding)
                results["chunks_processed"] += 1
            
            # Update task status to COMPLETED
            stmt = update(PDFProcessingTask).where(
                PDFProcessingTask.task_id == task_id
            ).values(
                status=PDFProcessingStatus.COMPLETED,
                updated_at=datetime.now()
            )
            session.execute(stmt)
            session.commit()
        
        results["success"] = True
        LOGGER.info(f"Successfully processed {results['chunks_processed']} chunks for PDF {pdf_id}")
        return results
        
    except Exception as e:
        error_msg = f"Error processing PDF {pdf_id}: {str(e)}"
        LOGGER.error(error_msg)
        traceback.print_exc()
        
        # The on_failure handler will update the task status
        raise Exception(error_msg)

def generate_embedding_sync(text: str) -> list:
    """
    Synchronous version of generate_embedding for Celery workers
    
    Args:
        text: Text to embed
        
    Returns:
        Embedding vector as a list of floats
    """
    import os
    from openai import OpenAI
    
    try:
        client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))
        response = client.embeddings.create(
            model="text-embedding-3-small",
            input=text
        )
        return response.data[0].embedding
    except Exception as e:
        LOGGER.error(f"Error generating embedding: {str(e)}")
        raise