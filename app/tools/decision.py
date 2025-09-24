# app/tools/decision.py
def decide(alert_row: dict, ml_pred: dict) -> dict:
    # alert_row = the alert fields (host, title, severity, etc.)
    # ml_pred = { predicted_label: 'suppress'/'keep', predicted_label_probs: {...} }

    pred = ml_pred.get("predicted_label") or ml_pred.get("predicted_decision")
    confidence = (ml_pred.get("predicted_label_probs") or {}).get(pred, None)

    # simple policy: never suppress critical
    if alert_row.get("severity") == "critical":
        return {"decision": "forward", "reason": "critical – always forward"}

    # confidence gate
    if pred == "suppress" and confidence and confidence >= 0.8:
        return {"decision": "suppress", "reason": f"ml_suppress_conf={confidence:.2f}"}

    # fallback to rules (example duplicate check injected earlier in flow)
    return {"decision": "forward", "reason": "default-forward (no strong suppress)"}
