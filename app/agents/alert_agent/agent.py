import os
from google.adk.agents import Agent
from google.adk.agents.callback_context import CallbackContext
from google.genai import types

from .tools import (
    analyze_alert_tool,
    check_duplicate_alerts_tool,
    get_alert_history_tool,
    suppress_alert_tool,
    forward_alert_tool,
    detect_flapping_alerts_tool,
    detect_self_resolving_alerts_tool,
    analyze_alert_patterns_tool
)
from .prompts import return_instructions_alert_agent

def setup_before_agent_call(callback_context: CallbackContext):
    """Setup before calling the alert agent."""
    if "alert_settings" not in callback_context.state:
        callback_context.state["alert_settings"] = {
            "suppression_threshold": 0.8,
            "duplicate_window_minutes": 5,
            "critical_always_forward": True
        }

alert_agent = Agent(
    model=os.getenv("ALERT_AGENT_MODEL", "gemini-2.0-flash-exp"),
    name="alert_agent",
    instruction=return_instructions_alert_agent(),
        tools=[
            analyze_alert_tool,
            check_duplicate_alerts_tool,
            get_alert_history_tool,
            suppress_alert_tool,
            forward_alert_tool,
            detect_flapping_alerts_tool,
            detect_self_resolving_alerts_tool,
            analyze_alert_patterns_tool
        ],
    before_agent_callback=setup_before_agent_call,
    generate_content_config=types.GenerateContentConfig(temperature=0.01),
)
