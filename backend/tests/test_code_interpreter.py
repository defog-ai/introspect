"""Tests for the code_interpreter_tool functionality."""

import pytest
import asyncio
import json
import sys
import os
import pandas as pd

# Import directly from the backend
from tools.analysis_tools import code_interpreter_tool
from tools.analysis_models import AnswerQuestionFromDatabaseInput

# Define test database configuration similar to conftest.py
TEST_DB = {
    "db_name": "test_db",
    "db_type": "postgres",
    "db_creds": {
        "host": "agents-postgres",
        "port": 5432,
        "database": "test_db",
        "user": "postgres",
        "password": "postgres",
    },
}

@pytest.mark.asyncio(loop_scope="session")
async def test_code_interpreter_advanced_statistics():
    """
    Test the code_interpreter_tool's ability to perform advanced statistical calculations
    that would be difficult or impossible in SQL alone.
    """
    # This question requires calculating z-scores, which is challenging in SQL
    question = "Calculate the z-scores for ticket prices and identify any outliers (prices more than 2 standard deviations from the mean)"
    input_data = AnswerQuestionFromDatabaseInput(
        question=question,
        db_name=TEST_DB["db_name"]
    )
    
    # Call the code_interpreter_tool
    result = await code_interpreter_tool(input_data)

    # Verify the response structure
    assert "analysis_id" in result, "Missing analysis_id in result"
    assert "question" in result, "Missing question in result"
    assert "code" in result, "Missing code in result"
    assert "result" in result, "Missing result in result"
    
    # Verify the code contains statistical calculations
    code = result["code"]
    assert "z_score" in code or "zscore" in code, "Code does not contain z-score calculation"

    # Verify the result contains z-score related information
    result_text = result["result"]
    print(f"\nTest result preview: {result_text[:200]}...")
    assert any(term in result_text.lower() for term in ["z-score", "zscore", "standard deviation", "outlier"]), "Result does not contain z-score analysis"


@pytest.mark.asyncio(loop_scope="session")
async def test_code_interpreter_probability_analysis():
    """
    Test the code_interpreter_tool's ability to perform probability calculations
    and distributions not easily done in SQL.
    """
    # This requires probability distribution analysis
    question = "Perform a probability analysis on ticket sales. What is the probability distribution of tickets sold by type? Generate a probability mass function and calculate the entropy of the distribution."
    input_data = AnswerQuestionFromDatabaseInput(
        question=question,
        db_name=TEST_DB["db_name"]
    )
    
    # Call the code_interpreter_tool
    result = await code_interpreter_tool(input_data)
    
    # Verify code contains probability-related functions
    code = result["code"]
    assert any(term in code.lower() for term in ["probability", "distribution", "entropy"]), "Code does not contain probability analysis"
    
    # Verify result discusses probability distribution
    result_text = result["result"]
    assert any(term in result_text.lower() for term in ["probability", "distribution", "entropy"]), "Result does not contain probability analysis"
    
    print(f"\nTest result preview: {result_text[:200]}...")


@pytest.mark.asyncio(loop_scope="session")
async def test_code_interpreter_correlation_analysis():
    """
    Test the code_interpreter_tool's ability to perform correlation analysis
    between variables, which requires matrix operations beyond SQL's capabilities.
    """
    # This requires correlation analysis between variables
    question = "Analyze the correlation between ticket prices and sales quantities. Calculate Pearson and Spearman correlation coefficients and explain their significance."
    input_data = AnswerQuestionFromDatabaseInput(
        question=question,
        db_name=TEST_DB["db_name"]
    )
    
    # Call the code_interpreter_tool
    result = await code_interpreter_tool(input_data)
    
    # Verify code contains correlation functions
    code = result["code"]
    assert any(term in code.lower() for term in ["corr", "pearson", "spearman", "correlation"]), "Code does not contain correlation analysis"
    
    # Verify result discusses correlation
    result_text = result["result"]
    assert any(term in result_text.lower() for term in ["correlation", "relationship", "pearson", "spearman"]), "Result does not contain correlation analysis"
    
    print(f"\nTest result preview: {result_text[:200]}...")


@pytest.mark.asyncio(loop_scope="session")
async def test_code_interpreter_custom_formula():
    """
    Test the code_interpreter_tool's ability to apply custom business formulas
    that would be complex to implement in SQL.
    """
    # This requires applying a custom business formula
    question = "Calculate a customer loyalty score based on the formula: 'loyalty = (days since first purchase) * 0.1 + (number of tickets) * 0.5 + (total spent) * 0.01'. Rank customers by this score."
    input_data = AnswerQuestionFromDatabaseInput(
        question=question,
        db_name=TEST_DB["db_name"]
    )
    
    # Call the code_interpreter_tool
    result = await code_interpreter_tool(input_data)
    
    # Verify code implements the custom formula
    code = result["code"]
    assert "loyalty" in code, "Code does not implement loyalty formula"
    
    # Verify result discusses the loyalty scoring
    result_text = result["result"]
    assert "loyalty" in result_text.lower(), "Result does not mention loyalty scoring"
    assert "rank" in result_text.lower(), "Result does not mention ranking"
    
    print(f"\nTest result preview: {result_text[:200]}...")


@pytest.mark.asyncio(loop_scope="session")
async def test_code_interpreter_time_series():
    """
    Test the code_interpreter_tool's ability to perform time series analysis
    that would require specialized libraries in Python.
    """
    # This requires time series forecasting and decomposition
    question = "Perform a time series analysis of ticket sales. Decompose the time series into trend, seasonal, and residual components. Forecast sales for the next month using exponential smoothing."
    input_data = AnswerQuestionFromDatabaseInput(
        question=question,
        db_name=TEST_DB["db_name"]
    )
    
    # Call the code_interpreter_tool
    result = await code_interpreter_tool(input_data)
    
    # Verify code does time series analysis
    code = result["code"]
    
    # Verify result discusses time series components
    result_text = result["result"]
    assert any(term in result_text.lower() for term in ["time series", "trend", "seasonal", "residual", "forecast"]), "Result does not contain time series analysis"
    
    print(f"\nTest result preview: {result_text[:200]}...")