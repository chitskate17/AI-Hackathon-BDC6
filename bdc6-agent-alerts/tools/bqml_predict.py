from google.cloud import bigquery

bq_client = bigquery.Client()

BQML_MODEL = "ruckusoperations.BDC_6.alert_priority_bt"


def predict_alert_priority(
    number: int,
    incident_type: str,
    urgency: str,
    service: str,
    status: str = "Open",
    auto_resolved: str = "No", 
    tta_seconds: int = 300,
    ttr_seconds: int = 1800,
    response_effort: str = "Medium"
) -> dict:
    """Uses BQML model to predict incident priority (Sev1, Sev2, Sev3) with confidence scores.
    
    Args:
        number (int): Incident number/ID
        incident_type (str): Type of incident (e.g., 'Network', 'Server', 'Application')
        urgency (str): Incident urgency level (e.g., 'High', 'Medium', 'Low')
        service (str): Affected service name
        status (str): Current incident status (default: 'Open')
        auto_resolved (str): Whether incident auto-resolved ('Yes'/'No', default: 'No')
        tta_seconds (int): Time to acknowledge in seconds (default: 300)
        ttr_seconds (int): Time to resolve in seconds (default: 1800)
        response_effort (str): Response effort level (default: 'Medium')
        
    Returns:
        dict: status, predicted priority, confidence probabilities, and input features
    """
    try:
        query = f"""
        SELECT
          Number,
          predicted_Priority AS predicted_priority,
          MAX(CASE WHEN probs.label = 'Sev1' THEN probs.prob END) AS prob_Sev1,
          MAX(CASE WHEN probs.label = 'Sev2' THEN probs.prob END) AS prob_Sev2,
          MAX(CASE WHEN probs.label = 'Sev3' THEN probs.prob END) AS prob_Sev3
        FROM
          ML.PREDICT(MODEL `{BQML_MODEL}`,
            (
              SELECT
                {number} AS Number,
                '{incident_type}' AS `Incident Type`,
                '{urgency}' AS Urgency,
                '{service}' AS Service,
                '{status}' AS Status,
                '{auto_resolved}' AS `Auto Resolved`,
                {tta_seconds} AS `TTA in seconds`,
                {ttr_seconds} AS `TTR in seconds`,
                '{response_effort}' AS `Response Effort`
            )
          ), UNNEST(predicted_Priority_probs) AS probs
        GROUP BY Number, predicted_Priority
        """
        results = bq_client.query(query).result()
        for row in results:
            return {
                "status": "success", 
                "incident_number": row.Number,
                "predicted_priority": row.predicted_priority,
                "confidence_scores": {
                    "Sev1_probability": row.prob_Sev1 or 0.0,
                    "Sev2_probability": row.prob_Sev2 or 0.0, 
                    "Sev3_probability": row.prob_Sev3 or 0.0
                },
                "input_features": {
                    "incident_type": incident_type,
                    "urgency": urgency,
                    "service": service,
                    "status": status,
                    "auto_resolved": auto_resolved,
                    "tta_seconds": tta_seconds,
                    "response_effort": response_effort
                }
            }
        return {
            "status": "error",
            "error_message": "No prediction result returned from BQML model"
        }
    except Exception as e:
        return {
            "status": "error",
            "error_message": f"Error predicting incident severity: {str(e)}"
        }

