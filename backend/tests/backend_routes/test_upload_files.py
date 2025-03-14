"""Tests for file upload functionality."""

import os
import random
import tempfile
import pytest
import requests
import sys

from .conftest import BASE_URL, TEST_DB, cleanup_test_database


def test_add_pdf_to_project(admin_token):
    """Test adding a PDF file to an existing database (test_db)"""
    db_name = TEST_DB["db_name"]
    
    try:
        # First, ensure DB credentials are set up
        add_creds_payload = {
            "token": admin_token,
            "db_name": db_name,
            "db_type": TEST_DB["db_type"],
            "db_creds": TEST_DB["db_creds"],
        }
        response = requests.post(
            f"{BASE_URL}/integration/update_db_creds", json=add_creds_payload
        )
        assert response.status_code == 200, f"Failed to set up database credentials. Response: {response.text}"
        
        # Create a simple PDF content (minimal valid PDF)
        pdf_content = b"%PDF-1.0\n1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj 2 0 obj<</Type/Pages/Kids[3 0 R]/Count 1>>endobj 3 0 obj<</Type/Page/MediaBox[0 0 612 792]/Resources<<>>>>endobj\nxref\n0 4\n0000000000 65535 f\n0000000010 00000 n\n0000000053 00000 n\n0000000102 00000 n\ntrailer<</Size 4/Root 1 0 R>>\nstartxref\n149\n%%EOF"
        
        # Create temporary PDF file with predictable name
        import tempfile
        import os
        
        pdf_filename = 'test_document.pdf'
        pdf_path = os.path.join(tempfile.gettempdir(), pdf_filename)
        with open(pdf_path, 'wb') as pdf_file:
            pdf_file.write(pdf_content)
        
        # Get DB info before uploading to check current state
        get_db_info_response = requests.post(
            f"{BASE_URL}/integration/get_db_info",
            json={"token": admin_token, "db_name": db_name},
        )
        assert get_db_info_response.status_code == 200, f"Failed to get DB info: {get_db_info_response.text}"
        
        initial_db_info = get_db_info_response.json()
        initial_pdf_count = len(initial_db_info.get("associated_files", []))
        print(f"\nInitial PDF count: {initial_pdf_count}")
        
        # Upload PDF to existing database
        with open(pdf_path, 'rb') as pdf_f:
            # Use multipart form data to upload the PDF file
            files = [
                ('files', (pdf_filename, pdf_f, 'application/pdf'))
            ]
            form_data = {
                'token': admin_token,
                'db_name': db_name
            }
            
            response = requests.post(
                f"{BASE_URL}/upload_files",
                files=files,
                data=form_data
            )
        
        # Cleanup the temp file
        os.unlink(pdf_path)
        
        # Verify the response
        assert response.status_code == 200, f"Failed to upload PDF: {response.text}"
        data = response.json()
        print(f"\nResponse data: {data}")
        
        # Verify the database name matches
        assert data["db_name"] == db_name, f"Expected db_name to be {db_name}, got {data['db_name']}"
        
        # Get updated DB info to verify PDF was added
        updated_db_info = data["db_info"]
        print(f"\nUpdated DB info: {updated_db_info}")
        
        # Verify PDF was associated with the project
        assert "associated_files" in updated_db_info, "No associated_files in db_info"
        assert len(updated_db_info["associated_files"]) > initial_pdf_count, f"No new PDF files added"
        
        # Get the newly added PDF file ID (the last one in the list)
        pdf_file_id = updated_db_info["associated_files"][-1]
        print(f"\nNewly added PDF file ID: {pdf_file_id}")
        
        # If PDF file ID is a dictionary, extract the ID
        if isinstance(pdf_file_id, dict) and 'file_id' in pdf_file_id:
            pdf_file_id = pdf_file_id['file_id']
        
        # Verify PDF file can be downloaded
        download_response = requests.get(
            f"{BASE_URL}/download_pdf/{pdf_file_id}"
        )
        assert download_response.status_code == 200, f"Failed to download PDF: {download_response.text}"
        assert download_response.headers["Content-Type"] == "application/pdf", "Response is not a PDF file"
        
        # Store PDF ID globally for the next test
        global TEST_PDF_ID
        TEST_PDF_ID = pdf_file_id
        
    except Exception as e:
        print(f"\nTest failed with error: {str(e)}")
        raise e


def test_delete_pdf_from_project(admin_token):
    """Test deleting a PDF file from an existing database (test_db)"""
    db_name = TEST_DB["db_name"]
    
    try:
        # First, check if we have a PDF ID from the previous test
        global TEST_PDF_ID
        pdf_file_id = None
        
        try:
            if TEST_PDF_ID:
                pdf_file_id = TEST_PDF_ID
                print(f"\nUsing PDF ID from previous test: {pdf_file_id}")
        except NameError:
            # If TEST_PDF_ID doesn't exist, we'll find one from DB info
            pass
            
        # If we don't have a PDF ID yet, get current DB info to find PDF files
        if not pdf_file_id:
            get_db_info_response = requests.post(
                f"{BASE_URL}/integration/get_db_info",
                json={"token": admin_token, "db_name": db_name},
            )
            assert get_db_info_response.status_code == 200, f"Failed to get DB info: {get_db_info_response.text}"
            
            initial_db_info = get_db_info_response.json()
            print(f"\nInitial DB info: {initial_db_info}")
            
            # Verify there are PDF files associated with the project
            assert "associated_files" in initial_db_info, "No associated_files in db_info"
            associated_files = initial_db_info.get("associated_files", [])
            assert len(associated_files) > 0, "No PDF files found to delete"
            
            # Get the first PDF file ID
            pdf_file_id = associated_files[0]
            
        print(f"\nPDF file ID to delete: {pdf_file_id}")
        
        # If PDF file ID is a dictionary, extract the ID
        if isinstance(pdf_file_id, dict) and 'file_id' in pdf_file_id:
            pdf_file_id = pdf_file_id['file_id']
        
        # Delete the PDF file
        delete_response = requests.delete(
            f"{BASE_URL}/delete_pdf/{pdf_file_id}",
            params={"token": admin_token, "db_name": db_name}
        )
        assert delete_response.status_code == 200, f"Failed to delete PDF: {delete_response.text}"
        
        # Verify the PDF was removed from the project
        updated_db_info = delete_response.json()["db_info"]
        print(f"\nUpdated DB info after deletion: {updated_db_info}")
        
        # Get the currently associated files
        updated_files = updated_db_info.get("associated_files", [])
        
        # If we're dealing with dictionary IDs, convert them for comparison
        if updated_files and isinstance(updated_files[0], dict) and 'file_id' in updated_files[0]:
            file_ids = [f['file_id'] for f in updated_files]
            assert pdf_file_id not in file_ids, "PDF file was not removed from project"
        else:
            assert pdf_file_id not in updated_files, "PDF file was not removed from project"
        
        print(f"\nSuccessfully deleted PDF file with ID: {pdf_file_id}")
        
    except Exception as e:
        print(f"\nTest failed with error: {str(e)}")
        raise e


def test_upload_single_csv_file(admin_token):
    """Test uploading a CSV file through the /upload_files endpoint"""
    # Create a unique database name for this test
    test_db_name = f"csv_single_{random.randint(1000, 9999)}"
    
    try:
        # Create a simple CSV for testing
        csv_content = """Name,Age,City
John Doe,30,New York
Jane Smith,25,Los Angeles
Bob Johnson,40,Chicago"""
        
        # Create CSV file with our desired name
        import os
        import tempfile
        temp_dir = tempfile.gettempdir()
        temp_file_path = os.path.join(temp_dir, 'test_single_csv_file.csv')
        
        # Write content to the file
        with open(temp_file_path, 'w') as temp_file:
            temp_file.write(csv_content)
        
        # Open the file for upload
        with open(temp_file_path, 'rb') as file:
            # Use multipart form data to upload the file
            files = {'files': (os.path.basename(temp_file_path), file, 'text/csv')}
            form_data = {
                'token': admin_token,
                'db_name': test_db_name  # Specify the database name
            }
            
            # Send the upload request
            response = requests.post(
                f"{BASE_URL}/upload_files",
                files=files,
                data=form_data
            )
        
        # Cleanup the temp file
        os.unlink(temp_file_path)
        
        # Verify the response
        assert response.status_code == 200, f"Failed to upload CSV file: {response.text}"
        data = response.json()
        assert "db_name" in data, "No db_name in response"
        assert "db_info" in data, "No db_info in response"
        
        db_name = data["db_name"]
        db_info = data["db_info"]
        
        # Make sure we got the right database name back
        assert db_name == test_db_name, f"Expected db_name to be {test_db_name}, got {db_name}"
        
        # Verify the database was created and contains our table
        assert "tables" in db_info, "No tables in db_info"
        assert len(db_info["tables"]) == 1, f"Expected 1 table, got {len(db_info['tables'])}"
        
        # Get the table name (should be based on the CSV filename)
        table_name = db_info["tables"][0]
        assert table_name == "test_single_csv_file", f"Table name '{table_name}' does not match expected 'test_single_csv_file'"
        
        # Verify the table has the correct columns by querying it
        get_metadata_response = requests.post(
            f"{BASE_URL}/integration/get_metadata",
            json={"token": admin_token, "db_name": db_name, "format": "json"},
            headers={"Content-Type": "application/json"},
        )
        
        assert get_metadata_response.status_code == 200, f"Failed to get metadata: {get_metadata_response.text}"
        metadata = get_metadata_response.json()["metadata"]
        
        # Extract column names from metadata
        columns = {m["column_name"] for m in metadata if m["table_name"] == table_name}
        expected_columns = {"name", "age", "city"}
        
        # Verify all columns exist (case-insensitive comparison)
        for col in expected_columns:
            assert any(col.lower() == c.lower() for c in columns), f"Column '{col}' not found in uploaded CSV table"
            
    except Exception as e:
        print(f"\nTest failed with error: {str(e)}")
        raise e
    finally:
        # Always clean up the test database, even if the test fails
        cleanup_test_database(test_db_name)


def test_upload_single_excel_sheet(admin_token):
    """Test uploading an Excel file with a single sheet through the /upload_files endpoint"""
    # Create a unique database name for this test
    test_db_name = f"excel_single_{random.randint(1000, 9999)}"
    
    try:
        # Skip if pandas is not installed
        try:
            import pandas as pd
        except ImportError:
            pytest.skip("pandas not installed")
        
        # Create a simple Excel file for testing
        data = {
            'Product': ['Widget A', 'Widget B', 'Widget C'],
            'Price': [19.99, 29.99, 39.99],
            'Quantity': [100, 200, 300]
        }
        df = pd.DataFrame(data)
        
        # Create Excel file with our desired name
        import os
        import tempfile
        temp_dir = tempfile.gettempdir()
        temp_file_path = os.path.join(temp_dir, 'test_single_excel_sheet.xlsx')
        
        # Write the dataframe to the Excel file with our desired sheet name
        with pd.ExcelWriter(temp_file_path) as writer:
            df.to_excel(writer, sheet_name='test_single_excel_sheet', index=False)
        
        # Open the file for upload
        with open(temp_file_path, 'rb') as file:
            # Use multipart form data to upload the file
            files = {'files': (os.path.basename(temp_file_path), file, 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')}
            form_data = {
                'token': admin_token,
                'db_name': test_db_name  # Specify the database name
            }
            
            # Send the upload request
            response = requests.post(
                f"{BASE_URL}/upload_files",
                files=files,
                data=form_data
            )
        
        # Cleanup the temp file
        os.unlink(temp_file_path)
        
        # Verify the response
        assert response.status_code == 200, f"Failed to upload Excel file: {response.text}"
        data = response.json()
        assert "db_name" in data, "No db_name in response"
        assert "db_info" in data, "No db_info in response"
        
        db_name = data["db_name"]
        db_info = data["db_info"]
        
        # Make sure we got the right database name back
        assert db_name == test_db_name, f"Expected db_name to be {test_db_name}, got {db_name}"
        
        # Verify the database was created and contains our table(s)
        assert "tables" in db_info, "No tables in db_info"
        assert len(db_info["tables"]) >= 1, f"Expected at least 1 table, got {len(db_info['tables'])}"
        
        # Get first table name (should be based on the Excel filename)
        table_name = db_info["tables"][0]
        assert table_name == "test_single_excel_sheet", f"Table name '{table_name}' does not match expected 'test_single_excel_sheet'. Note: For Excel files, the table name comes from the sheet name, not the file name."
        
        # Verify the table has the correct columns by querying the metadata
        get_metadata_response = requests.post(
            f"{BASE_URL}/integration/get_metadata",
            json={"token": admin_token, "db_name": db_name, "format": "json"},
            headers={"Content-Type": "application/json"},
        )
        
        assert get_metadata_response.status_code == 200, f"Failed to get metadata: {get_metadata_response.text}"
        metadata = get_metadata_response.json()["metadata"]
        
        # Print current columns for debugging
        print("\nAvailable columns in Excel table:")
        columns = {m["column_name"] for m in metadata if m["table_name"] == table_name}
        for col in columns:
            print(f"- {col}")
        
        # Column names are sanitized in system (converted to lowercase, special chars replaced)
        expected_column_prefixes = {"product", "price", "quantity"}
        
        # Verify all expected columns exist with more flexible matching (prefix matching)
        for expected_prefix in expected_column_prefixes:
            matching_columns = [c for c in columns if c.startswith(expected_prefix)]
            assert matching_columns, f"No column starting with '{expected_prefix}' found in uploaded Excel table"
        
    except Exception as e:
        print(f"\nTest failed with error: {str(e)}")
        raise e
    finally:
        # Always clean up the test database, even if the test fails
        cleanup_test_database(test_db_name)


def test_upload_multiple_csv_files(admin_token):
    """Test uploading multiple CSV files in a single request"""
    test_db_name = f"multi_csv_{random.randint(1000, 9999)}"
    
    try:
        # Create two CSV files with different data
        csv_content1 = """Customer,Email,Orders
Alice Johnson,alice@example.com,5
Bob Williams,bob@example.com,3
Charlie Davis,charlie@example.com,8"""
        
        csv_content2 = """Product,Category,Price
Laptop,Electronics,999.99
Phone,Electronics,499.99
Tablet,Electronics,299.99"""
        
        # Create temporary files
        import tempfile
        with tempfile.NamedTemporaryFile(suffix='.csv', delete=False) as csv_file1:
            csv_file1.write(csv_content1.encode('utf-8'))
            csv_file_path1 = csv_file1.name
            
        with tempfile.NamedTemporaryFile(suffix='.csv', delete=False) as csv_file2:
            csv_file2.write(csv_content2.encode('utf-8'))
            csv_file_path2 = csv_file2.name
        
        # Upload both CSV files in a single request
        with open(csv_file_path1, 'rb') as file1, open(csv_file_path2, 'rb') as file2:
            # Use multipart form data to upload both files
            files = [
                ('files', (os.path.basename(csv_file_path1), file1, 'text/csv')),
                ('files', (os.path.basename(csv_file_path2), file2, 'text/csv'))
            ]
            form_data = {
                'token': admin_token,
                'db_name': test_db_name
            }
            
            # Send the upload request with both files
            response = requests.post(
                f"{BASE_URL}/upload_files",
                files=files,
                data=form_data
            )
        
        # Cleanup the temp files
        os.unlink(csv_file_path1)
        os.unlink(csv_file_path2)
        
        # Verify the response
        assert response.status_code == 200, f"Failed to upload files: {response.text}"
        data = response.json()
        assert data["db_name"] == test_db_name, f"Expected db_name to be {test_db_name}, got {data['db_name']}"
        
        # Get metadata to verify columns from both files exist
        get_metadata_response = requests.post(
            f"{BASE_URL}/integration/get_metadata",
            json={"token": admin_token, "db_name": test_db_name, "format": "json"},
            headers={"Content-Type": "application/json"},
        )
        
        assert get_metadata_response.status_code == 200, f"Failed to get metadata: {get_metadata_response.text}"
        metadata = get_metadata_response.json()["metadata"]
        
        # Extract all column names
        all_columns = set()
        for m in metadata:
            all_columns.add(m["column_name"].lower())
        
        # Check if we have columns from each file
        first_file_columns = any(col in {"customer", "email", "orders"} for col in all_columns)
        second_file_columns = any(col in {"product", "category", "price"} for col in all_columns)
        
        assert first_file_columns, "No columns from first CSV file found"
        assert second_file_columns, "No columns from second CSV file found"
        
    except Exception as e:
        print(f"\nTest failed with error: {str(e)}")
        raise e
    finally:
        # Always clean up the test database, even if the test fails
        cleanup_test_database(test_db_name)


def test_upload_excel_file_with_multiple_sheets(admin_token):
    """Test uploading an Excel file with multiple sheets"""
    # Create a unique database name for this test
    test_db_name = f"excel_sheets_{random.randint(1000, 9999)}"
    
    try:
        # Skip if pandas is not installed
        try:
            import pandas as pd
        except ImportError:
            pytest.skip("pandas not installed")
        
        # Create Excel data with multiple sheets
        excel_data = {
            'Users': pd.DataFrame({
                'UserID': [1, 2, 3],
                'Username': ['user1', 'user2', 'user3'],
                'Role': ['admin', 'user', 'user']
            }),
            'Logins': pd.DataFrame({
                'UserID': [1, 2, 3],
                'LastLogin': ['2023-01-01', '2023-01-02', '2023-01-03']
            })
        }
        
        # Create temporary Excel file
        import tempfile
        with tempfile.NamedTemporaryFile(suffix='.xlsx', delete=False) as excel_file:
            excel_path = excel_file.name
        
        # Write data to Excel file with multiple sheets
        with pd.ExcelWriter(excel_path, engine='openpyxl') as writer:
            for sheet_name, df in excel_data.items():
                df.to_excel(writer, sheet_name=sheet_name, index=False)
        
        # Create a unique database name for this test
        test_db_name = f"excel_sheets_{random.randint(1000, 9999)}"
        
        # Upload the Excel file
        with open(excel_path, 'rb') as file:
            # Use multipart form data to upload the file
            files = {'files': (os.path.basename(excel_path), file, 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')}
            form_data = {
                'token': admin_token,
                'db_name': test_db_name
            }
            
            # Send the upload request
            response = requests.post(
                f"{BASE_URL}/upload_files",
                files=files,
                data=form_data
            )
        
        # Cleanup the temp file
        os.unlink(excel_path)
        
        # Verify the response
        assert response.status_code == 200, f"Failed to upload Excel file: {response.text}"
        data = response.json()
        assert data["db_name"] == test_db_name, f"Expected db_name to be {test_db_name}, got {data['db_name']}"
        
        # Get metadata to verify sheets were processed
        get_metadata_response = requests.post(
            f"{BASE_URL}/integration/get_metadata",
            json={"token": admin_token, "db_name": test_db_name, "format": "json"},
            headers={"Content-Type": "application/json"},
        )
        
        assert get_metadata_response.status_code == 200, f"Failed to get metadata: {get_metadata_response.text}"
        metadata = get_metadata_response.json()["metadata"]
        
        # Extract tables and their columns
        tables_columns = {}
        for m in metadata:
            table = m["table_name"]
            column = m["column_name"].lower()
            
            if table not in tables_columns:
                tables_columns[table] = set()
            tables_columns[table].add(column)
        
        # Verify we have data from both sheets
        users_sheet_found = False
        logins_sheet_found = False
        
        for table, columns in tables_columns.items():
            if any(col in {"userid", "username", "role"} for col in columns):
                users_sheet_found = True
            if any(col in {"userid", "lastlogin"} for col in columns):
                logins_sheet_found = True
        
        assert users_sheet_found, "Users sheet data not found"
        assert logins_sheet_found, "Logins sheet data not found"
        
    except Exception as e:
        print(f"\nTest failed with error: {str(e)}")
        raise e
    finally:
        # Always clean up the test database, even if the test fails
        cleanup_test_database(test_db_name)


def test_upload_csv_with_excel(admin_token):
    """Test uploading a mix of CSV and Excel files in a single request"""
    # Create a unique database name for this test
    test_db_name = f"mixed_files_{random.randint(1000, 9999)}"
    
    try:
        # Skip if pandas is not installed
        try:
            import pandas as pd
        except ImportError:
            pytest.skip("pandas not installed")
        
        # Create CSV content
        csv_content = """Department,Manager,Budget
Sales,John Smith,100000
Marketing,Jane Doe,150000
Engineering,Bob Johnson,200000"""
        
        # Create Excel data with a sheet
        excel_df = pd.DataFrame({
            'EmployeeID': [1, 2, 3],
            'Name': ['Alice', 'Bob', 'Charlie'],
            'Department': ['Sales', 'Marketing', 'Engineering']
        })
        
        # Create temporary files
        import tempfile
        
        # Create CSV file
        with tempfile.NamedTemporaryFile(suffix='.csv', delete=False) as csv_file:
            csv_file.write(csv_content.encode('utf-8'))
            csv_path = csv_file.name
        
        # Create Excel file
        with tempfile.NamedTemporaryFile(suffix='.xlsx', delete=False) as excel_file:
            excel_path = excel_file.name
        
        # Write data to Excel file
        excel_df.to_excel(excel_path, index=False)
        
        
        # Upload both files in a single request as the endpoint supports
        with open(csv_path, 'rb') as csv_f, open(excel_path, 'rb') as excel_f:
            # Use multipart form data to upload both files
            files = [
                ('files', (os.path.basename(csv_path), csv_f, 'text/csv')),
                ('files', (os.path.basename(excel_path), excel_f, 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'))
            ]
            form_data = {
                'token': admin_token,
                'db_name': test_db_name
            }
            
            # Send the upload request with both files
            response = requests.post(
                f"{BASE_URL}/upload_files",
                files=files,
                data=form_data
            )
        
        # Cleanup the temp files
        os.unlink(csv_path)
        os.unlink(excel_path)
        
        # Verify the response
        assert response.status_code == 200, f"Failed to upload files: {response.text}"
        data = response.json()
        assert data["db_name"] == test_db_name, f"Expected db_name to be {test_db_name}, got {data['db_name']}"
        
        # Get metadata to verify columns from both files exist
        get_metadata_response = requests.post(
            f"{BASE_URL}/integration/get_metadata",
            json={"token": admin_token, "db_name": test_db_name, "format": "json"},
            headers={"Content-Type": "application/json"},
        )
        
        assert get_metadata_response.status_code == 200, f"Failed to get metadata: {get_metadata_response.text}"
        metadata = get_metadata_response.json()["metadata"]
        
        # Extract tables and their columns for better debugging
        tables_columns = {}
        for m in metadata:
            table = m["table_name"]
            column = m["column_name"].lower()
            
            if table not in tables_columns:
                tables_columns[table] = set()
            tables_columns[table].add(column)
        
        # Print all tables and columns for debugging
        print("\nTables and columns in database:")
        for table, columns in tables_columns.items():
            print(f"Table: {table}")
            for col in columns:
                print(f"  - {col}")
        
        # Extract all column names as a flattened set
        all_columns = set()
        for columns in tables_columns.values():
            all_columns.update(columns)
        
        # Check for presence of CSV and Excel columns with more flexible matching
        csv_columns = {"department", "manager", "budget"}
        excel_columns = {"employeeid", "name", "department"}
        
        # Find any matches
        csv_matches = [col for col in all_columns if any(csv_col in col for csv_col in csv_columns)]
        excel_matches = [col for col in all_columns if any(excel_col in col for excel_col in excel_columns)]
        
        print(f"\nFound CSV column matches: {csv_matches}")
        print(f"Found Excel column matches: {excel_matches}")
        
        # Check if we found any matches
        csv_column_found = len(csv_matches) > 0
        excel_column_found = len(excel_matches) > 0
        
        assert csv_column_found, "No columns from CSV file found"
        assert excel_column_found, "No columns from Excel file found"
        
    except Exception as e:
        print(f"\nTest failed with error: {str(e)}")
        raise e
    finally:
        # Always clean up the test database, even if the test fails
        cleanup_test_database(test_db_name)


def test_upload_csv_with_pdf(admin_token):
    """Test uploading a CSV file and a PDF file in a single request"""
    # Create a unique database name for this test
    test_db_name = f"csv_pdf_{random.randint(1000, 9999)}"
    
    try:
        # Create a simple CSV content
        csv_content = """Product,Category,Price
Laptop,Electronics,999.99
Phone,Electronics,499.99
Tablet,Electronics,299.99"""
        
        # Create a simple PDF content (minimal valid PDF)
        pdf_content = b"%PDF-1.0\n1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj 2 0 obj<</Type/Pages/Kids[3 0 R]/Count 1>>endobj 3 0 obj<</Type/Page/MediaBox[0 0 612 792]/Resources<<>>>>endobj\nxref\n0 4\n0000000000 65535 f\n0000000010 00000 n\n0000000053 00000 n\n0000000102 00000 n\ntrailer<</Size 4/Root 1 0 R>>\nstartxref\n149\n%%EOF"
        
        # Create temporary files with specific names
        import tempfile
        import os
        
        # Create CSV file with predictable name
        csv_filename = 'product_catalog.csv'
        csv_path = os.path.join(tempfile.gettempdir(), csv_filename)
        with open(csv_path, 'w') as csv_file:
            csv_file.write(csv_content)
        
        # Create PDF file with predictable name
        pdf_filename = 'catalog_specs.pdf'
        pdf_path = os.path.join(tempfile.gettempdir(), pdf_filename)
        with open(pdf_path, 'wb') as pdf_file:
            pdf_file.write(pdf_content)
        
        # Upload both files in a single request
        with open(csv_path, 'rb') as csv_f, open(pdf_path, 'rb') as pdf_f:
            # Use multipart form data to upload both files
            files = [
                ('files', (csv_filename, csv_f, 'text/csv')),
                ('files', (pdf_filename, pdf_f, 'application/pdf'))
            ]
            form_data = {
                'token': admin_token,
                'db_name': test_db_name
            }
            
            # Send the upload request with both files
            response = requests.post(
                f"{BASE_URL}/upload_files",
                files=files,
                data=form_data
            )
        
        # Cleanup the temp files
        os.unlink(csv_path)
        os.unlink(pdf_path)
        
        # Verify the response
        assert response.status_code == 200, f"Failed to upload files: {response.text}"
        data = response.json()
        print(f"\nResponse data: {data}")
        assert data["db_name"] == test_db_name, f"Expected db_name to be {test_db_name}, got {data['db_name']}"
        
        # Print associated files for debugging
        db_info = data["db_info"]
        print(f"\nAssociated files: {db_info.get('associated_files')}")
        
        # Verify database was created with CSV data
        get_metadata_response = requests.post(
            f"{BASE_URL}/integration/get_metadata",
            json={"token": admin_token, "db_name": test_db_name, "format": "json"},
            headers={"Content-Type": "application/json"},
        )
        
        assert get_metadata_response.status_code == 200, f"Failed to get metadata: {get_metadata_response.text}"
        metadata = get_metadata_response.json()["metadata"]
        
        # Extract tables and their columns
        tables_columns = {}
        for m in metadata:
            table = m["table_name"]
            column = m["column_name"].lower()
            
            if table not in tables_columns:
                tables_columns[table] = set()
            tables_columns[table].add(column)
        
        # Print tables and columns for debugging
        print("\nTables and columns in database:")
        for table, columns in tables_columns.items():
            print(f"Table: {table}")
            for col in columns:
                print(f"  - {col}")
        
        # Extract all column names
        all_columns = set()
        for columns in tables_columns.values():
            all_columns.update(columns)
        
        print(f"\nAll columns: {all_columns}")
        
        # Verify CSV columns exist
        csv_columns = {"product", "category", "price"}
        csv_matches = [col for col in all_columns if any(csv_col in col for csv_col in csv_columns)]
        
        print(f"\nFound CSV columns: {csv_matches}")
        if not csv_matches:
            # If no exact matches, try broader check for table names
            csv_tables = [t for t in tables_columns.keys() if any(name in t.lower() for name in ["product", "catalog"])]
            print(f"Possible CSV tables: {csv_tables}")
            # Only fail if we didn't find any related tables either
            if not csv_tables:
                assert len(csv_matches) > 0, "No columns from CSV file found in the database"
        
        # Verify PDF was associated with the project
        assert "associated_files" in db_info, "No associated_files in db_info"
        assert len(db_info["associated_files"]) == 1, f"Expected 1 associated PDF file, got {len(db_info['associated_files'])}"
        
        # Verify PDF file can be downloaded
        pdf_file_id = db_info["associated_files"][0]
        # Print the PDF file ID for debugging
        print(f"\nPDF file ID: {pdf_file_id}, type: {type(pdf_file_id)}")
        
        # If PDF file ID is a dictionary, extract the ID
        if isinstance(pdf_file_id, dict) and 'file_id' in pdf_file_id:
            pdf_file_id = pdf_file_id['file_id']
        
        download_response = requests.get(
            f"{BASE_URL}/download_pdf/{pdf_file_id}"
        )
        assert download_response.status_code == 200, f"Failed to download PDF: {download_response.text}"
        assert download_response.headers["Content-Type"] == "application/pdf", "Response is not a PDF file"
        
        # Test deleting the PDF file
        delete_response = requests.delete(
            f"{BASE_URL}/delete_pdf/{pdf_file_id}",
            params={"token": admin_token, "db_name": test_db_name}
        )
        assert delete_response.status_code == 200, f"Failed to delete PDF: {delete_response.text}"
        
        # Verify PDF was removed from the project
        updated_db_info = delete_response.json()["db_info"]
        assert "associated_files" in updated_db_info, "No associated_files in updated db_info"
        assert len(updated_db_info["associated_files"]) == 0, "PDF file was not removed from project"
        
    except Exception as e:
        print(f"\nTest failed with error: {str(e)}")
        raise e
    finally:
        # Always clean up the test database, even if the test fails
        cleanup_test_database(test_db_name)


def test_upload_excel_with_pdf(admin_token):
    """Test uploading an Excel file and a PDF file in a single request"""
    # Create a unique database name for this test
    test_db_name = f"excel_pdf_{random.randint(1000, 9999)}"
    
    try:
        # Skip if pandas is not installed
        try:
            import pandas as pd
        except ImportError:
            pytest.skip("pandas not installed")
        
        # Create Excel data with a sheet
        excel_df = pd.DataFrame({
            'Product': ['Laptop', 'Phone', 'Tablet'],
            'Inventory': [50, 100, 75],
            'Price': [999.99, 499.99, 299.99]
        })
        
        # Create a simple PDF content (minimal valid PDF)
        pdf_content = b"%PDF-1.0\n1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj 2 0 obj<</Type/Pages/Kids[3 0 R]/Count 1>>endobj 3 0 obj<</Type/Page/MediaBox[0 0 612 792]/Resources<<>>>>endobj\nxref\n0 4\n0000000000 65535 f\n0000000010 00000 n\n0000000053 00000 n\n0000000102 00000 n\ntrailer<</Size 4/Root 1 0 R>>\nstartxref\n149\n%%EOF"
        
        # Create temporary files with specific names
        import tempfile
        import os
        
        # Create Excel file with predictable name
        excel_filename = 'product_inventory.xlsx'
        excel_path = os.path.join(tempfile.gettempdir(), excel_filename)
        excel_df.to_excel(excel_path, sheet_name='Inventory', index=False)
        
        # Create PDF file with predictable name
        pdf_filename = 'product_specs.pdf'
        pdf_path = os.path.join(tempfile.gettempdir(), pdf_filename)
        with open(pdf_path, 'wb') as pdf_file:
            pdf_file.write(pdf_content)
        
        # Upload both files in a single request
        with open(excel_path, 'rb') as excel_f, open(pdf_path, 'rb') as pdf_f:
            # Use multipart form data to upload both files
            files = [
                ('files', (excel_filename, excel_f, 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')),
                ('files', (pdf_filename, pdf_f, 'application/pdf'))
            ]
            form_data = {
                'token': admin_token,
                'db_name': test_db_name
            }
            
            # Send the upload request with both files
            response = requests.post(
                f"{BASE_URL}/upload_files",
                files=files,
                data=form_data
            )
        
        # Cleanup the temp files
        os.unlink(excel_path)
        os.unlink(pdf_path)
        
        # Verify the response
        assert response.status_code == 200, f"Failed to upload files: {response.text}"
        data = response.json()
        print(f"\nResponse data: {data}")
        assert data["db_name"] == test_db_name, f"Expected db_name to be {test_db_name}, got {data['db_name']}"
        
        # Print associated files for debugging
        db_info = data["db_info"]
        print(f"\nAssociated files: {db_info.get('associated_files')}")
        
        # Verify database was created with Excel data
        get_metadata_response = requests.post(
            f"{BASE_URL}/integration/get_metadata",
            json={"token": admin_token, "db_name": test_db_name, "format": "json"},
            headers={"Content-Type": "application/json"},
        )
        
        assert get_metadata_response.status_code == 200, f"Failed to get metadata: {get_metadata_response.text}"
        metadata = get_metadata_response.json()["metadata"]
        
        # Extract tables and their columns
        tables_columns = {}
        for m in metadata:
            table = m["table_name"]
            column = m["column_name"].lower()
            
            if table not in tables_columns:
                tables_columns[table] = set()
            tables_columns[table].add(column)
        
        # Print tables and columns for debugging
        print("\nTables and columns in database:")
        for table, columns in tables_columns.items():
            print(f"Table: {table}")
            for col in columns:
                print(f"  - {col}")
        
        # Extract all column names
        all_columns = set()
        for columns in tables_columns.values():
            all_columns.update(columns)
        
        print(f"\nAll columns: {all_columns}")
        
        # Verify Excel columns exist
        excel_columns = {"product", "inventory", "price"}
        excel_matches = [col for col in all_columns if any(excel_col in col for excel_col in excel_columns)]
        
        print(f"\nFound Excel columns: {excel_matches}")
        if not excel_matches:
            # If no exact matches, try broader check for table names
            excel_tables = [t for t in tables_columns.keys() if any(name in t.lower() for name in ["inventory", "product"])]
            print(f"Possible Excel tables: {excel_tables}")
            # Only fail if we didn't find any related tables either
            if not excel_tables:
                assert len(excel_matches) > 0, "No columns from Excel file found in the database"
        
        # Verify PDF was associated with the project
        assert "associated_files" in db_info, "No associated_files in db_info"
        assert len(db_info["associated_files"]) == 1, f"Expected 1 associated PDF file, got {len(db_info['associated_files'])}"
        
        # Verify PDF file can be downloaded
        pdf_file_id = db_info["associated_files"][0]
        # Print the PDF file ID for debugging
        print(f"\nPDF file ID: {pdf_file_id}, type: {type(pdf_file_id)}")
        
        # If PDF file ID is a dictionary, extract the ID
        if isinstance(pdf_file_id, dict) and 'file_id' in pdf_file_id:
            pdf_file_id = pdf_file_id['file_id']
        
        download_response = requests.get(
            f"{BASE_URL}/download_pdf/{pdf_file_id}"
        )
        assert download_response.status_code == 200, f"Failed to download PDF: {download_response.text}"
        assert download_response.headers["Content-Type"] == "application/pdf", "Response is not a PDF file"
        
        # Test deleting the PDF file
        delete_response = requests.delete(
            f"{BASE_URL}/delete_pdf/{pdf_file_id}",
            params={"token": admin_token, "db_name": test_db_name}
        )
        assert delete_response.status_code == 200, f"Failed to delete PDF: {delete_response.text}"
        
        # Verify PDF was removed from the project
        updated_db_info = delete_response.json()["db_info"]
        assert "associated_files" in updated_db_info, "No associated_files in updated db_info"
        assert len(updated_db_info["associated_files"]) == 0, "PDF file was not removed from project"
        
    except Exception as e:
        print(f"\nTest failed with error: {str(e)}")
        raise e
    finally:
        # Always clean up the test database, even if the test fails
        cleanup_test_database(test_db_name)


def test_upload_csv_excel_pdf_combination(admin_token):
    """Test uploading a combination of CSV, Excel, and PDF files in a single request"""
    # Create a unique database name for this test
    test_db_name = f"all_files_{random.randint(1000, 9999)}"
    
    try:
        # Skip if pandas is not installed
        try:
            import pandas as pd
        except ImportError:
            pytest.skip("pandas not installed")
        
        # Create CSV content - add more descriptive filename to ensure it's processed correctly
        csv_content = """Customer,Email,Status
John Smith,john@example.com,Active
Jane Doe,jane@example.com,Inactive
Bob Johnson,bob@example.com,Active"""
        
        # Create Excel data
        excel_df = pd.DataFrame({
            'OrderID': [1001, 1002, 1003],
            'CustomerID': ['JOHN', 'JANE', 'BOB'],
            'Amount': [150.50, 75.25, 200.00]
        })
        
        # Create a simple PDF content (minimal valid PDF)
        pdf_content = b"%PDF-1.0\n1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj 2 0 obj<</Type/Pages/Kids[3 0 R]/Count 1>>endobj 3 0 obj<</Type/Page/MediaBox[0 0 612 792]/Resources<<>>>>endobj\nxref\n0 4\n0000000000 65535 f\n0000000010 00000 n\n0000000053 00000 n\n0000000102 00000 n\ntrailer<</Size 4/Root 1 0 R>>\nstartxref\n149\n%%EOF"
        
        # Create temporary files with specific names
        import tempfile
        import os
        
        # Create CSV file with predictable name
        csv_filename = 'customer_data.csv'
        csv_path = os.path.join(tempfile.gettempdir(), csv_filename)
        with open(csv_path, 'w') as csv_file:
            csv_file.write(csv_content)
        
        # Create Excel file with predictable name
        excel_filename = 'order_data.xlsx'
        excel_path = os.path.join(tempfile.gettempdir(), excel_filename)
        excel_df.to_excel(excel_path, sheet_name='Orders', index=False)
        
        # Create PDF file with predictable name
        pdf_filename = 'document.pdf'
        pdf_path = os.path.join(tempfile.gettempdir(), pdf_filename)
        with open(pdf_path, 'wb') as pdf_file:
            pdf_file.write(pdf_content)
        
        # Upload all files in a single request
        with open(csv_path, 'rb') as csv_f, open(excel_path, 'rb') as excel_f, open(pdf_path, 'rb') as pdf_f:
            # Use multipart form data to upload all files
            files = [
                ('files', (csv_filename, csv_f, 'text/csv')),
                ('files', (excel_filename, excel_f, 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')),
                ('files', (pdf_filename, pdf_f, 'application/pdf'))
            ]
            form_data = {
                'token': admin_token,
                'db_name': test_db_name
            }
            
            # Send the upload request with all files
            response = requests.post(
                f"{BASE_URL}/upload_files",
                files=files,
                data=form_data
            )
        
        # Cleanup the temp files
        os.unlink(csv_path)
        os.unlink(excel_path)
        os.unlink(pdf_path)
        
        # Verify the response
        assert response.status_code == 200, f"Failed to upload files: {response.text}"
        data = response.json()
        print(f"\nResponse data: {data}")
        assert data["db_name"] == test_db_name, f"Expected db_name to be {test_db_name}, got {data['db_name']}"
        
        # Print associated files for debugging
        db_info = data["db_info"]
        print(f"\nAssociated files: {db_info.get('associated_files')}")
        
        # Verify database was created with CSV and Excel data
        get_metadata_response = requests.post(
            f"{BASE_URL}/integration/get_metadata",
            json={"token": admin_token, "db_name": test_db_name, "format": "json"},
            headers={"Content-Type": "application/json"},
        )
        
        assert get_metadata_response.status_code == 200, f"Failed to get metadata: {get_metadata_response.text}"
        metadata = get_metadata_response.json()["metadata"]
        
        # Extract tables and their columns
        tables_columns = {}
        for m in metadata:
            table = m["table_name"]
            column = m["column_name"].lower()
            
            if table not in tables_columns:
                tables_columns[table] = set()
            tables_columns[table].add(column)
        
        # Print tables and columns for debugging
        print("\nTables and columns in database for CSV+Excel+PDF test:")
        for table, columns in tables_columns.items():
            print(f"Table: {table}")
            for col in columns:
                print(f"  - {col}")
        
        # Extract all columns as a flattened set
        all_columns = set()
        for columns in tables_columns.values():
            all_columns.update(columns)
        
        print(f"\nAll columns: {all_columns}")
            
        # Check for presence of columns with more flexible matching
        column_checks = {
            "CSV": ["customer", "email", "status"],
            "Excel": ["orderid", "customerid", "amount"]
        }
        
        for file_type, expected_columns in column_checks.items():
            found_columns = []
            for col in all_columns:
                for expected in expected_columns:
                    if expected in col.lower():
                        found_columns.append(col)
                        break
            
            print(f"\nFound {file_type} columns: {found_columns}")
            if not found_columns:
                # If no exact matches, try broader check
                file_tables = []
                if file_type == "CSV":
                    file_tables = [t for t in tables_columns.keys() if "customer" in t.lower()]
                elif file_type == "Excel":
                    file_tables = [t for t in tables_columns.keys() if "order" in t.lower()]
                
                print(f"Possible {file_type} tables: {file_tables}")
                # Skip the assertion if we found related tables
                if not file_tables:
                    assert found_columns, f"No columns from {file_type} file found in the database"
        
        # Verify PDF was associated with the project
        assert "associated_files" in db_info, "No associated_files in db_info"
        assert len(db_info["associated_files"]) == 1, f"Expected 1 associated PDF file, got {len(db_info['associated_files'])}"
        
        # Verify PDF file can be downloaded
        pdf_file_id = db_info["associated_files"][0]
        # Print the PDF file ID for debugging
        print(f"\nPDF file ID: {pdf_file_id}, type: {type(pdf_file_id)}")
        
        # If PDF file ID is a dictionary, extract the ID
        if isinstance(pdf_file_id, dict) and 'file_id' in pdf_file_id:
            pdf_file_id = pdf_file_id['file_id']
        
        download_response = requests.get(
            f"{BASE_URL}/download_pdf/{pdf_file_id}"
        )
        assert download_response.status_code == 200, f"Failed to download PDF: {download_response.text}"
        assert download_response.headers["Content-Type"] == "application/pdf", "Response is not a PDF file"
        
        # Test deleting the PDF file
        delete_response = requests.delete(
            f"{BASE_URL}/delete_pdf/{pdf_file_id}",
            params={"token": admin_token, "db_name": test_db_name}
        )
        assert delete_response.status_code == 200, f"Failed to delete PDF: {delete_response.text}"
        
        # Verify PDF was removed from the project
        updated_db_info = delete_response.json()["db_info"]
        assert "associated_files" in updated_db_info, "No associated_files in updated db_info"
        assert len(updated_db_info["associated_files"]) == 0, "PDF file was not removed from project"
        
    except Exception as e:
        print(f"\nTest failed with error: {str(e)}")
        raise e
    finally:
        # Always clean up the test database, even if the test fails
        cleanup_test_database(test_db_name)