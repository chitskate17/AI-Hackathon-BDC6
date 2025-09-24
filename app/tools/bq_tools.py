# app/tools/bq_tools.py
from google.cloud import bigquery
client = bigquery.Client()

def run_sql(sql: str, max_rows: int = 1000):
    job = client.query(sql)
    rows = [dict(r) for r in job.result(max_results=max_rows)]
    return {"status": "ok", "rows": rows}

def write_table(table: str, rows: list):
    # rows = [ {col: value}, ... ]
    errors = client.insert_rows_json(table, rows)
    if errors:
        return {"status": "error", "errors": errors}
    return {"status": "ok", "inserted": len(rows)}
