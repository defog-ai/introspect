"""
Startup script to check and process all PDFs for embedding
"""

import asyncio
import logging

from utils_pdf.embedding import check_and_process_all_pdfs

LOGGER = logging.getLogger("server")

async def process_pdfs_on_startup():
    """
    Run during application startup to check and process any PDFs
    that haven't been processed for embedding yet
    """
    LOGGER.info("Starting PDF embedding processing on startup")
    
    try:
        results = await check_and_process_all_pdfs()
        
        if results.get("processed", 0) > 0:
            LOGGER.info(f"Successfully processed {results['processed']} PDFs for embedding on startup")
        else:
            LOGGER.info("No new PDFs needed processing on startup")
            
        if results.get("errors", 0) > 0:
            LOGGER.warning(f"Encountered {results['errors']} errors while processing PDFs on startup")
            
    except Exception as e:
        LOGGER.error(f"Error in process_pdfs_on_startup: {str(e)}")