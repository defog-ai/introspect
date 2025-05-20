from auth_utils import validate_user_request
from fastapi import APIRouter, Depends, HTTPException
from request_models import (
    AnswerQuestionFromDatabaseRequest,
    SynthesizeReportFromQuestionRequest,
    WebSearchRequest,
    CustomToolRequest,
    CustomToolCreateRequest,
    CustomToolUpdateRequest,
    CustomToolDeleteRequest,
    CustomToolListRequest,
    CustomToolToggleRequest,
    CustomToolTestRequest,
)
from tools.analysis_models import (
    GenerateReportFromQuestionInput,
    GenerateReportWithAgentsInput,
    AnswerQuestionInput,
)
from tools.analysis_tools import (
    generate_report_from_question,
    web_search_tool,
    generate_report_with_agents,
)
from datetime import datetime
from sqlalchemy.future import select
from sqlalchemy import update, delete
from db_config import get_defog_internal_session
from db_models import CustomTools
from utils_logging import LOGGER
import ast

router = APIRouter(
    dependencies=[Depends(validate_user_request)],
    tags=["Tools"],
)


@router.post("/answer_question_from_database")
async def answer_question_from_database_route(
    request: AnswerQuestionFromDatabaseRequest,
):
    """
    Route used for testing purposes.
    Generates SQL from a question and database.
    """
    question = request.question
    db_name = request.db_name
    model = request.model or "o4-mini"
    return await generate_report_from_question(
        question=question,
        db_name=db_name,
        model=model,
        clarification_responses="",
        post_tool_func=None
    )


@router.post("/generate_report_with_agents")
async def generate_report_with_agents_route(
    request: GenerateReportWithAgentsInput,
):
    """
    Generates a comprehensive analysis report using multiple OpenAI agents.
    This route uses a multi-agent approach where:
    1. An analyst agent generates initial data analysis
    2. An evaluator agent determines if more research is needed
    3. A report agent synthesizes findings into a final report
    
    The pipeline can loop up to 3 times to refine the analysis based on evaluator feedback.
    """
    return await generate_report_with_agents(
        db_name=request.db_name,
        model=request.model,
        question=request.question,
        clarification_responses=request.clarification_responses,
        pdf_file_ids=request.pdf_file_ids,
        use_websearch=request.use_websearch
    )


@router.post("/web_search")
async def web_search_route(request: WebSearchRequest):
    """
    Test route for testing the web search tool.
    Performs a Google search for the given question and returns the AI-generated
    summary of the search results.
    """
    try:
        LOGGER.info(f"Web search route called with question: {request.question}")
        
        search_input = AnswerQuestionInput(
            question=request.question,
        )
        search_result = await web_search_tool(search_input)
        
        LOGGER.info(f"Web search completed successfully")
        
        # Return a structured response
        return {
            "question": request.question,
            "search_result": search_result
        }
    except Exception as e:
        LOGGER.error(f"Error in web_search_route: {str(e)}", exc_info=True)
        # Return error information
        return {
            "question": request.question,
            "error": str(e)
        }


# Helper function to validate tool code without execution
def validate_tool_code(code: str) -> bool:
    """
    Validate that the tool code is syntactically correct and doesn't contain unsafe operations.
    """
    # Check syntax
    try:
        tree = ast.parse(code)
    except SyntaxError as e:
        return False, f"Syntax error in tool code: {str(e)}"
    
    # Check for unsafe operations (eval, exec, etc.)
    unsafe_calls = ['eval', 'exec', '__import__', 'subprocess', 'os.system', 
                    'os.popen', 'os.spawn', 'os.fork', 'pty.spawn']
    
    for node in ast.walk(tree):
        # Check for import statements
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            # Check import targets
            if isinstance(node, ast.ImportFrom) and node.module and any(
                unsafe in node.module for unsafe in ['subprocess', 'os', 'sys', 'pty', 'shutil']
            ):
                return False, f"Unsafe import: {node.module}"
            
            # Check imported names
            if isinstance(node, ast.ImportFrom) and node.names:
                for name in node.names:
                    if name.name in ['system', 'popen', 'spawn', 'eval', 'exec']:
                        return False, f"Unsafe import name: {name.name}"
        
        # Check for unsafe function calls
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id in ['eval', 'exec']:
            return False, f"Unsafe function call: {node.func.id}"
        
        # Check for attribute access that could be unsafe
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
            # Get the full attribute chain
            attr_chain = []
            obj = node.func
            while isinstance(obj, ast.Attribute):
                attr_chain.append(obj.attr)
                obj = obj.value
            
            if isinstance(obj, ast.Name):
                attr_chain.append(obj.id)
                attr_path = '.'.join(reversed(attr_chain))
                
                # Check if the attribute path contains unsafe operations
                for unsafe in unsafe_calls:
                    if unsafe in attr_path:
                        return False, f"Unsafe operation: {attr_path}"
    
    # Check if there's at least one async function definition
    has_async_function = any(
        isinstance(node, ast.AsyncFunctionDef)
        for node in ast.walk(tree)
    )
    
    if not has_async_function:
        return False, "Tool must contain at least one async function"

    return True, ""


# Helper function to validate input model code without execution
def validate_input_model(code: str) -> bool:
    """
    Validate that the provided input model code is safe and only defines
    Pydantic models. Import statements and unsafe builtins are disallowed.
    """

    try:
        tree = ast.parse(code)
    except SyntaxError as e:
        return False, f"Syntax error in input model: {str(e)}"

    unsafe_calls = [
        'eval', 'exec', '__import__', 'subprocess', 'os.system',
        'os.popen', 'os.spawn', 'os.fork', 'pty.spawn'
    ]

    for node in ast.walk(tree):
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            return False, "Import statements are not allowed in input_model"

        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id in unsafe_calls:
            return False, f"Unsafe function call: {node.func.id}"

        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
            attr_chain = []
            obj = node.func
            while isinstance(obj, ast.Attribute):
                attr_chain.append(obj.attr)
                obj = obj.value

            if isinstance(obj, ast.Name):
                attr_chain.append(obj.id)
                attr_path = '.'.join(reversed(attr_chain))

                if any(unsafe in attr_path for unsafe in unsafe_calls):
                    return False, f"Unsafe operation: {attr_path}"

    has_model = any(
        isinstance(node, ast.ClassDef) and
        any(
            (isinstance(base, ast.Name) and base.id == 'BaseModel') or
            (isinstance(base, ast.Attribute) and base.attr == 'BaseModel')
            for base in node.bases
        )
        for node in tree.body
    )

    if not has_model:
        return False, "Input model must define a class inheriting from BaseModel"

    return True, ""


# Custom tool routes
@router.post("/custom_tools/create")
async def create_custom_tool(request: CustomToolCreateRequest):
    """
    Create a new custom tool for a database.
    """
    tool_name = request.tool_name
    
    # Validate the tool code
    is_valid, error_message = validate_tool_code(request.tool_code)
    if not is_valid:
        raise HTTPException(status_code=400, detail=f"Invalid tool code: {error_message}")

    if request.input_model:
        is_valid, error_message = validate_input_model(request.input_model)
        if not is_valid:
            raise HTTPException(status_code=400, detail=f"Invalid input model: {error_message}")
    
    # Check if tool already exists
    async with get_defog_internal_session() as session:
        result = await session.execute(
            select(CustomTools).where(
                CustomTools.tool_name == tool_name
            )
        )
        existing_tool = result.first()
        
        if existing_tool:
            raise HTTPException(status_code=400, detail=f"Tool '{tool_name}' already exists")
        
        # Create the new tool
        new_tool = CustomTools(
            tool_name=tool_name,
            tool_description=request.tool_description,
            input_model=request.input_model,
            tool_code=request.tool_code,
            is_enabled=True,
            created_at=datetime.now(),
            updated_at=datetime.now()
        )
        
        session.add(new_tool)
        await session.commit()
    
    return {
        "status": "success",
        "message": f"Tool '{tool_name}' created successfully",
        "tool": {
            "tool_name": tool_name,
            "tool_description": request.tool_description,
            "is_enabled": True
        }
    }


@router.post("/custom_tools/update")
async def update_custom_tool(request: CustomToolUpdateRequest):
    """
    Update an existing custom tool.
    """
    tool_name = request.tool_name
    
    # Validate the tool code
    is_valid, error_message = validate_tool_code(request.tool_code)
    if not is_valid:
        raise HTTPException(status_code=400, detail=f"Invalid tool code: {error_message}")

    if request.input_model:
        is_valid, error_message = validate_input_model(request.input_model)
        if not is_valid:
            raise HTTPException(status_code=400, detail=f"Invalid input model: {error_message}")
    
    # Check if tool exists
    async with get_defog_internal_session() as session:
        result = await session.execute(
            select(CustomTools).where(
                CustomTools.tool_name == tool_name
            )
        )
        existing_tool = result.first()
        
        if not existing_tool:
            raise HTTPException(status_code=404, detail=f"Tool '{tool_name}' not found")
        
        # Update the tool
        await session.execute(
            update(CustomTools)
            .where(
                CustomTools.tool_name == tool_name
            )
            .values(
                tool_description=request.tool_description,
                input_model=request.input_model,
                tool_code=request.tool_code,
                updated_at=datetime.now()
            )
        )
        
        await session.commit()
    
    return {
        "status": "success",
        "message": f"Tool '{tool_name}' updated successfully",
        "tool": {
            "tool_name": tool_name,
            "tool_description": request.tool_description,
            "is_enabled": True
        }
    }


@router.post("/custom_tools/delete")
async def delete_custom_tool(request: CustomToolDeleteRequest):
    """
    Delete a custom tool.
    """
    tool_name = request.tool_name
    
    # Check if tool exists
    async with get_defog_internal_session() as session:
        result = await session.execute(
            select(CustomTools).where(
                CustomTools.tool_name == tool_name
            )
        )
        existing_tool = result.first()
        
        if not existing_tool:
            raise HTTPException(status_code=404, detail=f"Tool '{tool_name}' not found")
        
        # Delete the tool
        await session.execute(
            delete(CustomTools)
            .where(
                CustomTools.tool_name == tool_name
            )
        )
        
        await session.commit()
    
    return {
        "status": "success",
        "message": f"Tool '{tool_name}' deleted successfully"
    }


@router.post("/custom_tools/list")
async def list_custom_tools(request: CustomToolListRequest):
    """
    List all custom tools for a database.
    """
    async with get_defog_internal_session() as session:
        result = await session.execute(
            select(CustomTools)
        )
        tools = result.all()
        
        tool_list = [
            {
                "tool_name": tool[0].tool_name,
                "tool_description": tool[0].tool_description,
                "is_enabled": tool[0].is_enabled,
                "created_at": tool[0].created_at,
                "updated_at": tool[0].updated_at
            }
            for tool in tools
        ]
    
    return {
        "status": "success",
        "tools": tool_list
    }


@router.post("/custom_tools/toggle")
async def toggle_custom_tool(request: CustomToolToggleRequest):
    """
    Enable or disable a custom tool.
    """
    tool_name = request.tool_name
    is_enabled = request.is_enabled
    
    # Check if tool exists
    async with get_defog_internal_session() as session:
        result = await session.execute(
            select(CustomTools).where(
                CustomTools.tool_name == tool_name
            )
        )
        existing_tool = result.first()
        
        if not existing_tool:
            raise HTTPException(status_code=404, detail=f"Tool '{tool_name}' not found")
        
        # Update the tool's enabled status
        await session.execute(
            update(CustomTools)
            .where(
                CustomTools.tool_name == tool_name
            )
            .values(
                is_enabled=is_enabled,
                updated_at=datetime.now()
            )
        )
        
        await session.commit()
    
    action = "enabled" if is_enabled else "disabled"
    return {
        "status": "success",
        "message": f"Tool '{tool_name}' {action} successfully",
        "tool": {
            "tool_name": tool_name,
            "is_enabled": is_enabled
        }
    }


@router.post("/custom_tools/get")
async def get_custom_tool(request: CustomToolRequest):
    """
    Get details of a specific custom tool.
    """
    tool_name = request.tool_name
    
    async with get_defog_internal_session() as session:
        result = await session.execute(
            select(CustomTools).where(
                CustomTools.tool_name == tool_name
            )
        )
        tool = result.first()
        
        if not tool:
            raise HTTPException(status_code=404, detail=f"Tool '{tool_name}' not found")
        
        tool_info = {
            "tool_name": tool[0].tool_name,
            "tool_description": tool[0].tool_description,
            "input_model": tool[0].input_model,
            "tool_code": tool[0].tool_code,
            "is_enabled": tool[0].is_enabled,
            "created_at": tool[0].created_at,
            "updated_at": tool[0].updated_at
        }
    
    return {
        "status": "success",
        "tool": tool_info
    }


@router.post("/custom_tools/test")
async def test_custom_tool(request: CustomToolTestRequest):
    """
    Test a custom tool without saving it to the database.
    """
    # Validate the tool code
    is_valid, error_message = validate_tool_code(request.tool_code)
    if not is_valid:
        raise HTTPException(status_code=400, detail=f"Invalid tool code: {error_message}")

    if request.input_model:
        is_valid, error_message = validate_input_model(request.input_model)
        if not is_valid:
            raise HTTPException(status_code=400, detail=f"Invalid input model: {error_message}")
    
    # Create a temporary tool for testing
    import sys
    import types
    import inspect
    from pydantic import BaseModel, Field
    import traceback
    
    try:
        module_name = f"temp_tool_{hash(request.tool_code)}"
        module = types.ModuleType(module_name)
        sys.modules[module_name] = module

        # Execute the input model code in a restricted namespace first
        if request.input_model:
            namespace = {
                "BaseModel": BaseModel,
                "Field": Field,
                "__builtins__": {},
            }
            before_keys = set(namespace.keys())
            exec(request.input_model, namespace)
            for key in set(namespace.keys()) - before_keys:
                module.__dict__[key] = namespace[key]

        # Execute the tool code in the module's namespace
        exec(request.tool_code, module.__dict__)
        
        # Find the async function in the module
        tool_func = None
        for name, obj in inspect.getmembers(module):
            if inspect.iscoroutinefunction(obj):
                tool_func = obj
                break
        
        if not tool_func:
            raise HTTPException(status_code=400, detail="No async function found in the provided code")
        
        # Try to extract parameter details from the function
        signature = inspect.signature(tool_func)
        param_info = {}
        
        for param_name, param in signature.parameters.items():
            param_type = param.annotation
            if hasattr(param_type, '__name__'):
                param_info[param_name] = param_type.__name__
            else:
                param_info[param_name] = str(param_type)
        
        # Determine input
        if request.test_input:
            # Use provided test input
            # TestModel = eval(request.input_model.strip())
            # request.input_model is a string containing the definition of the model, like class MathInput(BaseModel):
            #     a: int = Field(..., description="The first number")
            #     b: int = Field(..., description="The second number"

            namespace = {
                "BaseModel": BaseModel,
                "Field": Field,
                "__builtins__": {},
            }
            before_keys = set(namespace.keys())
            exec(request.input_model, namespace)
            after_keys = set(namespace.keys())
            new_keys = after_keys - before_keys

            ModelClass = [
                obj for key, obj in namespace.items()
                if key in new_keys and isinstance(obj, type) and issubclass(obj, BaseModel)
            ][0]
            
            test_input = ModelClass(**request.test_input)
            result = await tool_func(test_input)
        else:
            # Look for a parameter class in the module
            param_class = None
            for name, obj in inspect.getmembers(module):
                if isinstance(obj, type) and issubclass(obj, BaseModel) and obj != BaseModel:
                    param_class = obj
                    break
            
            if param_class:
                # Create a dummy input with default values
                dummy_input = param_class()
                result = await tool_func(dummy_input)
            else:
                # Call without parameters if no input model found
                result = await tool_func()
        
        return {
            "status": "success",
            "message": "Tool test executed successfully",
            "parameter_info": param_info,
            "result": result
        }
    
    except Exception as e:
        LOGGER.error(f"Error testing custom tool: {str(e)}")
        LOGGER.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=f"Error testing tool: {str(e)}")
    
    finally:
        # Clean up loaded module
        if module_name in sys.modules:
            del sys.modules[module_name]
