import os
from google.adk.tools import FunctionTool
from google.adk.tools import ToolContext
from google.cloud import bigquery

# Initialize BigQuery client
client = bigquery.Client()
MODEL = os.getenv("ALERT_CLASSIFIER_MODEL", "ruckusoperations.BDC_6.alert_classifier")

def predict_features(features: dict, tool_context: ToolContext) -> dict:
    """Predict alert suppression using ML model in BigQuery."""
    try:
        # The BQML model expects a table with the exact column names
        # Based on the model schema: source, host, severity, status, created_at, resolved_at
        
        # Extract and format the features for the ML model, handling NULL values properly
        source = features.get("source") or "NULL"
        host = features.get("host") or "NULL"
        severity = features.get("severity") or "NULL"
        status = features.get("status") or "NULL"
        created_at = features.get("created_at") or "NULL"
        resolved_at = features.get("resolved_at") or "NULL"
        
        # Handle NULL values properly in SQL
        def format_value(value, is_timestamp=False):
            if value == "NULL" or value is None or value == "":
                return "CAST(NULL AS TIMESTAMP)" if is_timestamp else "NULL"
            if is_timestamp:
                # Ensure proper timestamp format
                if isinstance(value, str):
                    return f"TIMESTAMP('{value}')"
                else:
                    return f"TIMESTAMP('{str(value)}')"
            else:
                # Escape single quotes in string values
                escaped_value = str(value).replace("'", "\\'")
                return f"'{escaped_value}'"
        
        # Try multiple approaches to find the correct format
        approaches = [
            # Approach 1: Direct table format
            f"""
            SELECT * FROM ML.PREDICT(MODEL `{MODEL}`, (
                SELECT 
                    {format_value(source)} AS source,
                    {format_value(host)} AS host,
                    {format_value(severity)} AS severity,
                    {format_value(status)} AS status,
                    {format_value(created_at, True)} AS created_at,
                    {format_value(resolved_at, True)} AS resolved_at
            ))
            """,
            # Approach 2: Using WITH clause
            f"""
            WITH input_data AS (
                SELECT 
                    {format_value(source)} AS source,
                    {format_value(host)} AS host,
                    {format_value(severity)} AS severity,
                    {format_value(status)} AS status,
                    {format_value(created_at, True)} AS created_at,
                    {format_value(resolved_at, True)} AS resolved_at
            )
            SELECT * FROM ML.PREDICT(MODEL `{MODEL}`, (SELECT * FROM input_data))
            """,
            # Approach 3: Using VALUES clause
            f"""
            SELECT * FROM ML.PREDICT(MODEL `{MODEL}`, (
                SELECT * FROM UNNEST([STRUCT(
                    {format_value(source)} AS source,
                    {format_value(host)} AS host,
                    {format_value(severity)} AS severity,
                    {format_value(status)} AS status,
                    {format_value(created_at, True)} AS created_at,
                    {format_value(resolved_at, True)} AS resolved_at
                )])
            ))
            """
        ]
        
        # Try each approach until one works
        for i, sql in enumerate(approaches, 1):
            try:
                print(f"Trying approach {i}: {sql}")
                rows = [dict(r) for r in client.query(sql).result()]
                print(f"Approach {i} succeeded!")
                return {"status": "ok", "predictions": rows, "approach_used": i}
            except Exception as e:
                print(f"Approach {i} failed: {str(e)}")
                if i == len(approaches):  # Last approach
                    raise e
                continue
        
    except Exception as e:
        return {"status": "error", "message": str(e)}

def explain_features(features: dict, top_k: int = 5, tool_context: ToolContext = None) -> dict:
    """Explain ML predictions for alert classification."""
    try:
        # Extract and format the features for the ML model, handling NULL values properly
        source = features.get("source") or "NULL"
        host = features.get("host") or "NULL"
        severity = features.get("severity") or "NULL"
        status = features.get("status") or "NULL"
        created_at = features.get("created_at") or "NULL"
        resolved_at = features.get("resolved_at") or "NULL"
        
        # Handle NULL values properly in SQL
        def format_value(value, is_timestamp=False):
            if value == "NULL" or value is None or value == "":
                return "NULL"
            if is_timestamp:
                return f"TIMESTAMP('{value}')"
            else:
                # Escape single quotes in string values
                escaped_value = str(value).replace("'", "\\'")
                return f"'{escaped_value}'"
        
        # Create the SQL query using the correct BQML format - as a table, not STRUCT
        sql = f"""
        SELECT * FROM ML.EXPLAIN_PREDICT(MODEL `{MODEL}`,
            (SELECT 
                {format_value(source)} AS source,
                {format_value(host)} AS host,
                {format_value(severity)} AS severity,
                {format_value(status)} AS status,
                {format_value(created_at, True)} AS created_at,
                {format_value(resolved_at, True)} AS resolved_at
            ),
            STRUCT({top_k} AS top_k_features))
        """
        rows = [dict(r) for r in client.query(sql).result()]
        return {"status": "ok", "explain": rows}
    except Exception as e:
        return {"status": "error", "message": str(e)}

def decide(alert_row: dict, ml_pred: dict, tool_context: ToolContext = None) -> dict:
    """Decide action based on ML prediction and alert data."""
    try:
        # The model outputs predicted_decision_reason and predicted_decision_reason_probs
        pred = ml_pred.get("predicted_decision_reason", "keep")
        pred_probs = ml_pred.get("predicted_decision_reason_probs", {})
        
        # Get confidence for the predicted label
        confidence = None
        if isinstance(pred_probs, list) and len(pred_probs) > 0:
            # Find the probability for the predicted label
            for prob_entry in pred_probs:
                if prob_entry.get("label") == pred:
                    confidence = prob_entry.get("prob", 0.0)
                    break

        # Simple policy: never suppress critical (severity-1 or Sev1)
        if alert_row.get("severity") in ["severity-1", "Sev1"]:
            return {"decision": "forward", "reason": "critical_severity_always_forward"}

        # Confidence gate - if model predicts "suppressed: jira exists" with high confidence
        if pred == "suppressed: jira exists" and confidence and confidence >= 0.8:
            return {"decision": "suppress", "reason": f"ml_suppress_conf={confidence:.2f}"}

        # Fallback to rules
        return {"decision": "forward", "reason": "default-forward (no strong suppress)"}
    except Exception as e:
        return {"decision": "forward", "reason": f"error in decision: {str(e)}"}

def test_ml_model(tool_context: ToolContext) -> dict:
    """Test function to verify ML model is working with sample data."""
    try:
        model_name = os.getenv("ALERT_CLASSIFIER_MODEL", "ruckusoperations.BDC_6.alert_classifier")
        
        # First, let's check if the model exists and get its schema
        try:
            model_info_sql = f"""
            SELECT 
                model_name,
                model_type,
                creation_time,
                last_modified_time
            FROM `{model_name.split('.')[0]}.{model_name.split('.')[1]}.INFORMATION_SCHEMA.MODELS`
            WHERE model_name = '{model_name.split('.')[2]}'
            """
            model_info = list(client.query(model_info_sql).result())
            print(f"Model info: {model_info}")
        except Exception as e:
            print(f"Could not get model info: {e}")
        
        # Test with sample data that matches the model schema
        test_features = {
            "source": "jira",
            "host": "test-host",
            "severity": "Sev2",
            "status": "closed",
            "created_at": "2025-01-27T10:30:00Z",
            "resolved_at": "2025-01-27T11:30:00Z"
        }
        
        # Try the predict_features function with the test data
        result = predict_features(test_features, tool_context)
        
        return {
            "status": "success" if result.get("status") == "ok" else "error",
            "test_result": result,
            "message": "ML model test completed",
            "model_name": model_name,
            "test_features": test_features
        }
    except Exception as e:
        return {
            "status": "error",
            "message": f"ML model test failed: {str(e)}"
        }

def diagnose_ml_model(tool_context: ToolContext) -> dict:
    """Diagnose ML model issues by testing different input formats."""
    try:
        model_name = os.getenv("ALERT_CLASSIFIER_MODEL", "ruckusoperations.BDC_6.alert_classifier")
        
        # Test different input formats to find what works
        test_cases = [
            {
                "name": "Basic test with all fields",
                "features": {
                    "source": "jira",
                    "host": "test-host",
                    "severity": "Sev2",
                    "status": "closed",
                    "created_at": "2025-01-27T10:30:00Z",
                    "resolved_at": "2025-01-27T11:30:00Z"
                }
            },
            {
                "name": "Test with NULL values",
                "features": {
                    "source": "jira",
                    "host": "test-host",
                    "severity": "Sev2",
                    "status": "closed",
                    "created_at": "2025-01-27T10:30:00Z",
                    "resolved_at": None
                }
            },
            {
                "name": "Test with minimal fields",
                "features": {
                    "source": "jira",
                    "host": "test-host",
                    "severity": "Sev2",
                    "status": "closed",
                    "created_at": "2025-01-27T10:30:00Z",
                    "resolved_at": "2025-01-27T11:30:00Z"
                }
            }
        ]
        
        results = []
        for test_case in test_cases:
            try:
                result = predict_features(test_case["features"], tool_context)
                results.append({
                    "test_name": test_case["name"],
                    "status": "success",
                    "result": result
                })
            except Exception as e:
                results.append({
                    "test_name": test_case["name"],
                    "status": "error",
                    "error": str(e)
                })
        
        return {
            "status": "completed",
            "diagnosis_results": results,
            "model_name": model_name
        }
    except Exception as e:
        return {
            "status": "error",
            "message": f"ML model diagnosis failed: {str(e)}"
        }

def create_ml_model(tool_context: ToolContext) -> dict:
    """Create a new ML model for alert classification with the correct schema."""
    try:
        project_id = os.getenv("BQ_PROJECT_ID", "ruckusoperations")
        dataset_id = os.getenv("BQ_DATASET_ID", "BDC_6")
        model_name = "alert_classifier_v2"
        
        # Create the ML model with enhanced features for flapping and self-resolving detection
        create_model_sql = f"""
        CREATE OR REPLACE MODEL `{project_id}.{dataset_id}.{model_name}`
        OPTIONS(
            model_type='LOGISTIC_REG',
            input_label_cols=['decision_reason'],
            data_split_method='RANDOM',
            data_split_eval_fraction=0.2
        ) AS
        WITH enhanced_features AS (
            SELECT
                source,
                host,
                severity,
                status,
                created_at,
                resolved_at,
                decision_reason,
                -- Flapping features
                COUNT(*) OVER (
                    PARTITION BY host, title 
                    ORDER BY created_at 
                    RANGE BETWEEN INTERVAL 30 MINUTE PRECEDING AND CURRENT ROW
                ) as recent_alert_count,
                -- Self-resolving features
                CASE 
                    WHEN resolved_at IS NOT NULL 
                    THEN TIMESTAMP_DIFF(resolved_at, created_at, MINUTE)
                    ELSE NULL 
                END as resolution_time_minutes,
                -- Pattern features
                COUNT(*) OVER (
                    PARTITION BY host, title, DATE(created_at)
                ) as daily_alert_count
            FROM `{project_id}.{dataset_id}.alerts_data`
            WHERE decision_reason IS NOT NULL
            AND source IN ('pagerduty', 'jira', 'icinga')
        )
        SELECT
            source,
            host,
            severity,
            status,
            created_at,
            resolved_at,
            recent_alert_count,
            resolution_time_minutes,
            daily_alert_count,
            decision_reason
        FROM enhanced_features
        """
        
        print(f"Creating ML model with SQL: {create_model_sql}")
        query_job = client.query(create_model_sql)
        query_job.result()  # Wait for completion
        
        return {
            "status": "success",
            "message": f"ML model {model_name} created successfully",
            "model_name": f"{project_id}.{dataset_id}.{model_name}",
            "sql_used": create_model_sql
        }
    except Exception as e:
        return {
            "status": "error",
            "message": f"Failed to create ML model: {str(e)}"
        }

def train_ml_model(tool_context: ToolContext) -> dict:
    """Train the ML model with the correct schema."""
    try:
        project_id = os.getenv("BQ_PROJECT_ID", "ruckusoperations")
        dataset_id = os.getenv("BQ_DATASET_ID", "BDC_6")
        model_name = "alert_classifier_v2"
        
        # Check if model exists, if not create it
        try:
            check_sql = f"""
            SELECT model_name 
            FROM `{project_id}.{dataset_id}.INFORMATION_SCHEMA.MODELS`
            WHERE model_name = '{model_name}'
            """
            existing_models = list(client.query(check_sql).result())
            
            if not existing_models:
                # Create the model
                create_result = create_ml_model(tool_context)
                if create_result["status"] != "success":
                    return create_result
        
        except Exception as e:
            print(f"Error checking model existence: {e}")
        
        # Train the model
        train_sql = f"""
        CREATE OR REPLACE MODEL `{project_id}.{dataset_id}.{model_name}`
        OPTIONS(
            model_type='LOGISTIC_REG',
            input_label_cols=['decision_reason'],
            data_split_method='RANDOM',
            data_split_eval_fraction=0.2
        ) AS
        SELECT
            source,
            host,
            severity,
            status,
            created_at,
            resolved_at,
            decision_reason
        FROM `{project_id}.{dataset_id}.alerts_data`
        WHERE decision_reason IS NOT NULL
        AND source IN ('pagerduty', 'jira', 'icinga')
        """
        
        print(f"Training ML model with SQL: {train_sql}")
        query_job = client.query(train_sql)
        query_job.result()  # Wait for completion
        
        return {
            "status": "success",
            "message": f"ML model {model_name} trained successfully",
            "model_name": f"{project_id}.{dataset_id}.{model_name}",
            "training_sql": train_sql
        }
    except Exception as e:
        return {
            "status": "error",
            "message": f"Failed to train ML model: {str(e)}"
        }

def predict_with_new_model(features: dict, tool_context: ToolContext) -> dict:
    """Predict using the new ML model with correct schema."""
    try:
        project_id = os.getenv("BQ_PROJECT_ID", "ruckusoperations")
        dataset_id = os.getenv("BQ_DATASET_ID", "BDC_6")
        model_name = "alert_classifier_v2"
        
        # Check if model exists first
        try:
            check_sql = f"""
            SELECT model_name 
            FROM `{project_id}.{dataset_id}.INFORMATION_SCHEMA.MODELS`
            WHERE model_name = '{model_name}'
            """
            existing_models = list(client.query(check_sql).result())
            
            if not existing_models:
                return {
                    "status": "error",
                    "message": f"Model {model_name} not found. Please create and train the model first using create_ml_model or train_ml_model tools."
                }
        except Exception as e:
            return {
                "status": "error",
                "message": f"Error checking model existence: {str(e)}"
            }
        
        # Extract and format the features for the ML model
        source = features.get("source") or "NULL"
        host = features.get("host") or "NULL"
        severity = features.get("severity") or "NULL"
        status = features.get("status") or "NULL"
        created_at = features.get("created_at") or "NULL"
        resolved_at = features.get("resolved_at") or "NULL"
        
        # Handle NULL values properly in SQL
        def format_value(value, is_timestamp=False):
            if value == "NULL" or value is None or value == "":
                return "CAST(NULL AS TIMESTAMP)" if is_timestamp else "NULL"
            if is_timestamp:
                # Ensure proper timestamp format
                if isinstance(value, str):
                    return f"TIMESTAMP('{value}')"
                else:
                    return f"TIMESTAMP('{str(value)}')"
            else:
                # Escape single quotes in string values
                escaped_value = str(value).replace("'", "\\'")
                return f"'{escaped_value}'"
        
        # Use the new model with correct schema
        sql = f"""
        SELECT * FROM ML.PREDICT(MODEL `{project_id}.{dataset_id}.{model_name}`, (
            SELECT 
                {format_value(source)} AS source,
                {format_value(host)} AS host,
                {format_value(severity)} AS severity,
                {format_value(status)} AS status,
                {format_value(created_at, True)} AS created_at,
                {format_value(resolved_at, True)} AS resolved_at
        ))
        """
        
        print(f"Executing prediction with new model: {sql}")
        rows = [dict(r) for r in client.query(sql).result()]
        return {"status": "ok", "predictions": rows, "model_used": f"{project_id}.{dataset_id}.{model_name}"}
    except Exception as e:
        return {"status": "error", "message": str(e)}

# Wrap ML functions as FunctionTools
call_ds_agent = FunctionTool(func=predict_features)
explain_ds_agent = FunctionTool(func=explain_features)
decision_agent = FunctionTool(func=decide)
test_ml_model_tool = FunctionTool(func=test_ml_model)
diagnose_ml_model_tool = FunctionTool(func=diagnose_ml_model)
create_ml_model_tool = FunctionTool(func=create_ml_model)
train_ml_model_tool = FunctionTool(func=train_ml_model)
predict_with_new_model_tool = FunctionTool(func=predict_with_new_model)
