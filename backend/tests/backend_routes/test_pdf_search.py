import pytest
import os
import uuid
from fastapi.testclient import TestClient
import requests

from main import app
from .conftest import BASE_URL, TEST_DB, create_pdf_and_get_base_64

client = TestClient(app)


def test_pdf_search_workflow(admin_token):
    """Test the complete PDF search workflow:
    1. Upload PDF files
    2. Create an analysis
    3. Generate analysis step
    4. Run PDF search on the analysis
    """
    # Step 1: Create and upload PDF files with relevant content
    # Create first PDF with content about VIP tickets
    pdf1_name, pdf1_path, pdf1_base64 = create_pdf_and_get_base_64([
        "This is a test PDF document for testing the SQL-PDF search feature.",
        "It contains information about ticket prices.",
        "VIP tickets cost $150 and include special perks.",
        "Standard tickets cost $50 for regular admission."
    ])
    
    # Create second PDF with content about ticket sales
    pdf2_name, pdf2_path, pdf2_base64 = create_pdf_and_get_base_64([
        "This is another test PDF for SQL-PDF search.",
        "Information about ticket sales data.",
        "VIP tickets have been selling well among corporate clients.",
        "Student tickets at $25 are popular among younger audiences."
    ])
    
    pdf_ids = []
    
    try:
        # Upload first PDF
        with open(pdf1_path, 'rb') as pdf_file:
            files = [
                ('files', (pdf1_name, pdf_file, 'application/pdf'))
            ]
            form_data = {
                'token': admin_token,
                'db_name': TEST_DB["db_name"]
            }
            
            response = requests.post(
                f"{BASE_URL}/upload_files",
                files=files,
                data=form_data
            )
        
        assert response.status_code == 200
        upload_result = response.json()
        assert "message" in upload_result
        assert upload_result["message"] == "Success"
        assert "db_name" in upload_result
        assert upload_result["db_name"] == TEST_DB["db_name"]
        assert "db_info" in upload_result
        
        # Upload second PDF
        with open(pdf2_path, 'rb') as pdf_file:
            files = [
                ('files', (pdf2_name, pdf_file, 'application/pdf'))
            ]
            form_data = {
                'token': admin_token,
                'db_name': TEST_DB["db_name"]
            }
            
            response = requests.post(
                f"{BASE_URL}/upload_files",
                files=files,
                data=form_data
            )
        
        assert response.status_code == 200
        upload_result = response.json()
        assert "message" in upload_result
        assert upload_result["message"] == "Success"
        assert "db_name" in upload_result
        assert upload_result["db_name"] == TEST_DB["db_name"]
        assert "db_info" in upload_result

        pdf_ids = [x["file_id"] for x in upload_result["db_info"]["associated_files"]]
        
        # Step 2: Create an analysis
        analysis_id = str(uuid.uuid4())
        create_analysis_response = requests.post(
            f"{BASE_URL}/query-data/create_analysis",
            json={
                "token": admin_token,
                "db_name": TEST_DB["db_name"],
                "custom_id": analysis_id,
                "initialisation_details": {
                    "user_question": "What are the prices of VIP tickets?"
                }
            }
        )
        
        assert create_analysis_response.status_code == 200
        analysis = create_analysis_response.json()
        assert analysis["analysis_id"] == analysis_id
        
        # Step 3: Generate analysis step (SQL query)
        generate_response = requests.post(
            f"{BASE_URL}/query-data/generate_analysis",
            json={
                "token": admin_token,
                "db_name": TEST_DB["db_name"],
                "analysis_id": analysis_id,
                "user_question": "What are the prices of VIP tickets?"
            }
        )
        
        assert generate_response.status_code == 200
        generated_analysis = generate_response.json()
        assert generated_analysis["data"]["sql"] is not None
        assert "VIP" in generated_analysis["data"]["sql"] or "vip" in generated_analysis["data"]["sql"]
        
        # Step 4: Run PDF search on the analysis
        pdf_search_response = requests.post(
            f"{BASE_URL}/query-data/pdf_search",
            json={
                "analysis_id": analysis_id,
                "token": admin_token,
            },
        )
        
        assert pdf_search_response.status_code == 200
        pdf_search_result = pdf_search_response.json()
        assert pdf_search_result.get("success") is True
        assert "pdf_results" in pdf_search_result
        assert "analysis" in pdf_search_result
        
        # Verify the analysis contains the PDF search results
        updated_analysis = pdf_search_result["analysis"]
        assert "pdf_search_results" in updated_analysis["data"]
        assert updated_analysis["data"]["pdf_search_results"] is not None
        
        # Print the PDF search results for debugging
        print("PDF Search Results:", pdf_search_result["pdf_results"])
    
    finally:
        # Clean up temporary PDF files
        for path in [pdf1_path, pdf2_path]:
            if os.path.exists(path):
                os.remove(path)
        for file_id in pdf_ids:
            # remove the pdfs from the db
            # call the /delete_pdf/{file_id} route
            delete_pdf_response = requests.delete(f"{BASE_URL}/delete_pdf/{file_id}?token={admin_token}&db_name={TEST_DB['db_name']}")
            assert delete_pdf_response.status_code == 200
