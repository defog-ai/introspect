"""
Functions for tracking and querying PDF processing task status
"""
import logging
from datetime import datetime
from typing import Dict, List, Optional, Any, Union

from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession

from db_config import engine
from db_models import PDFProcessingTasks, PDFProcessingStatus, PDFFiles

LOGGER = logging.getLogger("server")

async def create_task_record(task_id: str, file_id: int, pdf_name: str) -> None:
    """
    Create a new task record for PDF processing
    
    Args:
        task_id: Celery task ID
        file_id: ID of the PDF file
        pdf_name: Name of the PDF file
    """
    async with AsyncSession(engine) as session:
        async with session.begin():
            # first delete all tasks with this file id
            delete_stmt = delete(PDFProcessingTasks).where(
                PDFProcessingTasks.file_id == file_id
            )
            await session.execute(delete_stmt)
            
            # now create a new one
            task_record = PDFProcessingTasks(
                task_id=task_id,
                file_id=file_id,
                pdf_name=pdf_name,
                status=PDFProcessingStatus.PENDING,
                created_at=datetime.now(),
                updated_at=datetime.now()
            )
            session.add(task_record)

async def get_pdf_processing_status(file_id: int) -> Dict[str, Any]:
    """
    Get the processing status of a PDF file
    
    Args:
        file_id: ID of the PDF file
        
    Returns:
        Dictionary with status information
    """
    async with AsyncSession(engine) as session:
        # Get the latest processing task for this PDF
        query = select(PDFProcessingTasks).where(
            PDFProcessingTasks.file_id == file_id
        ).order_by(PDFProcessingTasks.updated_at.desc())
        
        result = await session.execute(query)
        task = result.scalar_one_or_none()
        
        if not task:
            return {
                "file_id": file_id,
                "status": "UNKNOWN",
                "message": "No processing task found for this PDF"
            }
        
        return {
            "file_id": file_id,
            "pdf_name": task.pdf_name,
            "task_id": task.task_id,
            "status": task.status.value,
            "created_at": task.created_at.isoformat() if task.created_at else None,
            "updated_at": task.updated_at.isoformat() if task.updated_at else None,
            "error_message": task.error_message
        }

async def get_all_pdf_processing_statuses() -> List[Dict[str, Any]]:
    """
    Get processing status for all PDFs
    
    Returns:
        List of dictionaries with status information for all PDFs
    """
    async with AsyncSession(engine) as session:
        # First get all PDFs
        pdf_query = select(PDFFiles)
        pdf_result = await session.execute(pdf_query)
        pdf_files = {pdf.file_id: pdf for pdf in pdf_result.scalars().all()}
        
        # Then get the latest task for each PDF
        results = []
        for file_id, pdf in pdf_files.items():
            # Get the latest task
            task_query = select(PDFProcessingTasks).where(
                PDFProcessingTasks.file_id == file_id
            ).order_by(PDFProcessingTasks.updated_at.desc())
            
            task_result = await session.execute(task_query)
            task = task_result.scalar_one_or_none()
            
            status_info = {
                "file_id": file_id,
                "pdf_name": pdf.file_name,
            }
            
            if task:
                status_info.update({
                    "task_id": task.task_id,
                    "status": task.status.value,
                    "created_at": task.created_at.isoformat() if task.created_at else None,
                    "updated_at": task.updated_at.isoformat() if task.updated_at else None,
                    "error_message": task.error_message
                })
            else:
                # No task found - PDF wasn't processed or predates task tracking
                status_info.update({
                    "status": "UNKNOWN",
                    "message": "No processing information available"
                })
            
            results.append(status_info)
        
        return results