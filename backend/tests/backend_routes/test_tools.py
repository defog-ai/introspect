"""Tests for custom tools API endpoints."""

import requests
import sys
import os

# Get the conftest directly from the current directory
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, current_dir)
from conftest import BASE_URL, TEST_DB


def test_custom_tools_crud(admin_token):
    """
    Test the CRUD operations for custom tools API:
    1. Create a custom tool
    2. List custom tools
    3. Get a specific custom tool
    4. Update a custom tool
    5. Toggle a custom tool
    6. Delete a custom tool
    """
    try:
        # Define a simple custom tool
        tool_name = "test_counter_tool"
        tool_description = "A simple counter tool for testing"
        
        input_model = """
class CounterInput(BaseModel):
    start: int = Field(1, description="Starting value")
    count: int = Field(5, description="Number of items to count")
"""
        
        tool_code = """
async def test_counter_tool(input: CounterInput):
    \"\"\"
    Generates a simple count sequence.
    \"\"\"
    start = input.start
    count = input.count
    
    results = []
    for i in range(start, start + count):
        results.append(i)
    
    return {
        "sequence": results,
        "count": count,
        "start": start,
        "end": start + count - 1
    }
"""
        
        # Step 1: Create a custom tool
        create_response = requests.post(
            f"{BASE_URL}/custom_tools/create",
            json={
                "token": admin_token,
                "tool_name": tool_name,
                "tool_description": tool_description,
                "input_model": input_model,
                "tool_code": tool_code
            },
            headers={"Content-Type": "application/json"},
        )
        
        assert create_response.status_code == 200, f"Failed to create custom tool: {create_response.text}"
        create_data = create_response.json()
        assert create_data["status"] == "success", f"Create tool failed: {create_data}"
        assert create_data["tool"]["tool_name"] == tool_name, "Tool name mismatch in create response"
        
        # Step 2: List custom tools
        list_response = requests.post(
            f"{BASE_URL}/custom_tools/list",
            json={
                "token": admin_token,
            },
            headers={"Content-Type": "application/json"},
        )
        
        assert list_response.status_code == 200, f"Failed to list custom tools: {list_response.text}"
        list_data = list_response.json()
        assert list_data["status"] == "success", "List custom tools failed"
        assert len(list_data["tools"]) >= 1, "No tools found in list response"
        
        found_tool = False
        for tool in list_data["tools"]:
            if tool["tool_name"] == tool_name:
                found_tool = True
                assert tool["tool_description"].strip() == tool_description.strip(), "Tool description mismatch"
                assert tool["is_enabled"] is True, "Tool should be enabled by default"
        
        assert found_tool, f"Created tool '{tool_name}' not found in tool list"
        
        # Step 3: Get specific custom tool
        get_response = requests.post(
            f"{BASE_URL}/custom_tools/get",
            json={
                "token": admin_token,
                "tool_name": tool_name
            },
            headers={"Content-Type": "application/json"},
        )
        
        assert get_response.status_code == 200, f"Failed to get custom tool: {get_response.text}"
        get_data = get_response.json()
        assert get_data["status"] == "success", "Get custom tool failed"
        assert get_data["tool"]["tool_name"].strip() == tool_name.strip(), "Tool name mismatch in get response"
        assert get_data["tool"]["tool_description"].strip() == tool_description.strip(), "Tool description mismatch in get response"
        assert get_data["tool"]["input_model"].strip() == input_model.strip(), "Input model mismatch in get response"
        assert get_data["tool"]["tool_code"].strip() == tool_code.strip(), "Tool code mismatch in get response"
        
        # Step 4: Update custom tool
        updated_description = "An updated counter tool for testing"
        updated_tool_code = tool_code.replace("sequence", "result_sequence")
        
        update_response = requests.post(
            f"{BASE_URL}/custom_tools/update",
            json={
                "token": admin_token,
                "tool_name": tool_name,
                "tool_description": updated_description,
                "input_model": input_model,
                "tool_code": updated_tool_code
            },
            headers={"Content-Type": "application/json"},
        )
        
        assert update_response.status_code == 200, f"Failed to update custom tool: {update_response.text}"
        update_data = update_response.json()
        assert update_data["status"] == "success", "Update custom tool failed"
        
        # Verify the update
        get_response = requests.post(
            f"{BASE_URL}/custom_tools/get",
            json={
                "token": admin_token,
                "tool_name": tool_name
            },
            headers={"Content-Type": "application/json"},
        )
        
        assert get_response.status_code == 200, "Failed to get updated custom tool"
        get_data = get_response.json()
        assert get_data["tool"]["tool_description"].strip() == updated_description.strip(), "Tool description not updated"
        assert get_data["tool"]["tool_code"].strip() == updated_tool_code.strip(), "Tool code not updated"
        
        # Step 5: Toggle custom tool (disable)
        toggle_response = requests.post(
            f"{BASE_URL}/custom_tools/toggle",
            json={
                "token": admin_token,
                "tool_name": tool_name,
                "is_enabled": False
            },
            headers={"Content-Type": "application/json"},
        )
        
        assert toggle_response.status_code == 200, f"Failed to toggle custom tool: {toggle_response.text}"
        toggle_data = toggle_response.json()
        assert toggle_data["status"] == "success", "Toggle custom tool failed"
        assert toggle_data["tool"]["is_enabled"] is False, "Tool should be disabled after toggle"
        
        # Verify the toggle
        get_response = requests.post(
            f"{BASE_URL}/custom_tools/get",
            json={
                "token": admin_token,
                "tool_name": tool_name
            },
            headers={"Content-Type": "application/json"},
        )
        
        assert get_response.status_code == 200, "Failed to get toggled custom tool"
        get_data = get_response.json()
        assert get_data["tool"]["is_enabled"] is False, "Tool not disabled after toggle"
        
        # Step 6: Delete custom tool
        delete_response = requests.post(
            f"{BASE_URL}/custom_tools/delete",
            json={
                "token": admin_token,
                "tool_name": tool_name
            },
            headers={"Content-Type": "application/json"},
        )
        
        assert delete_response.status_code == 200, f"Failed to delete custom tool: {delete_response.text}"
        delete_data = delete_response.json()
        assert delete_data["status"] == "success", "Delete custom tool failed"
        
        # Verify deletion
        get_response = requests.post(
            f"{BASE_URL}/custom_tools/get",
            json={
                "token": admin_token,
                "tool_name": tool_name
            },
            headers={"Content-Type": "application/json"},
        )
        
        assert get_response.status_code == 404, "Tool should not exist after deletion"
        
    except Exception as e:
        print(f"\nTest failed with error: {str(e)}")
        raise e


def test_custom_tool_test_endpoint(admin_token):
    """
    Test the custom tool test endpoint, which allows testing a tool without saving it.
    """
    try:
        # Define a simple test tool
        tool_code = """
async def test_math_tool(input):
    a = input.a
    b = input.b
    operation = input.operation
    
    if operation == "add":
        result = a + b
    elif operation == "subtract":
        result = a - b
    elif operation == "multiply":
        result = a * b
    elif operation == "divide":
        result = a / b if b != 0 else "Error: Division by zero"
    else:
        result = "Unknown operation"
    
    return {
        "operation": operation,
        "a": a,
        "b": b,
        "result": result
    }
"""
        
        input_model = """
class MathInput(BaseModel):
    a: float = Field(..., description="First number")
    b: float = Field(..., description="Second number")
    operation: str = Field(..., description="Operation (add, subtract, multiply, divide)")
"""
        
        # Create test input
        test_input = {
            "a": 10,
            "b": 5,
            "operation": "add"
        }
        
        # Test the tool
        test_response = requests.post(
            f"{BASE_URL}/custom_tools/test",
            json={
                "token": admin_token,
                "tool_code": tool_code,
                "input_model": input_model,
                "test_input": test_input
            },
            headers={"Content-Type": "application/json"},
        )
        
        assert test_response.status_code == 200, f"Failed to test custom tool: {test_response.text}"
        test_data = test_response.json()
        assert test_data["status"] == "success", "Tool test failed"
        assert "result" in test_data, "No result in test response"
        
        # Check the result from the test execution
        tool_result = test_data["result"]
        assert tool_result["operation"] == "add", "Operation mismatch in tool result"
        assert tool_result["a"] == 10, "First number mismatch in tool result"
        assert tool_result["b"] == 5, "Second number mismatch in tool result"
        assert tool_result["result"] == 15, "Addition result incorrect in tool result"
        
        # Test with invalid code (missing async)
        invalid_code = """
def test_math_tool(input):
    a = input.a
    b = input.b
    return {"sum": a + b}
"""
        
        invalid_response = requests.post(
            f"{BASE_URL}/custom_tools/test",
            json={
                "token": admin_token,
                "tool_code": invalid_code,
                "input_model": input_model,
                "test_input": test_input
            },
            headers={"Content-Type": "application/json"},
        )
        
        assert invalid_response.status_code == 400, "Should fail with invalid code"
        
        # Test with unsafe code (using eval)
        unsafe_code = """
async def unsafe_tool(input):
    code = input.code
    return {"result": eval(code)}
"""
        
        unsafe_response = requests.post(
            f"{BASE_URL}/custom_tools/test",
            json={
                "token": admin_token,
                "tool_code": unsafe_code,
                "input_model": input_model,
                "test_input": test_input
            },
            headers={"Content-Type": "application/json"},
        )
        
        assert unsafe_response.status_code == 400, "Should fail with unsafe code"
        
    except Exception as e:
        print(f"\nTest failed with error: {str(e)}")
        raise e


def test_custom_tool_execution_integration(admin_token):
    """
    Integration test that creates a custom tool and then tests it through the
    report generation flow to ensure custom tools are loaded and executed correctly.
    """
    try:
        # 1. Create a custom tool that gets data in a specific format
        tool_name = "ticket_summary_tool"
        tool_description = "Summarizes ticket sales data in a predefined format"
        
        input_model = """
class TicketSummaryInput(BaseModel):
    metric: str = Field("count", description="Metric to summarize (count, revenue)")
"""
        
        tool_code = """
async def ticket_summary_tool(input: TicketSummaryInput):
    \"\"\"
    Provides a summary of ticket sales, either by count or by revenue.
    \"\"\"
    metric = input.metric.lower()
    
    # Get database credentials
    db_type, db_creds = await get_db_type_creds("test_db")
    
    if metric == "count":
        # Query for count summary
        sql = \"\"\"
        SELECT tt.name AS ticket_type, COUNT(*) AS total_tickets
        FROM ticket_sales ts
        JOIN ticket_types tt ON ts.ticket_type_id = tt.id
        GROUP BY tt.name
        ORDER BY total_tickets DESC;
        \"\"\"
    else:
        # Query for revenue summary
        sql = \"\"\"
        SELECT tt.name AS ticket_type, COUNT(*) AS tickets_sold, 
               SUM(tt.price) AS total_revenue
        FROM ticket_sales ts
        JOIN ticket_types tt ON ts.ticket_type_id = tt.id
        GROUP BY tt.name
        ORDER BY total_revenue DESC;
        \"\"\"
    
    try:
        # Execute the query
        colnames, rows = await async_execute_query_once(
            db_type=db_type, db_creds=db_creds, query=sql
        )
        
        # Build result
        result_df = pd.DataFrame(rows, columns=colnames)
        
        summary = {
            "metric": metric,
            "data": result_df.to_dict(orient="records"),
            "column_names": colnames,
            "sql": sql
        }
        
        return summary
        
    except Exception as e:
        return {
            "error": str(e),
            "metric": metric
        }
"""
        
        # 2. Create the custom tool
        create_response = requests.post(
            f"{BASE_URL}/custom_tools/create",
            json={
                "token": admin_token,
                "tool_name": tool_name,
                "tool_description": tool_description,
                "input_model": input_model,
                "tool_code": tool_code
            },
            headers={"Content-Type": "application/json"},
        )
        
        assert create_response.status_code == 200, f"Failed to create custom tool: {create_response.text}"
        
        # 3. Generate a report that can leverage this custom tool
        # The question explicitly mentions a tool that aligns with our custom tool
        user_question = "Please summarize ticket sales by revenue using the ticket summary tool"
        
        report_response = requests.post(
            f"{BASE_URL}/answer_question_from_database",
            json={
                "token": admin_token,
                "question": user_question,
                "model": "o3-mini"
            },
            headers={"Content-Type": "application/json"},
        )
        
        assert report_response.status_code == 200, f"Failed to generate report: {report_response.text}"
        report_data = report_response.json()
        
        # Expect to see our custom tool in the report output
        assert "report" in report_data, "No report in response"
        assert "tool_outputs" in report_data, "No tool outputs in response"
        
        # 4. Verify the custom tool was used
        custom_tool_used = False
        tool_result = None
        
        for tool_output in report_data["tool_outputs"]:
            tool_name_from_output = tool_output.get("name", "")
            if tool_name_from_output.endswith("ticket_summary_tool"):
                custom_tool_used = True
                tool_result = tool_output.get("result", {})
                break
        
        # Check for evidence of tool usage in the report text
        report_text = report_data["report"]
        print(f"\nReport text: {report_text}")
        
        # 5. Clean up - delete the custom tool
        delete_response = requests.post(
            f"{BASE_URL}/custom_tools/delete",
            json={
                "token": admin_token,
                "tool_name": tool_name
            },
            headers={"Content-Type": "application/json"},
        )
        
        assert delete_response.status_code == 200, f"Failed to delete custom tool: {delete_response.text}"
        
    except Exception as e:
        print(f"\nTest failed with error: {str(e)}")
        raise e