from google.cloud import bigquery

bq_client = bigquery.Client()

def alert_summary(last_hours: int = 1) -> dict:
    """Returns alert metrics (total, suppressed, forwarded, noise reduction %).
    
    Args:
        last_hours (int): Number of hours to look back for alert data (default: 1).
        
    Returns:
        dict: status and alert metrics or error message.
    """
    try:
        # Note: Using BDC6_TABLE (raw data) instead of alert_priority_bt (BQML model)
        # Adjust column names based on your actual table structure
        query = f"""
        WITH alerts AS (
          SELECT 
            Number,
            `Incident Type` AS incident_type,
            Status,
            Urgency,
            Service,
            `Auto Resolved` AS auto_resolved,
            `Response Effort` AS response_effort
          FROM `ruckusoperations.BDC_6.BDC6_TABLE`
          -- Note: Add timestamp filter when you have a timestamp column
          -- WHERE creation_time >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL {last_hours} HOUR)
        )
        SELECT
          COUNT(*) AS total,
          SUM(CASE WHEN Status = 'Closed' THEN 1 ELSE 0 END) AS resolved,
          SUM(CASE WHEN Status = 'Open' THEN 1 ELSE 0 END) AS open,
          SUM(CASE WHEN auto_resolved = 'Yes' THEN 1 ELSE 0 END) AS auto_resolved,
          SUM(CASE WHEN Urgency = 'High' THEN 1 ELSE 0 END) AS high_urgency,
          SUM(CASE WHEN Urgency = 'Medium' THEN 1 ELSE 0 END) AS medium_urgency,
          SUM(CASE WHEN Urgency = 'Low' THEN 1 ELSE 0 END) AS low_urgency
        FROM alerts
        """
        results = bq_client.query(query).result()
        for row in results:
            total = row.total
            resolved = row.resolved
            open_incidents = row.open
            auto_resolved = row.auto_resolved
            high_urgency = row.high_urgency
            medium_urgency = row.medium_urgency
            low_urgency = row.low_urgency
            
            # Calculate metrics
            resolution_rate = round((resolved / total) * 100, 2) if total > 0 else 0
            auto_resolution_rate = round((auto_resolved / total) * 100, 2) if total > 0 else 0
            
            return {
                "status": "success",
                "query_scope": f"All incidents (add timestamp filter for last {last_hours} hours)",
                "total_incidents": total,
                "open_incidents": open_incidents,
                "resolved_incidents": resolved, 
                "auto_resolved": auto_resolved,
                "resolution_rate_percent": resolution_rate,
                "auto_resolution_rate_percent": auto_resolution_rate,
                "urgency_breakdown": {
                    "high": high_urgency,
                    "medium": medium_urgency, 
                    "low": low_urgency
                }
            }
        return {
            "status": "error", 
            "error_message": "No alert data found"
        }
    except Exception as e:
        return {
            "status": "error",
            "error_message": f"Error retrieving alert metrics: {str(e)}"
        }

