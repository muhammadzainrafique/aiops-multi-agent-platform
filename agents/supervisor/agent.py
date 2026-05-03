# agents/supervisor/agent.py
import json
import threading
import time
from datetime import datetime, timezone

from flask import Flask, request, jsonify, Response

from shared.utils.logger import get_logger
from shared.utils.redis_client import (
    get_redis_client,
    QUEUE_SUPERVISOR_TO_EVALUATOR,
    STORE_INCIDENTS,
)
from shared.utils.k8s_client import (
    get_k8s_clients,
    get_pod_logs,
    get_actual_pod_name,
)
from shared.models.incident import Incident
from shared.utils.slack_notifier import notify_incident_created
from agents.supervisor.config import (
    WEBHOOK_HOST, WEBHOOK_PORT,
    POD_LOG_TAIL_LINES, SEVERITY_MAP, DEFAULT_SEVERITY,
)

app = Flask(__name__)
log = get_logger("supervisor")


class SupervisorAgent:

    def __init__(self):
        self.redis = get_redis_client()
        self.core_v1, self.apps_v1 = get_k8s_clients()
        log.info("Supervisor agent initialised")

    # ── Active monitor ────────────────────────────────────────────────────────

    def start_active_monitor(self):
        """Starts background thread that scans cluster every 30s."""
        def loop():
            log.info("Active monitor started — scanning every 30s")
            while True:
                try:
                    self._scan_cluster()
                except Exception as e:
                    log.error(f"Scan error: {e}")
                time.sleep(30)
        threading.Thread(target=loop, daemon=True).start()

    def _scan_cluster(self):
        """Detects real Kubernetes problems and auto-fires alerts."""
        try:
            pods = self.core_v1.list_namespaced_pod(namespace="default")
        except Exception as e:
            log.warning(f"Cannot list pods: {e}")
            return

        SKIP = ('supervisor', 'evaluator', 'resolver', 'redis',
                'prometheus', 'grafana', 'alertmanager', 'kube-state')

        for pod in pods.items:
            name = pod.metadata.name
            if any(s in name for s in SKIP):
                continue

            phase    = pod.status.phase or ''
            statuses = pod.status.container_statuses or []

            for cs in statuses:
                reason    = (cs.state.waiting.reason or '') if cs.state.waiting else ''
                last_reason = (cs.last_state.terminated.reason or '') if cs.last_state.terminated else ''

                # CrashLoopBackOff
                if 'CrashLoop' in reason:
                    self._auto_alert('PodCrashLooping', 'default', name, 'critical')

                # High restart count
                elif (cs.restart_count or 0) >= 3:
                    self._auto_alert('PodCrashLooping', 'default', name, 'critical')

                # OOMKilled
                elif last_reason == 'OOMKilled':
                    self._auto_alert('HighMemoryUsage', 'default', name, 'critical')

                # ImagePullBackOff
                elif reason in ('ImagePullBackOff', 'ErrImagePull', 'InvalidImageName'):
                    self._auto_alert('ImagePullError', 'default', name, 'critical')

                # Container not ready (but pod is running)
                elif not cs.ready and phase == 'Running':
                    self._auto_alert('PodNotReady', 'default', name, 'warning')

            # Pod in Error/Failed phase
            if phase in ('Failed', 'Unknown'):
                self._auto_alert('PodFailed', 'default', name, 'critical')

    def _auto_alert(self, alert_name: str, namespace: str,
                    pod_name: str, severity: str):
        """Fires alert with 5-minute dedup — prevents spam."""
        key = f"auto:{namespace}:{pod_name}:{alert_name}"
        if self.redis.get(key):
            return
        self.redis.setex(key, 300, "1")

        log.info(f"AUTO-DETECTED: {alert_name} on {namespace}/{pod_name}")
        fake = {"labels": {
            "alertname": alert_name,
            "namespace" : namespace,
            "pod"       : pod_name,
            "severity"  : severity,
        }}
        self._process_single_alert(fake)

    # ── Webhook handler ───────────────────────────────────────────────────────

    def handle_alert(self, payload: dict) -> dict:
        alerts = payload.get("alerts", [])
        if not alerts:
            return {"processed": 0}
        processed = []
        for raw in alerts:
            inc = self._process_single_alert(raw)
            if inc:
                processed.append(inc.summary())
        return {"processed": len(processed), "incidents": processed}

    def _process_single_alert(self, raw_alert: dict):
        labels     = raw_alert.get("labels", {})
        alert_name = labels.get("alertname", "UnknownAlert")
        namespace  = labels.get("namespace", "default")
        raw_name   = labels.get("pod", labels.get("pod_name", "unknown"))
        severity   = SEVERITY_MAP.get(
            labels.get("severity", "").lower(), DEFAULT_SEVERITY
        )

        pod_name = get_actual_pod_name(self.core_v1, namespace, raw_name)
        log.info(f"Processing: {alert_name} | {namespace}/{pod_name} | {severity}")

        raw_logs = get_pod_logs(
            self.core_v1,
            namespace=namespace,
            pod_name=pod_name,
            tail_lines=POD_LOG_TAIL_LINES,
        )

        incident = Incident(
            alert_name=alert_name,
            namespace=namespace,
            pod_name=pod_name,
            severity=severity,
            raw_logs=raw_logs,
        )

        self.redis.hset(STORE_INCIDENTS, incident.id, incident.to_json())
        self.redis.lpush(QUEUE_SUPERVISOR_TO_EVALUATOR, incident.to_json())
        log.info(f"Queued: {incident.summary()}")
        notify_incident_created(incident)
        return incident

    def health(self) -> dict:
        try:
            self.redis.ping()
            redis_ok = True
        except Exception:
            redis_ok = False
        return {
            "agent"    : "supervisor",
            "status"   : "healthy" if redis_ok else "degraded",
            "redis"    : "ok" if redis_ok else "unreachable",
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
