# agents/supervisor/main.py
"""
Entrypoint for the Supervisor agent.
Starts the Flask webhook server and registers all HTTP routes.

Routes:
  POST /webhook   — Prometheus AlertManager sends alerts here
  GET  /health    — Kubernetes liveness / readiness probe
  GET  /incidents — Lists all stored incidents (debug / dashboard)
"""
from flask import Flask, request, jsonify
from dotenv import load_dotenv

from shared.utils.logger import get_logger
from agents.supervisor.agent import SupervisorAgent
from agents.supervisor.config import WEBHOOK_HOST, WEBHOOK_PORT

load_dotenv()

log   = get_logger("supervisor.main")
app   = Flask(__name__)
agent = SupervisorAgent()


@app.route("/webhook", methods=["POST"])
def webhook():
    """
    Receives Prometheus AlertManager webhook payloads.
    AlertManager must be configured to POST to http://<supervisor>:5001/webhook
    """
    payload = request.get_json(silent=True) or {}
    log.info(f"Webhook received — {len(payload.get('alerts', []))} alert(s)")
    result = agent.handle_alert(payload)
    return jsonify(result), 200


@app.route("/health", methods=["GET"])
def health():
    """Liveness probe endpoint for Kubernetes."""
    status = agent.health()
    code   = 200 if status["status"] == "healthy" else 503
    return jsonify(status), code


@app.route("/incidents", methods=["GET"])
def list_incidents():
    """
    Returns all stored incidents from Redis.
    Useful for debugging and the Grafana annotation source.
    """
    from shared.utils.redis_client import STORE_INCIDENTS
    import json

    raw = agent.redis.hgetall(STORE_INCIDENTS)
    incidents = [json.loads(v) for v in raw.values()]
    # Sort newest first
    incidents.sort(key=lambda x: x.get("created_at", ""), reverse=True)
    return jsonify({"count": len(incidents), "incidents": incidents}), 200


@app.route("/test-alert", methods=["POST"])
def test_alert():
    """
    Convenience endpoint to inject a fake alert without AlertManager.
    Used during development and failure simulation.

    Example body:
    {
      "alertname": "PodCrashLooping",
      "namespace": "default",
      "pod":       "my-app-xyz",
      "severity":  "critical"
    }
    """
    body = request.get_json(silent=True) or {}
    fake_payload = {
        "alerts": [{
            "labels": {
                "alertname" : body.get("alertname", "TestAlert"),
                "namespace"  : body.get("namespace", "default"),
                "pod"        : body.get("pod", "test-pod"),
                "severity"   : body.get("severity", "warning"),
            },
            "annotations": {
                "summary": body.get("summary", "Test alert from /test-alert endpoint"),
            }
        }]
    }
    result = agent.handle_alert(fake_payload)
    return jsonify(result), 200


if __name__ == "__main__":
    log.info(f"Supervisor agent starting on {WEBHOOK_HOST}:{WEBHOOK_PORT}")
    app.run(host=WEBHOOK_HOST, port=WEBHOOK_PORT, debug=False)
