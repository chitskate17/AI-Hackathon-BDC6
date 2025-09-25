import os
from google.adk.tools import FunctionTool
from google.adk.tools import ToolContext
from google.cloud import bigquery

# Initialize BigQuery client
client = bigquery.Client()

def run_sql(sql: str, tool_context: ToolContext) -> dict:
    """Execute SQL query in BigQuery and return results."""
    try:
        job = client.query(sql)
        rows = [dict(r) for r in job.result(max_results=1000)]
        return {"status": "ok", "rows": rows}
    except Exception as e:
        return {"status": "error", "message": str(e)}

def write_table(table: str, rows: list, tool_context: ToolContext) -> dict:
    """Write rows to a BigQuery table."""
    try:
        errors = client.insert_rows_json(table, rows)
        if errors:
            return {"status": "error", "errors": errors}
        return {"status": "ok", "inserted": len(rows)}
    except Exception as e:
        return {"status": "error", "message": str(e)}

# Wrap BigQuery SQL execution as an ADK FunctionTool
call_db_agent = FunctionTool(func=run_sql)
write_db_table = FunctionTool(func=write_table)
