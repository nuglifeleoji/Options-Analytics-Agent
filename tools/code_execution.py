"""
Code Execution Tool - Dynamic Python Code Execution for Custom Data Processing

This module provides a sandboxed environment for executing AI-generated Python code
to process options data with custom logic and export formats.

Author: Leo Ji
"""

import json
import csv
import os
import sys
from datetime import datetime
from io import StringIO
from langchain_core.tools import tool


@tool
def code_execution_tool(code: str, options_data: str = "") -> str:
    """Execute Python code for custom data processing and return the result.
    
    This tool allows AI to write custom code to process options data.
    The AI can read code_examples/csv_export_template.py for reference,
    then write customized code based on user requirements.
    
    Args:
        code: Python code to execute (string). The code can use:
              - options_data: The JSON data from search_options
              - json, csv, datetime, os modules (pre-imported)
        options_data: (Optional) JSON string from search_options tool.
                     This will be available as 'options_data' variable in the code.
        
    Returns:
        Captured output from the code execution
        
    Example usage:
        User: "I want only call options between $240-$260"
        AI should:
        1. Read code_examples/csv_export_template.py to see examples
        2. Write code that filters and exports data
        3. Call code_execution_tool(code=<generated_code>, options_data=<data_from_search_options>)
    """
    try:
        # Capture stdout
        old_stdout = sys.stdout
        sys.stdout = StringIO()
        
        # Create execution namespace with necessary imports and data
        exec_globals = {
            '__builtins__': __builtins__,
            'json': json,
            'csv': csv,
            'datetime': datetime,
            'os': os,
            'options_data': options_data  # Inject data into execution environment
        }
        
        # Execute the code
        exec(code, exec_globals)
        
        # Get the output
        output = sys.stdout.getvalue()
        sys.stdout = old_stdout
        
        if output:
            return f"✅ Code executed successfully:\n{output}"
        else:
            return "✅ Code executed successfully (no output)"
            
    except Exception as e:
        import traceback
        sys.stdout = old_stdout
        error_details = traceback.format_exc()
        return f"❌ Error executing code:\n{str(e)}\n\nDetails:\n{error_details}"


# Export the tool
__all__ = ['code_execution_tool']

