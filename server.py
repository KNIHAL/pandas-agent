import traceback
import json
from datetime import datetime, date, time
from decimal import Decimal
import numpy as np
import pandas as _pd
from core.config import mcp
from core.metadata import read_metadata
from core.execution import run_pandas_code
from core.visualization import generate_chartjs

@mcp.tool()
def read_metadata_tool(file_path: str) -> dict:
    """Read file metadata (Excel or CSV) and return in MCP-compatible format.
    
    Args:
        file_path: Absolute path to data file
        
    Returns:
        dict: Structured metadata including:
            For Excel:
                - file_info: {type: "excel", sheet_count, sheet_names}
                - data: {sheets: [{sheet_name, rows, columns}]}
            For CSV:
                - file_info: {type: "csv", encoding, delimiter}
                - data: {rows, columns}
            Common:
                - status: SUCCESS/ERROR
                - columns contain:
                    - name, type, examples
                    - stats: null_count, unique_count
                    - warnings, suggested_operations
    """
    try:
        result = read_metadata(file_path)
        return result
    except Exception as e:
        return {
            "status": "ERROR",
            "error_type": "TOOL_EXECUTION_ERROR",
            "message": str(e)
        }

@mcp.tool()
def run_pandas_code_tool(code: str) -> dict:
    """Execute pandas code with smart suggestions and security checks.
    
    Args:
        code: Python code string containing pandas operations
        
    Returns:
        dict: Either the result or error information
        
    Forbidden Operations:
        The following operations are blocked for security reasons:
        - 'os.', 'sys.', 'subprocess.' - System access operations
        - 'open(', 'exec(', 'eval(' - Code execution functions
        - 'import os', 'import sys' - Specific dangerous imports
        - 'document.', 'window.', 'XMLHttpRequest' - Browser/DOM access
        - 'fetch(', 'eval(', 'Function(' - JavaScript/remote operations
        - 'script', 'javascript:' - Script injection attempts
        
    Requirements:
        - Must assign final result to 'result' variable
        - Code should contain necessary imports (pandas available as 'pd')
    """
    return run_pandas_code(code)

@mcp.tool()
def generate_chartjs_tool(
    data: dict,
    chart_types: list = None,
    title: str = "Data Visualization",
    request_params: dict = None
) -> dict:
    """Generate interactive Chart.js visualizations from structured data.
    
    Args:
        data: Structured data in MCP format with required structure:
            {
                "columns": [
                    {
                        "name": str,      # Column name
                        "type": str,       # "string" or "number"
                        "examples": list   # Array of values
                    },
                    ...                   # Additional columns
                ]
            }
        chart_types: List of supported chart types to generate (first is used)
        title: Chart title string
        request_params: Additional visualization parameters (optional)
        
    Returns:
        dict: Result with structure:
            {
                "status": "SUCCESS"|"ERROR",
                "chart_html": str,         # Generated HTML content
                "chart_type": str,         # Type of chart generated
                "html_path": str          # Path to saved HTML file
            }
    """
    return generate_chartjs(data, chart_types, title, request_params)

@mcp.tool()
def read_json_tool(file_path: str, orient: str = "records") -> dict:
    """Read JSON file and return data.
    
    Args:
        file_path: Path to JSON file
        orient: JSON structure - 'records', 'columns', 'index', 'values'
    
    Returns:
        dict with status and data
    """
    try:
        import pandas as pd
        df = pd.read_json(file_path, orient=orient)
        return {
            "status": "SUCCESS",
            "data": df.to_dict(orient='records'),
            "shape": df.shape,
            "columns": df.columns.tolist()
        }
    except Exception as e:
        return {"status": "ERROR", "message": str(e)}

@mcp.tool()
def dataframe_to_json_tool(code: str, output_path: str, orient: str = "records") -> dict:
    """Convert DataFrame to JSON file.
    
    Args:
        code: Pandas code that creates 'result' DataFrame
        output_path: Where to save JSON
        orient: Output format
    """
    try:
        result = run_pandas_code(code)
        if result.get('status') == 'ERROR':
            return result

        df = result.get('result')
        # Validate that the returned object is a DataFrame
        import pandas as pd
        if not isinstance(df, pd.DataFrame):
            return {"status": "ERROR", "message": "Expected a pandas.DataFrame in 'result'"}

        # pandas.DataFrame.to_json does not accept an `indent` parameter.
        # To produce pretty-printed JSON, convert to native Python data and use json.dump.
        data = df.to_dict(orient=orient)

        def _make_json_serializable(o):
            """Recursively convert pandas/numpy/datetime/Decimal types to JSON-serializable types."""
            # Primitives
            if o is None or isinstance(o, (str, bool, int, float)):
                return o

            # numpy scalar types
            if isinstance(o, (np.integer, np.floating, np.bool_, np.number)):
                try:
                    return o.item()
                except Exception:
                    return float(o)

            # Decimal
            if isinstance(o, Decimal):
                return str(o)

            # pandas NaT/NA
            try:
                if _pd.isna(o):
                    return None
            except Exception:
                pass

            # datetime types
            if isinstance(o, (datetime, date, time, _pd.Timestamp)):
                try:
                    return o.isoformat()
                except Exception:
                    return str(o)

            # dict-like
            if isinstance(o, dict):
                return {k: _make_json_serializable(v) for k, v in o.items()}

            # list/tuple/set
            if isinstance(o, (list, tuple, set)):
                return [_make_json_serializable(v) for v in o]

            # numpy arrays and other array-like
            if hasattr(o, 'tolist'):
                try:
                    return _make_json_serializable(o.tolist())
                except Exception:
                    pass

            # Fallback to string
            try:
                return str(o)
            except Exception:
                return None

        serializable_data = _make_json_serializable(data)
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(serializable_data, f, indent=2, ensure_ascii=False)

        return {"status": "SUCCESS", "path": output_path}
    except Exception as e:
        return {"status": "ERROR", "message": str(e), "traceback": traceback.format_exc()}

@mcp.tool()
def read_sql_tool(query: str, connection_string: str) -> dict:
    """Read data from SQL database.
    
    Args:
        query: SQL query
        connection_string: Database URL (e.g., 'sqlite:///data.db')
    
    Returns:
        dict with data
    """
    try:
        import pandas as pd
        from sqlalchemy import create_engine
        
        engine = create_engine(connection_string)
        df = pd.read_sql(query, engine)
        
        return {
            "status": "SUCCESS",
            "data": df.to_dict(orient='records'),
            "shape": df.shape,
            "columns": df.columns.tolist()
        }
    except Exception as e:
        return {"status": "ERROR", "message": str(e)}

@mcp.tool()
def dataframe_to_sql_tool(
    code: str, 
    table_name: str, 
    connection_string: str,
    if_exists: str = "replace"
) -> dict:
    """Save DataFrame to SQL database.
    
    Args:
        code: Pandas code creating 'result' DataFrame
        table_name: SQL table name
        connection_string: Database URL
        if_exists: 'replace', 'append', 'fail'
    """
    try:
        from sqlalchemy import create_engine
        
        result = run_pandas_code(code)
        if result.get('status') == 'ERROR':
            return result
        
        df = result.get('result')
        engine = create_engine(connection_string)
        df.to_sql(table_name, engine, if_exists=if_exists, index=False)
        
        return {"status": "SUCCESS", "table": table_name, "rows": len(df)}
    except Exception as e:
        return {"status": "ERROR", "message": str(e)}


def main():
    try:
        mcp.run()
    except Exception as e:
        print(f"Server failed to start: {str(e)}")
        raise

if __name__ == "__main__":
    main()