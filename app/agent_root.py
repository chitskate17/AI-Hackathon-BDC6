import os
from datetime import date

from google.adk.agents import Agent
from google.adk.agents.callback_context import CallbackContext
from google.genai import types

# Import sub-agents
from .agents.data_agent.agent import data_agent
from .agents.ml_agent.agent import ml_agent
from .agents.alert_agent.agent import alert_agent

# Import root prompts
from .prompts import return_instructions_root

# Import workflow tools
from .tools.alert_workflow import process_alert_workflow_tool

date_today = date.today()

def setup_before_agent_call(callback_context: CallbackContext):
    """Setup before calling the root agent."""
    if "all_db_settings" not in callback_context.state:
        callback_context.state["all_db_settings"] = {"use_database": "BigQuery"}

        # Alert management settings
        if "alert_settings" not in callback_context.state:
            callback_context.state["alert_settings"] = {
                "suppression_threshold": 0.8,
                "duplicate_window_minutes": 5,
                "critical_always_forward": True,
                "flapping_window_minutes": 30,
                "flapping_threshold": 3,
                "self_resolve_threshold_minutes": 15,
                "min_resolution_count": 3
            }

    # Database settings for sub-agents
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


root_agent = Agent(
    model=os.getenv("ROOT_AGENT_MODEL", "gemini-2.0-flash-exp"),
    name="alert_management_orchestrator",
    instruction=return_instructions_root(),
    global_instruction=f"You are an Alert Management Multi-Agent Orchestrator System for suppressing noisy alerts. Today's date: {date_today}",
    sub_agents=[data_agent, ml_agent, alert_agent],
    tools=[process_alert_workflow_tool],
    before_agent_callback=setup_before_agent_call,
    generate_content_config=types.GenerateContentConfig(temperature=0.01),
)
