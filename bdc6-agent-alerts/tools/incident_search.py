from google.cloud import bigquery
from typing import Optional

bq_client = bigquery.Client()

def search_incidents(
    urgency: Optional[str] = None,
    incident_type: Optional[str] = None,
    status: Optional[str] = None,
    service: Optional[str] = None,
    auto_resolved: Optional[str] = None,
    response_effort: Optional[str] = None,
    limit: int = 20
) -> dict:
    """Search and retrieve actual incidents from BDC6_TABLE based on criteria.
    
    Args:
        urgency (str, optional): Filter by urgency ('High', 'Medium', 'Low')
        incident_type (str, optional): Filter by incident type (e.g., 'Network', 'Server', 'Application') 
        status (str, optional): Filter by status ('Open', 'Closed', etc.)
        service (str, optional): Filter by service name
        auto_resolved (str, optional): Filter by auto-resolution ('Yes', 'No')
        response_effort (str, optional): Filter by response effort ('High', 'Medium', 'Low')
        limit (int): Maximum number of incidents to return (default: 20, max: 100)
        
    Returns:
        dict: status and list of matching incidents or error message
    """
    try:
        # Build WHERE clause based on provided filters
        where_conditions = []
        
        if urgency:
            where_conditions.append(f"Urgency = '{urgency}'")
        if incident_type:
            where_conditions.append(f"`Incident Type` = '{incident_type}'")
        if status:
            where_conditions.append(f"Status = '{status}'")
        if service:
            where_conditions.append(f"Service = '{service}'")
        if auto_resolved:
            where_conditions.append(f"`Auto Resolved` = '{auto_resolved}'")
        if response_effort:
            where_conditions.append(f"`Response Effort` = '{response_effort}'")
            
        where_clause = " AND ".join(where_conditions) if where_conditions else "1=1"
        
        # Limit to reasonable max
        limit = min(limit, 100)
        
        query = f"""
        SELECT 
            Number,
            `Incident Type` AS incident_type,
            Urgency,
            Service,
            Status,
            `Auto Resolved` AS auto_resolved,
            `TTA in seconds` AS tta_seconds,
            `TTR in seconds` AS ttr_seconds,
            `Response Effort` AS response_effort
        FROM `ruckusoperations.BDC_6.BDC6_TABLE`
        WHERE {where_clause}
        ORDER BY Number DESC
        LIMIT {limit}
        """
        
        results = bq_client.query(query).result()
        
        incidents = []
        for row in results:
            incidents.append({
                "number": row.Number,
                "incident_type": row.incident_type,
                "urgency": row.Urgency,
                "service": row.Service,
                "status": row.Status,
                "auto_resolved": row.auto_resolved,
                "tta_seconds": row.tta_seconds,
                "ttr_seconds": row.ttr_seconds,
                "response_effort": row.response_effort
            })
        
        # Build filter description
        applied_filters = []
        if urgency: applied_filters.append(f"urgency={urgency}")
        if incident_type: applied_filters.append(f"type={incident_type}")
        if status: applied_filters.append(f"status={status}")
        if service: applied_filters.append(f"service={service}")
        if auto_resolved: applied_filters.append(f"auto_resolved={auto_resolved}")
        if response_effort: applied_filters.append(f"effort={response_effort}")
        
        filter_description = f" with filters: {', '.join(applied_filters)}" if applied_filters else " (no filters applied)"
        
        return {
            "status": "success",
            "total_found": len(incidents),
            "filters_applied": filter_description,
            "incidents": incidents,
            "note": f"Showing latest {len(incidents)} incidents{filter_description}"
        }
        
    except Exception as e:
        return {
            "status": "error",
            "error_message": f"Error searching incidents: {str(e)}"
        }
