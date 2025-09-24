# app/run_local.py
import asyncio
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from app.agent_root import get_agent

async def run_demo():
    agent = get_agent()
    session_service = InMemorySessionService()
    session = await session_service.create_session(app_name="alerts_app", user_id="devuser")
    runner = Runner(agent=agent, session_service=session_service, app_name="alerts_app")

    prompt = "Process up to 100 pending alerts now and summarize."
    async for ev in runner.run_async(user_id="devuser", session_id=session.id, new_message=prompt):
        # print streaming parts
        if ev.content and ev.content.parts:
            print(ev.content.parts[0].text)

if __name__ == "__main__":
    asyncio.run(run_demo())