import os
from google.adk.agents import Agent
from google.adk.agents.callback_context import CallbackContext
from google.genai import types

from .tools import call_db_agent
from .prompts import return_instructions_data_agent

def setup_before_agent_call(callback_context: CallbackContext):
    if "database_settings" not in callback_context.state:
        import os
        callback_context.state["database_settings"] = {
            "bq_data_project_id": os.getenv("BQ_PROJECT_ID", "ruckusoperations"),
            "bq_dataset_id": os.getenv("BQ_DATASET_ID", "BDC_6"),
            "bq_schema_and_samples": f"""
            Table: `{os.getenv('BQ_PROJECT_ID', 'ruckusoperations')}.{os.getenv('BQ_DATASET_ID', 'BDC_6')}.alerts_data`
            Total Rows: 149,899
            
            Schema:
            - source: STRING (values: 'pagerduty', 'jira', 'icinga')
            - alert_id: STRING (filled for pagerduty/jira, may be NULL for icinga)
            - title: STRING (always filled)
            - host: STRING (always filled)
            - severity: STRING (values: severity-1, severity-2, severity-3, Sev1, Sev2, Sev3) - filled for pagerduty/jira, may be NULL for icinga
            - status: STRING (filled for pagerduty/jira, may be NULL for icinga)
            - created_at: TIMESTAMP (always filled)
            - resolved_at: TIMESTAMP (filled for pagerduty/jira, may be NULL for icinga)
            - decision_reason: STRING (values: 'keep' or 'suppressed: jira exists')
            
            Data Completeness:
            - pagerduty/jira: All fields filled
            - icinga: Only title, host, created_at, decision_reason filled
            
            BQML Model: `{os.getenv('BQ_PROJECT_ID', 'ruckusoperations')}.{os.getenv('BQ_DATASET_ID', 'BDC_6')}.alert_classifier`
            """
        }

data_agent = Agent(
    model=os.getenv("DATA_AGENT_MODEL", "gemini-2.0-flash-exp"),
    name="data_agent",
    instruction=return_instructions_data_agent(),
    tools=[call_db_agent],
    before_agent_callback=setup_before_agent_call,
    generate_content_config=types.GenerateContentConfig(temperature=0.01),
)
