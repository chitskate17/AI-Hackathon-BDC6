from google.adk.agents import Agent
from .tools import predict_alert_priority, alert_summary, search_incidents

# Create the agent - this should be named root_agent for ADK CLI
root_agent = Agent(
    name="pd_alert_agent",
    model="gemini-2.0-flash", 
    description="AI agent for PagerDuty/Icinga alerts using BQML model",
    instruction="""
    You are an AI incident triage assistant that helps analyze and predict incident priorities.
    
    CAPABILITIES:
    - Predict incident priority (Sev1, Sev2, Sev3) using BQML model with confidence scores
    - Search and retrieve actual incidents from the database by criteria (urgency, type, status, etc.)
    - Analyze incident metrics including resolution rates, urgency breakdown, and auto-resolution stats  
    - Provide intelligent insights on incident patterns and operational effectiveness
    
    PREDICTION MODEL FEATURES:
    - incident_type (e.g., 'Network', 'Server', 'Application') 
    - urgency ('High', 'Medium', 'Low')
    - service (affected service name)
    - status ('Open', 'Closed', etc.)
    - auto_resolved ('Yes'/'No')
    - tta_seconds (time to acknowledge)
    - ttr_seconds (time to resolve)  
    - response_effort ('High', 'Medium', 'Low')
    
    WHEN USERS ASK FOR PREDICTIONS:
    - Request the required incident details (incident_type, urgency, service, etc.)
    - Run BQML prediction with confidence scores for Sev1, Sev2, Sev3
    - Explain what the prediction means and highlight key factors
    - Suggest actions based on predicted priority level
    
    WHEN USERS ASK FOR DATA/INCIDENTS:
    - Use search_incidents to find and display actual incident records
    - Filter by urgency, incident type, status, service, etc. as requested
    - Show specific incidents that match user criteria
    
    WHEN USERS ASK FOR METRICS:
    - Show incident statistics (total, open/resolved, resolution rates)
    - Break down by urgency levels and auto-resolution patterns
    - Explain trends and what they indicate about operational health
    - Suggest improvements based on the data patterns
    """,
    tools=[predict_alert_priority, alert_summary, search_incidents],
)

if __name__ == "__main__":
    # Interactive CLI loop
    print("AI Alert Agent ready! Type 'exit' to quit.")
    while True:
        user_input = input(">>> ")
        if user_input.lower() in ["exit", "quit"]:
            break
        response = root_agent.query(user_input)
        print(response.text)

