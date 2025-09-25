import os
from google.adk.agents import Agent
from google.adk.agents.callback_context import CallbackContext
from google.genai import types

from .tools import call_ds_agent, test_ml_model_tool, diagnose_ml_model_tool, create_ml_model_tool, train_ml_model_tool, predict_with_new_model_tool
from .prompts import return_instructions_ml_agent

def setup_before_agent_call(callback_context: CallbackContext):
    # Any setup for ML agent
    if "ml_settings" not in callback_context.state:
        callback_context.state["ml_settings"] = {"use_ml": True}

ml_agent = Agent(
    model=os.getenv("ML_AGENT_MODEL", "gemini-2.0-flash-exp"),
    name="ml_agent",
    instruction=return_instructions_ml_agent(),
    tools=[call_ds_agent, test_ml_model_tool, diagnose_ml_model_tool, create_ml_model_tool, train_ml_model_tool, predict_with_new_model_tool],
    before_agent_callback=setup_before_agent_call,
    generate_content_config=types.GenerateContentConfig(temperature=0.01),
)
