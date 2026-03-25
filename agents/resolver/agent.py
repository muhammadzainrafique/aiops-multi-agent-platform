# agents/resolver/agent.py
"""
Resolver Agent — the hands of the AIOps pipeline.

Responsibilities:
  1. Consume enriched incidents from the Evaluator queue.
  2. Read the action_type recommended by the Evaluator LLM.
  3. Execute the appropriate Kubernetes remediation action.
  4. Update the Incident with what was actually done and mark resolved.
  5. Log a human-readable summary of every action taken.

Supported action types:
  restart_pod        → Delete the pod (K8s recreates it automatically)
  scale_deployment   → Scale the parent Deployment up by SCALE_UP_REPLICAS
  check_resources    → Describe the pod and log resource usage (no mutation)
  review_logs        → Re-fetch and log the latest pod logs
  manual_review      → Flag the incident for human attention, take no action
"""
import json
import time
from datetime import datetime, timezone

from kubernetes.client.rest import ApiException

from shared.utils.logger import get_logger
from shared.utils.redis_client import (
    get_redis_client,
    QUEUE_EVALUATOR_TO_RESOLVER,
    STORE_INCIDENTS,
)
from shared.utils.k8s_client import get_k8s_clients, get_pod_logs
from shared.models.incident import Incident
from agents.resolver.config import (
    QUEUE_BLOCK_TIMEOUT,
    DEFAULT_NAMESPACE,
    SCALE_UP_REPLICAS,
)

log = get_logger("resolver")


class ResolverAgent:
    """
    Executes automated remediation actions based on the Evaluator's diagnosis.
    Every action is logged in human-readable form and stored back in Redis.
    """

    def __init__(self):
        self.redis              = get_redis_client()
        self.core_v1, self.apps_v1 = get_k8s_clients()
        # Rate-limiting: track restart timestamps
        self._restart_timestamps: list = []
        log.info("Resolver agent initialised")

    # ── Main loop ─────────────────────────────────────────────────────────────

    def run(self):
        """
        Blocking consumer loop — processes one incident at a time.
        Runs until the process is killed.
        """
        log.info(f"Listening on queue: {QUEUE_EVALUATOR_TO_RESOLVER}")

        while True:
            try:
                self._consume_one()
            except KeyboardInterrupt:
                log.info("Resolver agent shutting down")
                break
            except Exception as e:
                log.error(f"Unexpected error in resolver loop: {e}")
                time.sleep(3)

    def _consume_one(self):
        """Blocks on BRPOP and processes the next incident."""
        result = self.redis.brpop(
            QUEUE_EVALUATOR_TO_RESOLVER,
            timeout=QUEUE_BLOCK_TIMEOUT,
        )
        if result is None:
            return

        _, raw = result
        try:
            incident = Incident.from_json(raw)
        except Exception as e:
            log.error(f"Failed to deserialise incident: {e}")
            return

        log.info(f"Received incident: {incident.summary()}")
        self._resolve(incident)

    # ── Resolution dispatcher ─────────────────────────────────────────────────

    def _resolve(self, incident: Incident):
        """
        Reads action_type from the Evaluator's output and dispatches
        to the correct remediation method.
        """
        # Parse the action metadata stored by the Evaluator
        try:
            meta        = json.loads(incident.action_taken or "{}")
            action_type = meta.get("action_type", "manual_review")
        except (json.JSONDecodeError, TypeError):
            action_type = "manual_review"

        log.info(
            f"Resolving incident {incident.id} | "
            f"action_type={action_type} | "
            f"pod={incident.namespace}/{incident.pod_name}"
        )

        # Dispatch to the correct handler
        dispatch = {
            "restart_pod"      : self._restart_pod,
            "scale_deployment" : self._scale_deployment,
            "check_resources"  : self._check_resources,
            "review_logs"      : self._review_logs,
            "manual_review"    : self._manual_review,
        }
        handler = dispatch.get(action_type, self._manual_review)

        try:
            action_summary = handler(incident)
            incident.status      = "resolved"
            incident.action_taken = action_summary
            incident.resolved_at  = datetime.now(timezone.utc).isoformat()

        except Exception as e:
            log.error(f"Remediation failed for {incident.id}: {e}")
            incident.status      = "resolution_failed"
            incident.action_taken = f"FAILED: {e}"

        finally:
            self._save(incident)
            self._print_resolution_report(incident)

    # ── Remediation actions ───────────────────────────────────────────────────

    def _restart_pod(self, incident: Incident) -> str:
        """
        Deletes the pod — Kubernetes automatically recreates it via the
        parent ReplicaSet / Deployment. This is the safest restart method.
        """
        namespace = incident.namespace or DEFAULT_NAMESPACE
        pod_name  = incident.pod_name

        # Safety cap — avoid restart storms
        now = time.time()
        self._restart_timestamps = [
            t for t in self._restart_timestamps if now - t < 60
        ]
        if len(self._restart_timestamps) >= 5:
            msg = (
                f"Restart rate limit reached "
                f"({len(self._restart_timestamps)} restarts/min). "
                f"Escalating to manual review."
            )
            log.warning(msg)
            return msg

        self.core_v1.delete_namespaced_pod(
            name=pod_name,
            namespace=namespace,
        )
        self._restart_timestamps.append(now)

        msg = (
            f"Pod '{pod_name}' in namespace '{namespace}' was deleted. "
            f"Kubernetes will recreate it automatically via the parent Deployment."
        )
        log.info(msg)
        return msg

    def _scale_deployment(self, incident: Incident) -> str:
        """
        Finds the Deployment managing the pod and scales it up.
        Uses the pod's labels to identify the parent Deployment.
        """
        namespace = incident.namespace or DEFAULT_NAMESPACE
        pod_name  = incident.pod_name

        # Find parent Deployment by matching pod labels
        try:
            pod = self.core_v1.read_namespaced_pod(
                name=pod_name, namespace=namespace
            )
            labels      = pod.metadata.labels or {}
            deployments = self.apps_v1.list_namespaced_deployment(
                namespace=namespace
            )

            target_deployment = None
            for dep in deployments.items:
                selector = dep.spec.selector.match_labels or {}
                if all(labels.get(k) == v for k, v in selector.items()):
                    target_deployment = dep
                    break

            if not target_deployment:
                return (
                    f"No Deployment found managing pod '{pod_name}'. "
                    f"Manual scaling required."
                )

            current_replicas = target_deployment.spec.replicas or 1
            new_replicas     = current_replicas + SCALE_UP_REPLICAS

            # Patch the Deployment replica count
            self.apps_v1.patch_namespaced_deployment_scale(
                name      = target_deployment.metadata.name,
                namespace = namespace,
                body      = {"spec": {"replicas": new_replicas}},
            )

            msg = (
                f"Deployment '{target_deployment.metadata.name}' scaled from "
                f"{current_replicas} → {new_replicas} replicas in namespace '{namespace}'."
            )
            log.info(msg)
            return msg

        except ApiException as e:
            raise RuntimeError(f"Kubernetes API error during scale: {e.reason}")

    def _check_resources(self, incident: Incident) -> str:
        """
        Reads pod spec and describes its resource requests/limits.
        Non-mutating — safe to always run. Good for OOM and CPU issues.
        """
        namespace = incident.namespace or DEFAULT_NAMESPACE
        pod_name  = incident.pod_name

        try:
            pod        = self.core_v1.read_namespaced_pod(
                name=pod_name, namespace=namespace
            )
            containers = pod.spec.containers
            lines      = [
                f"Resource report for pod '{pod_name}' "
                f"in namespace '{namespace}':"
            ]

            for c in containers:
                resources = c.resources
                requests  = resources.requests or {}
                limits    = resources.limits   or {}
                lines.append(
                    f"  Container '{c.name}': "
                    f"CPU req={requests.get('cpu','unset')} "
                    f"lim={limits.get('cpu','unset')} | "
                    f"Mem req={requests.get('memory','unset')} "
                    f"lim={limits.get('memory','unset')}"
                )

            lines.append(
                "Recommendation: Review limits above and increase memory "
                "allocation if OOMKilled. Apply changes via kubectl or "
                "update the Deployment manifest."
            )
            msg = "\n".join(lines)
            log.info(msg)
            return msg

        except ApiException as e:
            raise RuntimeError(f"Could not describe pod: {e.reason}")

    def _review_logs(self, incident: Incident) -> str:
        """
        Re-fetches fresh pod logs and logs them for human review.
        Non-mutating — used when action_type is review_logs.
        """
        namespace = incident.namespace or DEFAULT_NAMESPACE
        fresh_logs = get_pod_logs(
            self.core_v1,
            namespace=namespace,
            pod_name=incident.pod_name,
            tail_lines=50,
        )
        msg = (
            f"Fresh log review for '{incident.pod_name}' "
            f"in '{namespace}':\n{fresh_logs}"
        )
        log.info(msg)
        return f"Log review completed. See Resolver logs for full output."

    def _manual_review(self, incident: Incident) -> str:
        """
        Flags the incident for human attention.
        No Kubernetes mutation is performed.
        """
        msg = (
            f"Incident {incident.id} flagged for MANUAL REVIEW.\n"
            f"Alert    : {incident.alert_name}\n"
            f"Pod      : {incident.namespace}/{incident.pod_name}\n"
            f"Diagnosis: {incident.ai_diagnosis}\n"
            f"Suggested: {incident.recommended_action}\n"
            f"Action   : No automated action taken — human intervention required."
        )
        log.warning(msg)
        return "Flagged for manual review. No automated action taken."

    # ── Helpers ───────────────────────────────────────────────────────────────

    def _save(self, incident: Incident):
        """Persists updated incident state to Redis."""
        self.redis.hset(STORE_INCIDENTS, incident.id, incident.to_json())

    def _print_resolution_report(self, incident: Incident):
        """
        Prints a clean, human-readable resolution report to the logs.
        This is the 'human-readable output' requirement from the FYP spec.
        """
        separator = "─" * 60
        log.info(f"\n{separator}")
        log.info(f"  INCIDENT RESOLUTION REPORT")
        log.info(separator)
        log.info(f"  ID         : {incident.id}")
        log.info(f"  Alert      : {incident.alert_name}")
        log.info(f"  Pod        : {incident.namespace}/{incident.pod_name}")
        log.info(f"  Severity   : {incident.severity.upper()}")
        log.info(f"  Status     : {incident.status.upper()}")
        log.info(f"  Diagnosis  : {incident.ai_diagnosis}")
        log.info(f"  Action     : {incident.action_taken}")
        log.info(f"  Resolved at: {incident.resolved_at}")
        log.info(separator)
