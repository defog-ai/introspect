"""
Unit tests for PDF search functionality.
"""

import os
import time
import pytest

import requests
from utils_pdf.task_status import create_task_record
from conftest import TEST_DB, BASE_URL, create_pdf_and_get_base_64

@pytest.mark.asyncio
async def test_semantic_search():
    """Test semantic search on embeddings. Kind of an end to end test for pdf functionality:
    - Creates a pdf
    - Uploads the file to db via request
    - Calls the celery worker task which:
        - Chunks it
        - Embeds it
        - Adds it to db
    - Runs semantic search on the embedded pdf
    """
    # create a temp pdf with 4 pages
    pdf_name, temp_file_path, base64_pdf = create_pdf_and_get_base_64([
        "Paris is the capital of France.",
        "Delhi is the capital of India",
        "France has a big GDP. Its capital, Paris, is the biggest contributor.",
        "London is in UK"
    ])

    try:
        from utils_pdf.embedding import semantic_search

        db_name = TEST_DB["db_name"]

        # upload this pdf to a test db
        # Upload the PDF
        db_info = None
        with open(temp_file_path, 'rb') as pdf_file:
            files = [
                ('files', (os.path.basename(temp_file_path), pdf_file, 'application/pdf'))
            ]
            response = requests.post(f"{BASE_URL}/upload_files", files=files, data={"db_name": db_name})
            db_info = response.json()["db_info"]
        
        if not db_info:
            raise Exception("Failed to upload PDF file")

        # get pdf id
        pdf_id = db_info["associated_files"][0]["file_id"]

        # use celery task to create chunks, embed them and store
        from celery_tasks.pdf_tasks import process_pdf
        # Submit task to Celery
        task = process_pdf.delay(pdf_id, pdf_name, base64_pdf)
        
        # Record task in database for status tracking
        await create_task_record(task.id, pdf_id, pdf_name)
        
        print(f"Submitted Celery task {task.id} for PDF {pdf_id} ({pdf_name}). Waiting 5 secs for it to complete.")

        time.sleep(5)
        
        # now search
        result = await semantic_search("What is the capital of France?", top_k = 2, pdf_ids=[pdf_id])
        print(f"\n\n Search result: {result}\n\n")
        
        # Check the results
        assert len(result) == 2
        assert result[0]["text"] == "Paris is the capital of France."
        assert result[1]["text"] == "France has a big GDP. Its capital, Paris, is the biggest contributor."
        

    except Exception as e:
        pytest.fail(f"Test failed with exception: {str(e)}")
    finally:
        os.unlink(temp_file_path)
