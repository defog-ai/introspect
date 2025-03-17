"""
Unit tests for PDF search functionality.
"""

import json
import os
import time
import pytest

import requests
from utils_pdf.task_status import create_task_record
from conftest import TEST_DB, BASE_URL, create_pdf_and_get_base_64
from utils_oracle import delete_pdf_file

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

    file_id = None
    db_name = TEST_DB["db_name"]

    try:
        from utils_pdf.embedding import semantic_search

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
        file_id = db_info["associated_files"][0]["file_id"]

        # the above upload_files route also submits a pdf for processing
        
        print(f"Submitted PDF {file_id} ({pdf_name}) for processing. Waiting 5 secs for it to complete.")

        time.sleep(5)
        
        # now search
        result = await semantic_search("What is the capital of France?", top_k = 2, file_ids=[file_id])
        print(f"\n\n Search result: {json.dumps(result, indent=2)}\n\n")
        
        # Check the results
        assert len(result) == 2
        assert result[0]["text"] == "Paris is the capital of France."
        assert result[1]["text"] == "France has a big GDP. Its capital, Paris, is the biggest contributor."
    except Exception as e:
        # Any uncaught exceptions will be raised and fail the test
        raise e
    finally:
        # Clean up files regardless of test outcome
        if os.path.exists(temp_file_path):
            os.unlink(temp_file_path)
        
        # Only try to delete the PDF if we've created one
        if file_id:
            # Don't wait for the delete to complete - this prevents event loop issues
            # when running multiple tests that use asyncio
            try:
                import asyncio
                task = asyncio.create_task(delete_pdf_file(db_name, file_id))
                # We don't await the task as it causes event loop issues
            except Exception as cleanup_err:
                print(f"Warning: Failed to delete test PDF: {cleanup_err}")
