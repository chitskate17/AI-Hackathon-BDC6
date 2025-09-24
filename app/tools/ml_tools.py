# app/tools/ml_tools.py
from google.cloud import bigquery
client = bigquery.Client()
MODEL = "ruckusoperations.BDC_6.alert_classifier"

def predict_features(features: dict):
    # features -> dict of feature_name: value
    cols = ", ".join(f"{repr(v)} AS {k}" for k,v in features.items())
    sql = f"""
      SELECT * FROM ML.PREDICT(MODEL `{MODEL}`, (SELECT STRUCT({cols}) AS input))
    """
    rows = [dict(r) for r in client.query(sql).result()]
    return {"status":"ok", "predictions": rows}

def explain_features(features: dict, top_k: int = 5):
    cols = ", ".join(f"{repr(v)} AS {k}" for k,v in features.items())
    sql = f"""
      SELECT * FROM ML.EXPLAIN_PREDICT(MODEL `{MODEL}`,
        (SELECT STRUCT({cols}) AS input),
        STRUCT({top_k} AS top_k_features))
    """
    rows = [dict(r) for r in client.query(sql).result()]
    return {"status":"ok", "explain": rows}
