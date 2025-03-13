"""
API routes for PDF data integration with query-data analyses
"""

import logging
import traceback
from fastapi import APIRouter, Request, Depends
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from auth_utils import validate_user_request
from utils_pdf.api import get_relevant_pdf_data

LOGGER = logging.getLogger("server")

router = APIRouter(
    dependencies=[Depends(validate_user_request)],
    tags=["Query data PDF integration"],
)


class PDFDataRequest(BaseModel):
    analysis_id: str


@router.post("/query-data/pdf-data")
async def get_pdf_data(request: PDFDataRequest):
    """
    Get relevant data from PDFs based on an analysis
    
    Args:
        analysis_id: ID of the analysis to get PDF data for
    
    Returns:
        PDF data content and source information
    """
    try:
        analysis_id = request.analysis_id
        
        LOGGER.info(f"Getting PDF data for analysis {analysis_id}")
        
        # Get relevant PDF data
        pdf_data = await get_relevant_pdf_data(analysis_id)
        
        if not pdf_data:
            return JSONResponse(
                status_code=200,
                content={
                    "success": True,
                    "has_data": False,
                    "message": "No relevant PDF data found"
                }
            )
        
        return JSONResponse(
            status_code=200,
            content={
                "success": True,
                "has_data": True,
                "content": pdf_data.content,
                "source_pdfs": pdf_data.source_pdfs
            }
        )
    except Exception as e:
        LOGGER.error(f"Error getting PDF data: {str(e)}")
        traceback.print_exc()
        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "message": f"Error getting PDF data: {str(e)}"
            }
        )