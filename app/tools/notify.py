# app/tools/notify.py
import os, requests
SLACK_WEBHOOK = os.getenv("SLACK_WEBHOOK", "")

def forward_to_slack(payload: dict):
    text = f"{payload.get('decision')} | {payload.get('alert_id')} | {payload.get('reason')}"
    if not SLACK_WEBHOOK:
        return {"status":"skipped", "note":"no webhook set"}
    r = requests.post(SLACK_WEBHOOK, json={"text": text}, timeout=5)
    return {"status":"ok" if r.status_code==200 else "error", "code": r.status_code}
