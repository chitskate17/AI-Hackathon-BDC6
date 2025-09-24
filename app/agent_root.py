# app/agent_root.py
from google.adk.agents import Agent
from google.adk.tools import FunctionTool

from app.tools.bq_tools import run_sql, write_table
from app.tools.ml_tools import predict_features, explain_features
from app.tools.decision import decide
from app.tools.notify import forward_to_slack

# ----------------------------
# Tools wrapped using FunctionTool
# ----------------------------

bq_tool = FunctionTool(
    func=run_sql,
    name="run_sql",
    description="Execute SQL query in BigQuery and return results as JSON",
    args_schema={
        "sql": {"type": "string", "description": "SQL query string"},
        "max_rows": {"type": "integer", "description": "Maximum rows to fetch", "default": 1000}
    },
    return_schema={"type": "object", "description": "Query results as list of dicts"}
)

predict_tool = FunctionTool(
    func=predict_features,
    name="predict_alert",
    description="Predict if an alert should be suppressed or forwarded using BQML model",
    args_schema={"alert": {"type": "object", "description": "Alert data dictionary"}},
    return_schema={"type": "object", "description": "Prediction result with label and probability"}
)

explain_tool = FunctionTool(
    func=explain_features,
    name="explain_decision",
    description="Provide rationale for alert suppression/forwarding",
    args_schema={
        "alert": {"type": "object", "description": "Alert dictionary"},
        "prediction": {"type": "object", "description": "Prediction dictionary"}
    },
    return_schema={"type": "object", "description": "Decision explanation"}
)

decision_tool = FunctionTool(
    func=decide,
    name="decision_tool",
    description="Decide whether to suppress or forward an alert based on ML predictions and rules",
    args_schema={
        "alert_row": {"type": "object", "description": "Alert data dictionary"},
        "ml_pred": {"type": "object", "description": "ML prediction dictionary"}
    },
    return_schema={"type": "object", "description": "Decision result with 'decision' and 'reason' fields"}
)

notify_tool = FunctionTool(
    func=forward_to_slack,
    name="forward_alert",
    description="Forward actionable alert to target channel",
    args_schema={"alert": {"type": "object", "description": "Alert dictionary"}},
    return_schema={"type": "object", "description": "Forwarding status"}
)

# ----------------------------
# Root agent
# ----------------------------

root_agent = Agent(
    name="root_alerts_agent",
    model="gemini-1.5-mini",  # change if needed
    description="Orchestrator that processes alerts: query BQ, call ML, decide, notify",
    instruction="""
        Use the provided tools to fetch pending alerts, call prediction tool,
        make a decision using the decision tool and forward actionable alerts.
        Output a short human-friendly summary for each batch processed.
    """,
    tools=[bq_tool, predict_tool, explain_tool, decision_tool, notify_tool]
)

def get_agent():
    return root_agent
