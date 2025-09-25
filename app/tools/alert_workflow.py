"""
Alert Management Workflow Tools
Comprehensive tools for processing alerts through the multi-agent system
"""

import os
import json
from datetime import datetime
from typing import Dict, List, Any
from google.adk.tools import FunctionTool
from google.adk.tools import ToolContext
from google.cloud import bigquery

# Initialize BigQuery client
client = bigquery.Client()

def process_alert_workflow(alert_data: Dict[str, Any], tool_context: ToolContext) -> Dict[str, Any]:
    """
    Process an alert through the complete multi-agent workflow.
    
    Args:
        alert_data: Dictionary containing alert information
        tool_context: ADK tool context
    
    Returns:
        Complete workflow processing results
    """
    try:
        workflow_results = {
            "alert_id": alert_data.get("alert_id"),
            "timestamp": datetime.now().isoformat(),
            "workflow_steps": []
        }
        
        # Step 1: Initial Alert Analysis
        analysis_result = analyze_alert_initial(alert_data, tool_context)
        workflow_results["workflow_steps"].append({
            "step": "initial_analysis",
            "result": analysis_result
        })
        
        # Step 2: Duplicate Check
        duplicate_result = check_alert_duplicates(alert_data, tool_context)
        workflow_results["workflow_steps"].append({
            "step": "duplicate_check",
            "result": duplicate_result
        })
        
        # Step 3: Pattern Analysis (flapping and self-resolving)
        pattern_result = analyze_alert_patterns(alert_data, tool_context)
        workflow_results["workflow_steps"].append({
            "step": "pattern_analysis",
            "result": pattern_result
        })
        
        # Step 4: ML Prediction (if not duplicate and not flapping/self-resolving)
        if (not duplicate_result.get("is_duplicate", False) and 
            not pattern_result.get("pattern_summary", {}).get("should_suppress", False)):
            ml_result = predict_alert_suppression(alert_data, tool_context)
            workflow_results["workflow_steps"].append({
                "step": "ml_prediction",
                "result": ml_result
            })
        else:
            workflow_results["workflow_steps"].append({
                "step": "ml_prediction",
                "result": {"skipped": "duplicate_alert"}
            })
        
        # Step 4: Final Decision
        decision_result = make_final_decision(alert_data, workflow_results, tool_context)
        workflow_results["workflow_steps"].append({
            "step": "final_decision",
            "result": decision_result
        })
        
        # Step 5: Execute Action
        action_result = execute_alert_action(alert_data, decision_result, tool_context)
        workflow_results["workflow_steps"].append({
            "step": "action_execution",
            "result": action_result
        })
        
        workflow_results["final_decision"] = decision_result
        workflow_results["action_taken"] = action_result
        
        return {
            "status": "success",
            "workflow_results": workflow_results
        }
        
    except Exception as e:
        return {
            "status": "error",
            "message": f"Error in alert workflow: {str(e)}"
        }

def analyze_alert_initial(alert_data: Dict[str, Any], tool_context: ToolContext) -> Dict[str, Any]:
    """Perform initial alert analysis."""
    try:
        analysis = {
            "alert_id": alert_data.get("alert_id"),
            "host": alert_data.get("host"),
            "severity": alert_data.get("severity", "unknown"),
            "title": alert_data.get("title"),
            "status": alert_data.get("status", "unknown"),
            "source": alert_data.get("source", "unknown"),
            "created_at": alert_data.get("created_at", datetime.now().isoformat())
        }
        
        # Store in context
        if "alert_analyses" not in tool_context.state:
            tool_context.state["alert_analyses"] = []
        tool_context.state["alert_analyses"].append(analysis)
        
        return {
            "status": "success",
            "analysis": analysis
        }
    except Exception as e:
        return {
            "status": "error",
            "message": f"Error in initial analysis: {str(e)}"
        }

def analyze_alert_patterns(alert_data: Dict[str, Any], tool_context: ToolContext) -> Dict[str, Any]:
    """Analyze alert patterns for flapping and self-resolving behavior."""
    try:
        settings = tool_context.state.get("alert_settings", {})
        flapping_window = settings.get("flapping_window_minutes", 30)
        flapping_threshold = settings.get("flapping_threshold", 3)
        self_resolve_threshold_minutes = settings.get("self_resolve_threshold_minutes", 15)
        min_resolution_count = settings.get("min_resolution_count", 3)
        
        project_id = os.getenv('BQ_PROJECT_ID', 'ruckusoperations')
        dataset_id = os.getenv('BQ_DATASET_ID', 'BDC_6')
        
        # Flapping detection query
        flapping_query = f"""
        WITH state_changes AS (
            SELECT 
                created_at,
                resolved_at,
                status,
                LAG(status) OVER (PARTITION BY host, title ORDER BY created_at) as prev_status,
                CASE 
                    WHEN status != LAG(status) OVER (PARTITION BY host, title ORDER BY created_at) 
                    THEN 1 ELSE 0 
                END as state_change
            FROM `{project_id}.{dataset_id}.alerts_data`
            WHERE host = @host
            AND title = @title
            AND created_at >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL {flapping_window} MINUTE)
            ORDER BY created_at DESC
        )
        SELECT 
            COUNT(*) as total_alerts,
            SUM(state_change) as state_changes
        FROM state_changes
        """
        
        # Self-resolving detection query
        self_resolving_query = f"""
        WITH resolution_analysis AS (
            SELECT 
                created_at,
                resolved_at,
                TIMESTAMP_DIFF(resolved_at, created_at, MINUTE) as resolution_time_minutes,
                CASE 
                    WHEN TIMESTAMP_DIFF(resolved_at, created_at, MINUTE) <= {self_resolve_threshold_minutes}
                    THEN 1 ELSE 0 
                END as quick_resolution
            FROM `{project_id}.{dataset_id}.alerts_data`
            WHERE host = @host
            AND title = @title
            AND resolved_at IS NOT NULL
            AND created_at >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 7 DAY)
            ORDER BY created_at DESC
        )
        SELECT 
            COUNT(*) as total_resolved,
            SUM(quick_resolution) as quick_resolutions
        FROM resolution_analysis
        """
        
        query_params = [
            bigquery.ScalarQueryParameter("host", "STRING", alert_data.get("host", "")),
            bigquery.ScalarQueryParameter("title", "STRING", alert_data.get("title", ""))
        ]
        
        job_config = bigquery.QueryJobConfig(query_parameters=query_params)
        
        # Execute flapping analysis
        flapping_job = client.query(flapping_query, job_config=job_config)
        flapping_results = list(flapping_job.result())
        
        # Execute self-resolving analysis
        self_resolving_job = client.query(self_resolving_query, job_config=job_config)
        self_resolving_results = list(self_resolving_job.result())
        
        # Process flapping results
        is_flapping = False
        flapping_confidence = 0.0
        if flapping_results:
            flapping_data = dict(flapping_results[0])
            state_changes = flapping_data.get("state_changes", 0)
            total_alerts = flapping_data.get("total_alerts", 0)
            is_flapping = state_changes >= flapping_threshold and total_alerts > 1
            flapping_confidence = min(state_changes / flapping_threshold, 1.0) if flapping_threshold > 0 else 0.0
        
        # Process self-resolving results
        is_self_resolving = False
        self_resolve_confidence = 0.0
        if self_resolving_results:
            self_resolving_data = dict(self_resolving_results[0])
            total_resolved = self_resolving_data.get("total_resolved", 0)
            quick_resolutions = self_resolving_data.get("quick_resolutions", 0)
            is_self_resolving = (
                total_resolved >= min_resolution_count and 
                quick_resolutions >= (total_resolved * 0.7)
            )
            self_resolve_confidence = quick_resolutions / total_resolved if total_resolved > 0 else 0.0
        
        return {
            "status": "success",
            "flapping_analysis": {
                "is_flapping": is_flapping,
                "confidence": flapping_confidence,
                "state_changes": flapping_results[0].get("state_changes", 0) if flapping_results else 0,
                "total_alerts": flapping_results[0].get("total_alerts", 0) if flapping_results else 0
            },
            "self_resolving_analysis": {
                "is_self_resolving": is_self_resolving,
                "confidence": self_resolve_confidence,
                "total_resolved": self_resolving_results[0].get("total_resolved", 0) if self_resolving_results else 0,
                "quick_resolutions": self_resolving_results[0].get("quick_resolutions", 0) if self_resolving_results else 0
            },
            "pattern_summary": {
                "is_flapping": is_flapping,
                "is_self_resolving": is_self_resolving,
                "should_suppress": is_flapping or is_self_resolving
            }
        }
        
    except Exception as e:
        return {
            "status": "error",
            "message": f"Error analyzing alert patterns: {str(e)}",
            "pattern_summary": {
                "is_flapping": False,
                "is_self_resolving": False,
                "should_suppress": False
            }
        }

def check_alert_duplicates(alert_data: Dict[str, Any], tool_context: ToolContext) -> Dict[str, Any]:
    """Check for duplicate alerts."""
    try:
        # Get duplicate window from settings
        settings = tool_context.state.get("alert_settings", {})
        duplicate_window = settings.get("duplicate_window_minutes", 5)
        
        # Query for recent similar alerts
        project_id = os.getenv('BQ_PROJECT_ID', 'ruckusoperations')
        dataset_id = os.getenv('BQ_DATASET_ID', 'BDC_6')
        query = f"""
        SELECT alert_id, created_at, host, title, severity
        FROM `{project_id}.{dataset_id}.alerts_data`
        WHERE host = @host
        AND title = @title
        AND severity = @severity
        AND created_at >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL {duplicate_window} MINUTE)
        ORDER BY created_at DESC
        LIMIT 10
        """
        
        job_config = bigquery.QueryJobConfig(
            query_parameters=[
                bigquery.ScalarQueryParameter("host", "STRING", alert_data.get("host", "")),
                bigquery.ScalarQueryParameter("title", "STRING", alert_data.get("title", "")),
                bigquery.ScalarQueryParameter("severity", "STRING", alert_data.get("severity", ""))
            ]
        )
        
        query_job = client.query(query, job_config=job_config)
        results = list(query_job.result())
        
        is_duplicate = len(results) > 0
        duplicate_count = len(results)
        
        return {
            "status": "success",
            "is_duplicate": is_duplicate,
            "duplicate_count": duplicate_count,
            "recent_alerts": results,
            "duplicate_window_minutes": duplicate_window
        }
        
    except Exception as e:
        return {
            "status": "error",
            "message": f"Error checking duplicates: {str(e)}",
            "is_duplicate": False
        }

def predict_alert_suppression(alert_data: Dict[str, Any], tool_context: ToolContext) -> Dict[str, Any]:
    """Use ML model to predict alert suppression."""
    try:
        # Prepare features for ML model (matching the BQML model schema)
        features = {
            "source": alert_data.get("source", ""),
            "host": alert_data.get("host", ""),
            "severity": alert_data.get("severity", ""),
            "status": alert_data.get("status", ""),
            "created_at": alert_data.get("created_at", ""),
            "resolved_at": alert_data.get("resolved_at", "")
        }
        
        # Use ML model for prediction
        model_name = os.getenv("ALERT_CLASSIFIER_MODEL", "ruckusoperations.BDC_6.alert_classifier")
        
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
        
        # Create the SQL query using the correct BQML format - as a table, not STRUCT
        sql = f"""
        SELECT * FROM ML.PREDICT(MODEL `{model_name}`, (
            SELECT 
                {format_value(features["source"])} AS source,
                {format_value(features["host"])} AS host,
                {format_value(features["severity"])} AS severity,
                {format_value(features["status"])} AS status,
                {format_value(features["created_at"], True)} AS created_at,
                {format_value(features["resolved_at"], True)} AS resolved_at
        ))
        """
        
        query_job = client.query(sql)
        results = list(query_job.result())
        
        if results:
            prediction = dict(results[0])
            return {
                "status": "success",
                "prediction": prediction,
                "features_used": features
            }
        else:
            return {
                "status": "error",
                "message": "No prediction results returned"
            }
            
    except Exception as e:
        return {
            "status": "error",
            "message": f"Error in ML prediction: {str(e)}"
        }

def make_final_decision(alert_data: Dict[str, Any], workflow_results: Dict[str, Any], tool_context: ToolContext) -> Dict[str, Any]:
    """Make final decision based on all workflow results."""
    try:
        # Get settings
        settings = tool_context.state.get("alert_settings", {})
        suppression_threshold = settings.get("suppression_threshold", 0.8)
        critical_always_forward = settings.get("critical_always_forward", True)
        
        # Check if it's a duplicate
        duplicate_step = next((step for step in workflow_results["workflow_steps"] if step["step"] == "duplicate_check"), None)
        if duplicate_step and duplicate_step["result"].get("is_duplicate", False):
            return {
                "decision": "suppress",
                "reason": "duplicate_alert",
                "confidence": 1.0
            }
        
        # Check for flapping or self-resolving patterns
        pattern_step = next((step for step in workflow_results["workflow_steps"] if step["step"] == "pattern_analysis"), None)
        if pattern_step and pattern_step["result"].get("pattern_summary", {}).get("should_suppress", False):
            pattern_summary = pattern_step["result"].get("pattern_summary", {})
            if pattern_summary.get("is_flapping", False):
                return {
                    "decision": "suppress",
                    "reason": "flapping_alert",
                    "confidence": pattern_step["result"].get("flapping_analysis", {}).get("confidence", 0.8)
                }
            elif pattern_summary.get("is_self_resolving", False):
                return {
                    "decision": "suppress",
                    "reason": "self_resolving_alert",
                    "confidence": pattern_step["result"].get("self_resolving_analysis", {}).get("confidence", 0.8)
                }
        
         # Check if critical (never suppress)
        if alert_data.get("severity") in ["severity-1", "Sev1"] and critical_always_forward:
            return {
                "decision": "forward",
                "reason": "critical_alert_always_forward",
                "confidence": 1.0
            }
        
        # Get ML prediction
        ml_step = next((step for step in workflow_results["workflow_steps"] if step["step"] == "ml_prediction"), None)
        if ml_step and ml_step["result"].get("status") == "success":
            prediction = ml_step["result"].get("prediction", {})
            pred_label = prediction.get("predicted_decision_reason", "keep")
            pred_probs = prediction.get("predicted_decision_reason_probs", [])
            
            # Get confidence for the predicted label
            confidence = 0.0
            if isinstance(pred_probs, list):
                for prob_entry in pred_probs:
                    if prob_entry.get("label") == pred_label:
                        confidence = prob_entry.get("prob", 0.0)
                        break
            
            if pred_label == "suppressed: jira exists" and confidence >= suppression_threshold:
                return {
                    "decision": "suppress",
                    "reason": f"ml_prediction_confidence_{confidence:.2f}",
                    "confidence": confidence
                }
        
        # Default to forward
        return {
            "decision": "forward",
            "reason": "default_forward_no_strong_suppress",
            "confidence": 0.5
        }
        
    except Exception as e:
        return {
            "decision": "forward",
            "reason": f"error_in_decision_{str(e)}",
            "confidence": 0.0
        }

def execute_alert_action(alert_data: Dict[str, Any], decision: Dict[str, Any], tool_context: ToolContext) -> Dict[str, Any]:
    """Execute the final alert action (suppress or forward)."""
    try:
        action = decision.get("decision", "forward")
        reason = decision.get("reason", "unknown")
        
        if action == "suppress":
            # Log suppression
            suppression_record = {
                "alert_id": alert_data.get("alert_id"),
                "timestamp": datetime.now().isoformat(),
                "action": "suppressed",
                "reason": reason,
                "alert_data": alert_data
            }
            
            if "suppressed_alerts" not in tool_context.state:
                tool_context.state["suppressed_alerts"] = []
            tool_context.state["suppressed_alerts"].append(suppression_record)
            
            return {
                "status": "success",
                "action": "suppressed",
                "reason": reason,
                "alert_id": alert_data.get("alert_id")
            }
            
        else:  # forward
            # Log forwarding
            forward_record = {
                "alert_id": alert_data.get("alert_id"),
                "timestamp": datetime.now().isoformat(),
                "action": "forwarded",
                "reason": reason,
                "alert_data": alert_data
            }
            
            if "forwarded_alerts" not in tool_context.state:
                tool_context.state["forwarded_alerts"] = []
            tool_context.state["forwarded_alerts"].append(forward_record)
            
            # Here you would integrate with actual notification systems
            # For now, we'll just log the decision
            
            return {
                "status": "success",
                "action": "forwarded",
                "reason": reason,
                "alert_id": alert_data.get("alert_id")
            }
            
    except Exception as e:
        return {
            "status": "error",
            "message": f"Error executing action: {str(e)}"
        }

# Create FunctionTool wrapper
process_alert_workflow_tool = FunctionTool(func=process_alert_workflow)
