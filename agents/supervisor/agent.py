# agents/supervisor/agent.py
"""
Supervisor Agent — the entry point of the entire AIOps pipeline.

Responsibilities:
  1. Expose an HTTP webhook for Prometheus AlertManager POST requests.
  2. Parse incoming alerts and extract namespace, pod name, severity.
  3. Collect the last N log lines from the affected pod via Kubernetes API.
  4. Create an Incident object and push it to the Redis queue
     for the Evaluator agent to consume.
"""
import json
from datetime import datetime, timezone
from flask import Flask, request, jsonify

from shared.utils.logger import get_logger
from shared.utils.redis_client import get_redis_client, QUEUE_SUPERVISOR_TO_EVALUATOR, STORE_INCIDENTS
from shared.utils.k8s_client import get_k8s_clients, get_pod_logs
from shared.models.incident import Incident
from agents.supervisor.config import (
    WEBHOOK_HOST, WEBHOOK_PORT,
    POD_LOG_TAIL_LINES, SEVERITY_MAP, DEFAULT_SEVERITY,
)

logger = Flask(__name__)          # Flask app reuses the module name
app    = Flask(__name__)
log    = get_logger("supervisor")


class SupervisorAgent:
    """
    Wraps the Flask webhook server and all alert-handling logic.
    Keeps Flask routes thin — all real work happens here.
    """

    def __init__(self):
        self.redis    = get_redis_client()
        self.core_v1, self.apps_v1 = get_k8s_clients()
        log.info("Supervisor agent initialised")

    # ── Public method called by Flask route ──────────────────────────────────

    def handle_alert(self, payload: dict) -> dict:
        """
        Processes a raw Prometheus AlertManager webhook payload.
        Returns a summary dict for the HTTP response.
        """
        alerts = payload.get("alerts", [])
        if not alerts:
            log.warning("Received webhook with no alerts")
            return {"processed": 0}

        processed = []
        for raw_alert in alerts:
            incident = self._process_single_alert(raw_alert)
            if incident:
                processed.append(incident.summary())

        return {"processed": len(processed), "incidents": processed}

    # ── Private helpers ───────────────────────────────────────────────────────

    def _process_single_alert(self, raw_alert: dict):
        """
        Converts one Prometheus alert dict into an enriched Incident,
        stores it in Redis, and pushes it to the evaluator queue.
        Returns the Incident on success, None on failure.
        """
        labels      = raw_alert.get("labels", {})
        annotations = raw_alert.get("annotations", {})

        alert_name = labels.get("alertname", "UnknownAlert")
        namespace  = labels.get("namespace", "default")
        pod_name   = labels.get("pod", labels.get("pod_name", "unknown-pod"))
        severity   = SEVERITY_MAP.get(
            labels.get("severity", "").lower(), DEFAULT_SEVERITY
        )

        log.info(f"Processing alert: {alert_name} | {namespace}/{pod_name} | {severity}")

        # Collect pod logs so the Evaluator has raw data to analyse
        raw_logs = get_pod_logs(
            self.core_v1,
            namespace=namespace,
            pod_name=pod_name,
            tail_lines=POD_LOG_TAIL_LINES,
        )

        # Build the Incident object
        incident = Incident(
            alert_name=alert_name,
            namespace=namespace,
            pod_name=pod_name,
            severity=severity,
            raw_logs=raw_logs,
        )

        # Persist to Redis store (full history)
        self.redis.hset(STORE_INCIDENTS, incident.id, incident.to_json())

        # Push to evaluator queue (FIFO via LPUSH / BRPOP)
        self.redis.lpush(QUEUE_SUPERVISOR_TO_EVALUATOR, incident.to_json())

        log.info(f"Incident {incident.id} queued for Evaluator → {incident.summary()}")
        return incident

    def health(self) -> dict:
        """Returns agent health status — used by K8s liveness probe."""
        try:
            self.redis.ping()
            redis_ok = True
        except Exception:
            redis_ok = False

        return {
            "agent"      : "supervisor",
            "status"     : "healthy" if redis_ok else "degraded",
            "redis"      : "ok" if redis_ok else "unreachable",
            "timestamp"  : datetime.now(timezone.utc).isoformat(),
        }
