"""
Integration tests for PDF processing with Celery

These tests are designed to run inside the Docker container and 
test the actual functionality with real infrastructure.
"""
import asyncio
from io import BytesIO
import os
import tempfile
import pytest
from fastapi.testclient import TestClient
from conftest import TEST_DB

from main import app

client = TestClient(app)


def test_pdf_upload_and_processing():
    """
    Test the full PDF upload and processing flow.
    This test should be run inside the Docker container.
    """
    try:
        # Import required modules directly inside test to avoid import errors
        from db_config import engine
        from sqlalchemy.ext.asyncio import AsyncSession
        from sqlalchemy import select, delete
        from db_models import PDFFiles, PDFProcessingTask, PDFEmbeddings
        from utils_pdf.task_status import get_pdf_processing_status
        from starlette.datastructures import FormData, UploadFile

        
        # Create a simple PDF for testing
        pdf_content = b'%PDF-1.4\n1 0 obj\n<<\n/Type /Catalog\n>>\nendobj\n%%EOF'
        pdf_name = "test_upload.pdf"
        
        db_name = TEST_DB["db_name"]

        # Create temp PDF file with predictable name
        pdf_filename = 'product_catalog.pdf'
        pdf_path = os.path.join(tempfile.gettempdir(), pdf_filename)
        with open(pdf_path, 'wb') as pdf_file:
            pdf_file.write(pdf_content)
        
        # Upload the PDF
        with open(pdf_path, 'rb') as pdf_file:
            files = [
                ('files', (os.path.basename(pdf_path), pdf_file, 'application/pdf'))
            ]
            response = client.post("/upload_files", files=files, data={"db_name": db_name})

        os.unlink(pdf_path)
        
        # Check response
        assert response.status_code == 200
        
        # # Get the PDF ID from the database
        # async with AsyncSession(engine) as session:
        #     result = await session.execute(
        #         select(PDFFiles.file_id).where(PDFFiles.file_name == pdf_name)
        #     )
        #     pdf_id = result.scalar_one_or_none()
            
        #     # Make sure the PDF was added to the database
        #     assert pdf_id is not None, "PDF file not found in database"
            
        #     # Wait a bit for the task to be created
        #     for _ in range(5):  # Try for 5 seconds
        #         result = await session.execute(
        #             select(PDFProcessingTask).where(PDFProcessingTask.pdf_id == pdf_id)
        #         )
        #         task = result.scalar_one_or_none()
        #         if task:
        #             break
        #         await asyncio.sleep(1)
            
        #     # Verify task was created
        #     assert task is not None, "PDF processing task not created"
            
        #     # Check the task status
        #     status_response = await get_pdf_processing_status(pdf_id)
        #     assert status_response["pdf_id"] == pdf_id
        #     assert status_response["pdf_name"] == pdf_name
        #     assert status_response["status"] in ["PENDING", "PROCESSING", "COMPLETED"]
            
        #     # If we're patient enough, wait for processing to complete
        #     max_wait = 15  # Wait up to 15 seconds for processing
        #     for i in range(max_wait):
        #         status_response = await get_pdf_processing_status(pdf_id)
        #         if status_response["status"] in ["COMPLETED", "FAILED"]:
        #             break
        #         await asyncio.sleep(1)
            
        #     # Check for embeddings
        #     if status_response["status"] == "COMPLETED":
        #         result = await session.execute(
        #             select(PDFEmbeddings).where(PDFEmbeddings.pdf_id == pdf_id)
        #         )
        #         embeddings = result.scalars().all()
        #         assert len(embeddings) > 0, "No embeddings found for processed PDF"
            
        #     # Clean up after test
        #     await session.execute(delete(PDFEmbeddings).where(PDFEmbeddings.pdf_id == pdf_id))
        #     await session.execute(delete(PDFProcessingTask).where(PDFProcessingTask.pdf_id == pdf_id))
        #     await session.execute(delete(PDFFiles).where(PDFFiles.file_id == pdf_id))
        #     await session.commit()
    except Exception as e:
        print(f"\nTest failed with error: {str(e)}")
        raise e


# @pytest.mark.asyncio
# async def test_pdf_status_endpoints():
#     """
#     Test the PDF processing status endpoints.
#     """
#     from db_config import engine
#     from sqlalchemy.ext.asyncio import AsyncSession
#     from sqlalchemy import select, delete
#     from db_models import PDFFiles, PDFProcessingTask, PDFProcessingStatus
#     from file_upload_routes import get_pdf_status, get_all_pdf_statuses
    
#     # Create a test PDF file and processing task
#     async with AsyncSession(engine) as session:
#         # Create a PDF file entry
#         pdf_file = PDFFiles(
#             file_name="status_test.pdf",
#             base64_data="test_data"
#         )
#         session.add(pdf_file)
#         await session.flush()
        
#         pdf_id = pdf_file.file_id
        
#         # Create a task record
#         task = PDFProcessingTask(
#             task_id="test-task-id",
#             pdf_id=pdf_id,
#             pdf_name="status_test.pdf",
#             status=PDFProcessingStatus.PROCESSING
#         )
#         session.add(task)
#         await session.commit()
        
#         try:
#             # Test get_pdf_status endpoint
#             response = await get_pdf_status(pdf_id=pdf_id, token="test_token")
#             assert response.status_code == 200
            
#             response_json = response.body.decode("utf-8")
#             assert "status_test.pdf" in response_json
#             assert "PROCESSING" in response_json
            
#             # Test get_all_pdf_statuses endpoint
#             response = await get_all_pdf_statuses(token="test_token")
#             assert response.status_code == 200
            
#             response_json = response.body.decode("utf-8")
#             assert "status_test.pdf" in response_json
#             assert "PROCESSING" in response_json
            
#             # Test with db_name filter
#             response = await get_all_pdf_statuses(token="test_token", db_name="nonexistent")
#             assert response.status_code == 200
#             # This should return an empty list since our test PDF isn't associated with this db_name
            
#         finally:
#             # Clean up
#             await session.execute(delete(PDFProcessingTask).where(PDFProcessingTask.pdf_id == pdf_id))
#             await session.execute(delete(PDFFiles).where(PDFFiles.file_id == pdf_id))
#             await session.commit()