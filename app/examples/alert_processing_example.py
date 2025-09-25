"""
Example script demonstrating the Alert Management Multi-Agent System
"""

import os
import json
from datetime import datetime

# Example alert data for testing
SAMPLE_ALERTS = [
    {
        "alert_id": "alert_001",
        "host": "web-server-01",
        "severity": "severity-2",
        "title": "High CPU Usage",
        "description": "CPU usage is above 80% for the last 5 minutes",
        "status": "active",
        "source": "monitoring_system",
        "timestamp": datetime.now().isoformat()
    },
    {
        "alert_id": "alert_002",
        "host": "db-server-01",
        "severity": "Sev1",
        "title": "Database Connection Failed",
        "description": "Unable to connect to primary database",
        "status": "active",
        "source": "database_monitor",
        "timestamp": datetime.now().isoformat()
    },
    {
        "alert_id": "alert_003",
        "host": "web-server-01",
        "severity": "severity-3",
        "title": "Scheduled Maintenance",
        "description": "Scheduled maintenance window starting",
        "status": "active",
        "source": "scheduler",
        "timestamp": datetime.now().isoformat()
    },
    {
        "alert_id": "alert_004",
        "host": "web-server-01",
        "severity": "severity-2",
        "title": "High CPU Usage",
        "description": "CPU usage is above 80% for the last 5 minutes",
        "status": "active",
        "source": "monitoring_system",
        "timestamp": datetime.now().isoformat()
    }
]

def demonstrate_alert_processing():
    """
    Demonstrate the alert processing workflow.
    This would typically be called by the ADK web UI.
    """
    print("=== Alert Management Multi-Agent System Demo ===\n")
    
    for i, alert in enumerate(SAMPLE_ALERTS, 1):
        print(f"Processing Alert {i}: {alert['alert_id']}")
        print(f"Host: {alert['host']}")
        print(f"Severity: {alert['severity']}")
        print(f"Title: {alert['title']}")
        
        # Simulate the workflow processing
        result = simulate_alert_workflow(alert)
        
        print(f"Decision: {result['decision']}")
        print(f"Reason: {result['reason']}")
        print(f"Confidence: {result.get('confidence', 'N/A')}")
        print("-" * 50)
    
    print("\n=== Summary ===")
    print("The system successfully processed all alerts with the following logic:")
    print("- Critical alerts are always forwarded")
    print("- Duplicate alerts are suppressed")
    print("- ML predictions determine suppression for other alerts")
    print("- All decisions are logged with reasoning")

def simulate_alert_workflow(alert_data):
    """
    Simulate the alert workflow processing.
    In the actual system, this would be handled by the multi-agent orchestrator.
    """
    # Simulate duplicate check
    is_duplicate = check_for_duplicates(alert_data)
    
    # Simulate ML prediction
    ml_prediction = simulate_ml_prediction(alert_data)
    
    # Make decision
    decision = make_decision(alert_data, is_duplicate, ml_prediction)
    
    return decision

def check_for_duplicates(alert_data):
    """Simulate duplicate detection."""
    # In a real system, this would query the database
    # For demo purposes, we'll simulate based on alert_004 being a duplicate of alert_001
    if alert_data["alert_id"] == "alert_004":
        return True
    return False

def simulate_ml_prediction(alert_data):
    """Simulate ML prediction for alert suppression."""
    # Simulate different confidence levels based on alert characteristics
    if alert_data["severity"] == "severity-3":
        return {"predicted_label": "suppress", "confidence": 0.9}
    elif alert_data["severity"] == "severity-2" and alert_data["title"] == "High CPU Usage":
        return {"predicted_label": "suppress", "confidence": 0.7}
    else:
        return {"predicted_label": "forward", "confidence": 0.8}

def make_decision(alert_data, is_duplicate, ml_prediction):
    """Make final decision based on all factors."""
    # Critical alerts are never suppressed
    if alert_data["severity"] in ["severity-1", "Sev1"]:
        return {
            "decision": "forward",
            "reason": "critical_severity_always_forward",
            "confidence": 1.0
        }
    
    # Duplicate alerts are suppressed
    if is_duplicate:
        return {
            "decision": "suppress",
            "reason": "duplicate_alert",
            "confidence": 1.0
        }
    
    # Use ML prediction with confidence threshold
    if (ml_prediction["predicted_label"] == "suppress" and 
        ml_prediction["confidence"] >= 0.8):
        return {
            "decision": "suppress",
            "reason": f"ml_prediction_confidence_{ml_prediction['confidence']:.2f}",
            "confidence": ml_prediction["confidence"]
        }
    
    # Default to forward
    return {
        "decision": "forward",
        "reason": "default_forward_no_strong_suppress",
        "confidence": 0.5
    }

if __name__ == "__main__":
    demonstrate_alert_processing()
