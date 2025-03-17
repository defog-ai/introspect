"""
Tests for PDF data API routes
"""

import pytest
from unittest.mock import patch, AsyncMock, MagicMock
from fastapi.testclient import TestClient

from main import app
from query_data_pdf_routes import PDFDataRequest
from utils_pdf.api import PDFDataResponse


@pytest.fixture
def client():
    """Create a test client"""
    with TestClient(app) as client:
        yield client


@patch('query_data_pdf_routes.validate_user_request')
@patch('query_data_pdf_routes.get_relevant_pdf_data')
def test_get_pdf_data_with_results(mock_get_pdf_data, mock_validate_user, client):
    """Test the PDF data API endpoint with successful results"""
    # Bypass authentication
    mock_validate_user.return_value = None
    
    # Mock PDF data response
    mock_get_pdf_data.return_value = PDFDataResponse(
        content="## Revenue Analysis\n\nBased on the PDFs, revenue was $1.2M in 2023.",
        source_pdfs=[
            {"file_id": 123, "pdf_name": "Financial Report 2023.pdf"},
            {"file_id": 456, "pdf_name": "Q4 Analysis.pdf"}
        ]
    )
    
    # Make the API request
    response = client.post(
        "/query-data/pdf-data",
        json={"analysis_id": "analysis123"}
    )
    
    # Check response
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["has_data"] is True
    assert "Revenue Analysis" in data["content"]
    assert len(data["source_pdfs"]) == 2
    assert data["source_pdfs"][0]["file_id"] == 123
    assert data["source_pdfs"][0]["pdf_name"] == "Financial Report 2023.pdf"
    
    # Verify mock was called correctly
    mock_get_pdf_data.assert_called_once_with(analysis_id="analysis123")


@patch('query_data_pdf_routes.validate_user_request')
@patch('query_data_pdf_routes.get_relevant_pdf_data')
def test_get_pdf_data_no_results(mock_get_pdf_data, mock_validate_user, client):
    """Test the PDF data API endpoint when no PDF data is found"""
    # Bypass authentication
    mock_validate_user.return_value = None
    
    # Mock PDF data response as None (no data found)
    mock_get_pdf_data.return_value = None
    
    # Make the API request
    response = client.post(
        "/query-data/pdf-data",
        json={"analysis_id": "analysis123"}
    )
    
    # Check response
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["has_data"] is False
    assert "message" in data
    assert "No relevant PDF data found" in data["message"]


@patch('query_data_pdf_routes.validate_user_request')
@patch('query_data_pdf_routes.get_relevant_pdf_data')
def test_get_pdf_data_error(mock_get_pdf_data, mock_validate_user, client):
    """Test the PDF data API endpoint when an error occurs"""
    # Bypass authentication
    mock_validate_user.return_value = None
    
    # Mock PDF data function to raise an exception
    mock_get_pdf_data.side_effect = Exception("Test error")
    
    # Make the API request
    response = client.post(
        "/query-data/pdf-data",
        json={"analysis_id": "analysis123"}
    )
    
    # Check response
    assert response.status_code == 500
    data = response.json()
    assert data["success"] is False
    assert "message" in data
    assert "Error getting PDF data" in data["message"]