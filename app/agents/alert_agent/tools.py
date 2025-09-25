import os
import time
from datetime import datetime, timedelta
from typing import Dict, List, Any
from google.adk.tools import FunctionTool
from google.adk.tools import ToolContext
from google.cloud import bigquery

# Initialize BigQuery client
client = bigquery.Client()

def analyze_alert(alert_data: Dict[str, Any], tool_context: ToolContext) -> Dict[str, Any]:
    """
    Analyze an incoming alert for patterns and characteristics.
    
    Args:
        alert_data: Dictionary containing alert information
        tool_context: ADK tool context
    
    Returns:
        Analysis results including patterns and characteristics
    """
    try:
        # Extract key alert characteristics
        analysis = {
            "alert_id": alert_data.get("alert_id"),
            "created_at": alert_data.get("created_at", datetime.now().isoformat()),
            "host": alert_data.get("host"),
            "severity": alert_data.get("severity", "unknown"),
            "title": alert_data.get("title"),
            "status": alert_data.get("status", "unknown"),
            "source": alert_data.get("source", "unknown"),
            "analysis_timestamp": datetime.now().isoformat()
        }
        
        # Store analysis in context for other tools
        if "alert_analyses" not in tool_context.state:
            tool_context.state["alert_analyses"] = []
        tool_context.state["alert_analyses"].append(analysis)
        
        return {
            "status": "success",
            "analysis": analysis,
            "message": "Alert analyzed successfully"
        }
        
    except Exception as e:
        return {
            "status": "error",
            "message": f"Error analyzing alert: {str(e)}"
        }

def check_duplicate_alerts(alert_data: Dict[str, Any], tool_context: ToolContext) -> Dict[str, Any]:
    """
    Check if this alert is a duplicate of recent alerts.
    
    Args:
        alert_data: Dictionary containing alert information
        tool_context: ADK tool context
    
    Returns:
        Duplicate check results
    """
    try:
        # Get duplicate window from settings
        settings = tool_context.state.get("alert_settings", {})
        duplicate_window = settings.get("duplicate_window_minutes", 5)
        
        # Query for recent similar alerts
        project_id = os.getenv('BQ_PROJECT_ID', 'ruckusoperations')
        dataset_id = os.getenv('BQ_DATASET_ID', 'BDC_6')
        query = f"""
        SELECT alert_id, created_at, host, title, severity, decision_reason
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

def get_alert_history(alert_data: Dict[str, Any], tool_context: ToolContext) -> Dict[str, Any]:
    """
    Get historical alert patterns for the same host/type.
    
    Args:
        alert_data: Dictionary containing alert information
        tool_context: ADK tool context
    
    Returns:
        Historical alert data
    """
    try:
        # Query for historical alerts from the same host
        project_id = os.getenv('BQ_PROJECT_ID', 'ruckusoperations')
        dataset_id = os.getenv('BQ_DATASET_ID', 'BDC_6')
        query = f"""
        SELECT 
            COUNT(*) as total_alerts,
            COUNT(DISTINCT DATE(created_at)) as days_with_alerts,
            AVG(CASE WHEN decision_reason = 'suppressed: jira exists' THEN 1 ELSE 0 END) as suppression_rate,
            MAX(created_at) as last_alert_time
        FROM `{project_id}.{dataset_id}.alerts_data`
        WHERE host = @host
        AND created_at >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 7 DAY)
        """
        
        job_config = bigquery.QueryJobConfig(
            query_parameters=[
                bigquery.ScalarQueryParameter("host", "STRING", alert_data.get("host", ""))
            ]
        )
        
        query_job = client.query(query, job_config=job_config)
        results = list(query_job.result())
        
        history = results[0] if results else {}
        
        return {
            "status": "success",
            "history": dict(history),
            "message": "Alert history retrieved successfully"
        }
        
    except Exception as e:
        return {
            "status": "error",
            "message": f"Error getting alert history: {str(e)}",
            "history": {}
        }

def suppress_alert(alert_data: Dict[str, Any], reason: str, tool_context: ToolContext) -> Dict[str, Any]:
    """
    Suppress an alert and log the decision.
    
    Args:
        alert_data: Dictionary containing alert information
        reason: Reason for suppression
        tool_context: ADK tool context
    
    Returns:
        Suppression result
    """
    try:
        # Log suppression decision
        suppression_record = {
            "alert_id": alert_data.get("alert_id"),
            "timestamp": datetime.now().isoformat(),
            "action": "suppressed",
            "reason": reason,
            "alert_data": alert_data
        }
        
        # Store in context
        if "suppressed_alerts" not in tool_context.state:
            tool_context.state["suppressed_alerts"] = []
        tool_context.state["suppressed_alerts"].append(suppression_record)
        
        return {
            "status": "success",
            "action": "suppressed",
            "reason": reason,
            "alert_id": alert_data.get("alert_id"),
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        return {
            "status": "error",
            "message": f"Error suppressing alert: {str(e)}"
        }

def forward_alert(alert_data: Dict[str, Any], reason: str, tool_context: ToolContext) -> Dict[str, Any]:
    """
    Forward an alert to the appropriate channel.
    
    Args:
        alert_data: Dictionary containing alert information
        reason: Reason for forwarding
        tool_context: ADK tool context
    
    Returns:
        Forward result
    """
    try:
        # Log forwarding decision
        forward_record = {
            "alert_id": alert_data.get("alert_id"),
            "timestamp": datetime.now().isoformat(),
            "action": "forwarded",
            "reason": reason,
            "alert_data": alert_data
        }
        
        # Store in context
        if "forwarded_alerts" not in tool_context.state:
            tool_context.state["forwarded_alerts"] = []
        tool_context.state["forwarded_alerts"].append(forward_record)
        
        # Here you would integrate with actual notification systems
        # For now, we'll just log the decision
        
        return {
            "status": "success",
            "action": "forwarded",
            "reason": reason,
            "alert_id": alert_data.get("alert_id"),
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        return {
            "status": "error",
            "message": f"Error forwarding alert: {str(e)}"
        }

def detect_flapping_alerts(alert_data: Dict[str, Any], tool_context: ToolContext) -> Dict[str, Any]:
    """Detect if this alert is part of a flapping pattern (rapid state changes)."""
    try:
        settings = tool_context.state.get("alert_settings", {})
        flapping_window = settings.get("flapping_window_minutes", 30)  # 30 minutes default
        flapping_threshold = settings.get("flapping_threshold", 3)  # 3 state changes default
        
        project_id = os.getenv('BQ_PROJECT_ID', 'ruckusoperations')
        dataset_id = os.getenv('BQ_DATASET_ID', 'BDC_6')
        
        # Query to find rapid state changes for this host/title combination
        query = f"""
        WITH recent_alerts AS (
            SELECT 
                created_at,
                resolved_at,
                status,
                ROW_NUMBER() OVER (ORDER BY created_at) as row_num
            FROM `{project_id}.{dataset_id}.alerts_data`
            WHERE host = @host
            AND title = @title
            AND created_at >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL {flapping_window} MINUTE)
            ORDER BY created_at
        ),
        state_changes AS (
            SELECT 
                created_at,
                resolved_at,
                status,
                LAG(status) OVER (ORDER BY created_at) as prev_status,
                CASE 
                    WHEN status != LAG(status) OVER (ORDER BY created_at) 
                    THEN 1 ELSE 0 
                END as state_change
            FROM recent_alerts
        )
        SELECT 
            COUNT(*) as total_alerts,
            SUM(state_change) as state_changes,
            COUNT(DISTINCT DATE(created_at)) as days_with_alerts,
            MIN(created_at) as first_alert,
            MAX(created_at) as last_alert
        FROM state_changes
        """
        
        query_params = [
            bigquery.ScalarQueryParameter("host", "STRING", alert_data.get("host", "")),
            bigquery.ScalarQueryParameter("title", "STRING", alert_data.get("title", ""))
        ]
        
        job_config = bigquery.QueryJobConfig(query_parameters=query_params)
        query_job = client.query(query, job_config=job_config)
        results = list(query_job.result())
        
        if results:
            result = dict(results[0])
            state_changes = result.get("state_changes", 0)
            total_alerts = result.get("total_alerts", 0)
            
            # Determine if this is flapping
            is_flapping = state_changes >= flapping_threshold and total_alerts > 1
            
            return {
                "status": "success",
                "is_flapping": is_flapping,
                "state_changes": state_changes,
                "total_alerts": total_alerts,
                "flapping_threshold": flapping_threshold,
                "flapping_window_minutes": flapping_window,
                "confidence": min(state_changes / flapping_threshold, 1.0) if flapping_threshold > 0 else 0.0,
                "pattern_details": {
                    "days_with_alerts": result.get("days_with_alerts", 0),
                    "first_alert": result.get("first_alert"),
                    "last_alert": result.get("last_alert")
                }
            }
        else:
            return {
                "status": "success",
                "is_flapping": False,
                "state_changes": 0,
                "total_alerts": 0,
                "message": "No historical data found for flapping analysis"
            }
            
    except Exception as e:
        return {
            "status": "error",
            "message": f"Error detecting flapping alerts: {str(e)}",
            "is_flapping": False
        }

def detect_self_resolving_alerts(alert_data: Dict[str, Any], tool_context: ToolContext) -> Dict[str, Any]:
    """Detect if this alert tends to resolve itself quickly without human intervention."""
    try:
        settings = tool_context.state.get("alert_settings", {})
        self_resolve_threshold_minutes = settings.get("self_resolve_threshold_minutes", 15)  # 15 minutes default
        min_resolution_count = settings.get("min_resolution_count", 3)  # Need at least 3 examples
        
        project_id = os.getenv('BQ_PROJECT_ID', 'ruckusoperations')
        dataset_id = os.getenv('BQ_DATASET_ID', 'BDC_6')
        
        # Query to analyze resolution patterns for this host/title combination
        query = f"""
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
            SUM(quick_resolution) as quick_resolutions,
            AVG(resolution_time_minutes) as avg_resolution_time,
            MIN(resolution_time_minutes) as min_resolution_time,
            MAX(resolution_time_minutes) as max_resolution_time,
            STDDEV(resolution_time_minutes) as resolution_time_stddev
        FROM resolution_analysis
        """
        
        query_params = [
            bigquery.ScalarQueryParameter("host", "STRING", alert_data.get("host", "")),
            bigquery.ScalarQueryParameter("title", "STRING", alert_data.get("title", ""))
        ]
        
        job_config = bigquery.QueryJobConfig(query_parameters=query_params)
        query_job = client.query(query, job_config=job_config)
        results = list(query_job.result())
        
        if results:
            result = dict(results[0])
            total_resolved = result.get("total_resolved", 0)
            quick_resolutions = result.get("quick_resolutions", 0)
            avg_resolution_time = result.get("avg_resolution_time", 0)
            
            # Determine if this tends to self-resolve
            is_self_resolving = (
                total_resolved >= min_resolution_count and 
                quick_resolutions >= (total_resolved * 0.7)  # 70% of resolutions are quick
            )
            
            self_resolve_confidence = quick_resolutions / total_resolved if total_resolved > 0 else 0.0
            
            return {
                "status": "success",
                "is_self_resolving": is_self_resolving,
                "total_resolved": total_resolved,
                "quick_resolutions": quick_resolutions,
                "self_resolve_confidence": self_resolve_confidence,
                "resolution_stats": {
                    "avg_resolution_time_minutes": avg_resolution_time,
                    "min_resolution_time_minutes": result.get("min_resolution_time", 0),
                    "max_resolution_time_minutes": result.get("max_resolution_time", 0),
                    "resolution_time_stddev": result.get("resolution_time_stddev", 0)
                },
                "thresholds": {
                    "self_resolve_threshold_minutes": self_resolve_threshold_minutes,
                    "min_resolution_count": min_resolution_count
                }
            }
        else:
            return {
                "status": "success",
                "is_self_resolving": False,
                "total_resolved": 0,
                "quick_resolutions": 0,
                "message": "No resolution history found for self-resolving analysis"
            }
            
    except Exception as e:
        return {
            "status": "error",
            "message": f"Error detecting self-resolving alerts: {str(e)}",
            "is_self_resolving": False
        }

def analyze_alert_patterns(alert_data: Dict[str, Any], tool_context: ToolContext) -> Dict[str, Any]:
    """Comprehensive analysis of alert patterns including flapping and self-resolving behavior."""
    try:
        # Get flapping analysis
        flapping_result = detect_flapping_alerts(alert_data, tool_context)
        
        # Get self-resolving analysis
        self_resolving_result = detect_self_resolving_alerts(alert_data, tool_context)
        
        # Combine results
        combined_analysis = {
            "status": "success",
            "alert_id": alert_data.get("alert_id"),
            "host": alert_data.get("host"),
            "title": alert_data.get("title"),
            "flapping_analysis": flapping_result,
            "self_resolving_analysis": self_resolving_result,
            "pattern_summary": {
                "is_flapping": flapping_result.get("is_flapping", False),
                "is_self_resolving": self_resolving_result.get("is_self_resolving", False),
                "should_suppress": (
                    flapping_result.get("is_flapping", False) or 
                    self_resolving_result.get("is_self_resolving", False)
                )
            }
        }
        
        return combined_analysis
        
    except Exception as e:
        return {
            "status": "error",
            "message": f"Error analyzing alert patterns: {str(e)}"
        }

# Create FunctionTool wrappers
analyze_alert_tool = FunctionTool(func=analyze_alert)
check_duplicate_alerts_tool = FunctionTool(func=check_duplicate_alerts)
get_alert_history_tool = FunctionTool(func=get_alert_history)
suppress_alert_tool = FunctionTool(func=suppress_alert)
forward_alert_tool = FunctionTool(func=forward_alert)
detect_flapping_alerts_tool = FunctionTool(func=detect_flapping_alerts)
detect_self_resolving_alerts_tool = FunctionTool(func=detect_self_resolving_alerts)
analyze_alert_patterns_tool = FunctionTool(func=analyze_alert_patterns)
