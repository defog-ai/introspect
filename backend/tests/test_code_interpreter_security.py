"""Tests for the code_interpreter_tool security enhancements."""

import pytest
import asyncio
import json
import sys
import os
import pandas as pd

# Import directly from the backend
from tools.analysis_tools import execute_analysis_code_safely

@pytest.mark.asyncio
async def test_file_system_access_restriction():
    """
    Test that execute_analysis_code_safely properly restricts file system access
    to only the /tmp directory as specified.
    """
    # PoC exploit attempt - try to read /etc/passwd
    malicious_code = """
import pandas as pd
try:
    data = pd.read_csv('/etc/passwd', sep=':', header=None)
    final_result = f"SUCCESS: Was able to read {len(data)} lines from /etc/passwd"
except Exception as e:
    final_result = f"Error: {str(e)}"
"""
    
    # Execute the code in the secured environment
    result_text, error_message = await execute_analysis_code_safely(malicious_code, "[]")
    
    print(result_text)
    print(error_message)

    # Verify the code was prevented from accessing the sensitive file
    # The test now checks that we don't see "SUCCESS" which would indicate the exploit worked
    assert "SUCCESS" not in result_text, \
        "Security bypass - code was able to read sensitive file"
    assert "not permitted" in error_message, \
        "Should return an error when accessing unauthorized paths"

@pytest.mark.asyncio
async def test_tmp_directory_access_allowed():
    """
    Test that execute_analysis_code_safely allows file system access
    to the /tmp directory as expected.
    """
    # Create a test file in /tmp
    test_data = {'A': [1, 2, 3], 'B': [4, 5, 6]}
    test_df = pd.DataFrame(test_data)
    tmp_file = '/tmp/test_secure_access.csv'
    test_df.to_csv(tmp_file, index=False)
    
    # Code that tries to access the file in /tmp
    allowed_code = """
import pandas as pd
try:
    # This should be allowed since it's in /tmp
    data = pd.read_csv('/tmp/test_secure_access.csv')
    final_result = f"Success! Data read from /tmp: {data.shape[0]} rows, {data.shape[1]} columns"
except Exception as e:
    final_result = f"Error: {str(e)}"
"""
    
    try:
        # Execute the code in the secured environment
        result_text, error_message = await execute_analysis_code_safely(allowed_code, "[]")

        print(result_text)
        print(error_message)
        
        # Verify the code was allowed to access the file in /tmp
        assert "Success" in result_text, \
            "Access to /tmp should be allowed but was blocked"
        assert "3 rows" in result_text, \
            "Test data should be correctly read from the file"
    finally:
        # Clean up
        try:
            os.remove(tmp_file)
        except:
            pass

@pytest.mark.asyncio
async def test_normal_analysis_still_works():
    """
    Test that execute_analysis_code_safely still allows legitimate analysis
    code to run correctly.
    """
    # Normal analysis code
    analysis_code = """
import pandas as pd
import numpy as np

# Create a sample DataFrame
data = {'A': np.random.rand(100), 
        'B': np.random.rand(100),
        'C': np.random.randint(0, 5, 100)}
df = pd.DataFrame(data)

# Perform some analysis
stats = df.describe()
correlation = df.corr()

# Format the result
final_result = f"Statistics:\\n{stats}\\n\\nCorrelation:\\n{correlation}"
"""
    
    # Execute the code in the secured environment
    result_text, error_message = await execute_analysis_code_safely(analysis_code, "[]")
    
    # Verify the analysis ran successfully
    assert "Statistics" in result_text, \
        "Legitimate analysis code should run successfully"
    assert "Correlation" in result_text, \
        "Legitimate analysis code should produce expected output"
    assert error_message == "", \
        "No errors should be reported for legitimate code"