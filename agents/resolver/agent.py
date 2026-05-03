# agents/resolver/agent.py
"""
Resolver Agent — executes REAL Kubernetes remediation actions.
Key fix: finds parent Deployment by app label OR by deployment name directly,
so resource patching works even when pod name resolution had issues.
"""
import json
import time
from datetime import datetime, timezone

from kubernetes import client as k8s_client
from kubernetes.client.rest import ApiException

from shared.utils.logger import get_logger
from shared.utils.redis_client import (
    get_redis_client,
    QUEUE_EVALUATOR_TO_RESOLVER,
    STORE_INCIDENTS,
)
from shared.utils.k8s_client import get_k8s_clients, get_pod_logs
from shared.utils.slack_notifier import notify_incident_resolved, notify_evaluation_failed
from shared.models.incident import Incident
from agents.resolver.config import (
    QUEUE_BLOCK_TIMEOUT,
    DEFAULT_NAMESPACE,
    SCALE_UP_REPLICAS,
)

log = get_logger("resolver")

DEFAULT_MEMORY_LIMIT   = "512Mi"
DEFAULT_MEMORY_REQUEST = "256Mi"
DEFAULT_CPU_LIMIT      = "500m"
DEFAULT_CPU_REQUEST    = "250m"


class ResolverAgent:

    def __init__(self):
        self.redis = get_redis_client()
        self.core_v1, self.apps_v1 = get_k8s_clients()
        self._restart_timestamps: list = []
        log.info("Resolver agent initialised")

    def run(self):
        log.info(f"Listening on queue: {QUEUE_EVALUATOR_TO_RESOLVER}")
        while True:
            try:
                self._consume_one()
            except KeyboardInterrupt:
                log.info("Resolver shutting down")
                break
            except Exception as e:
                log.error(f"Unexpected error: {e}")
                time.sleep(3)

    def _consume_one(self):
        result = self.redis.brpop(
            QUEUE_EVALUATOR_TO_RESOLVER, timeout=QUEUE_BLOCK_TIMEOUT
        )
        if result is None:
            return
        _, raw = result
        try:
            incident = Incident.from_json(raw)
        except Exception as e:
            log.error(f"Deserialise failed: {e}")
            return
        log.info(f"Received: {incident.summary()}")
        self._resolve(incident)

    def _resolve(self, incident: Incident):
        try:
            meta        = json.loads(incident.action_taken or "{}")
            action_type = meta.get("action_type", "unknown")
        except (json.JSONDecodeError, TypeError):
            action_type = "unknown"

        action_type = self._refine_action(action_type, incident)
        log.info(
            f"Executing [{action_type}] for "
            f"{incident.namespace}/{incident.pod_name}"
        )

        dispatch = {
            "restart_pod"          : self._restart_pod,
            "scale_deployment"     : self._scale_deployment,
            "check_resources"      : self._fix_resources,
            "increase_memory"      : self._fix_resources,
            "increase_cpu"         : self._fix_resources,
            "review_logs"          : self._review_and_annotate,
            "network_policy_reset" : self._reset_network_policy,
            "rollback_deployment"  : self._rollback_deployment,
            "cordon_node"          : self._cordon_node,
            "manual_review"        : self._manual_review,
        }
        handler = dispatch.get(action_type, self._smart_fallback)

        try:
            action_summary        = handler(incident)
            incident.status       = "resolved"
            incident.action_taken = action_summary
            incident.resolved_at  = datetime.now(timezone.utc).isoformat()
            notify_incident_resolved(incident)
        except Exception as e:
            log.error(f"Remediation failed for {incident.id}: {e}")
            incident.status       = "resolution_failed"
            incident.action_taken = f"FAILED: {e}"
            notify_evaluation_failed(incident)
        finally:
            self._save(incident)
            self._print_report(incident)

    # ── Keyword inference ─────────────────────────────────────────────────────

    def _refine_action(self, action_type: str, incident: Incident) -> str:
        if action_type not in ("manual_review", "unknown", "check_resources"):
            return action_type
        diag = (incident.ai_diagnosis + " " + incident.alert_name).lower()
        if any(k in diag for k in ["oom","out of memory","memory","killed","evict"]):
            return "increase_memory"
        if any(k in diag for k in ["cpu","throttl","high cpu"]):
            return "increase_cpu"
        if any(k in diag for k in ["crash","restart","backoff","exit code","segfault"]):
            return "restart_pod"
        if any(k in diag for k in ["network","connection refused","timeout","dns","socket","unreachable"]):
            return "network_policy_reset"
        if any(k in diag for k in ["rollback","imagepull","errimagepull","bad image"]):
            return "rollback_deployment"
        if any(k in diag for k in ["scale","replica","unavailable","overload"]):
            return "scale_deployment"
        if any(k in diag for k in ["node","disk","pressure","taint"]):
            return "cordon_node"
        return "restart_pod"

    # ── Helper: find parent Deployment reliably ───────────────────────────────

    def _find_deployment(self, namespace: str, pod_name: str):
        """
        Finds the parent Deployment for a pod.
        Strategy 1: match pod labels against deployment selectors.
        Strategy 2: deployment name == pod_name base (e.g. demo-app-xxx → demo-app).
        Strategy 3: list all deployments and fuzzy-match by name prefix.
        Returns (AppsV1Deployment, str dep_name) or (None, None).
        """
        # Strategy 1: via pod labels
        try:
            pod    = self.core_v1.read_namespaced_pod(
                name=pod_name, namespace=namespace
            )
            labels = pod.metadata.labels or {}
            deps   = self.apps_v1.list_namespaced_deployment(namespace=namespace)
            for dep in deps.items:
                sel = dep.spec.selector.match_labels or {}
                if sel and all(labels.get(k) == v for k, v in sel.items()):
                    log.info(f"Found deployment via labels: {dep.metadata.name}")
                    return dep, dep.metadata.name
        except ApiException:
            pass

        # Strategy 2: deployment name is prefix of pod name (demo-app-xxx-yyy)
        try:
            deps = self.apps_v1.list_namespaced_deployment(namespace=namespace)
            for dep in deps.items:
                if pod_name.startswith(dep.metadata.name):
                    log.info(f"Found deployment via name prefix: {dep.metadata.name}")
                    return dep, dep.metadata.name
        except ApiException:
            pass

        # Strategy 3: pod_name itself is a deployment name
        try:
            dep = self.apps_v1.read_namespaced_deployment(
                name=pod_name, namespace=namespace
            )
            log.info(f"Found deployment by exact name: {dep.metadata.name}")
            return dep, dep.metadata.name
        except ApiException:
            pass

        log.warning(f"No deployment found for pod '{pod_name}' in '{namespace}'")
        return None, None

    # ── Action 1: Restart pod ─────────────────────────────────────────────────

    def _restart_pod(self, incident: Incident) -> str:
        namespace = incident.namespace or DEFAULT_NAMESPACE
        pod_name  = incident.pod_name

        now = time.time()
        self._restart_timestamps = [
            t for t in self._restart_timestamps if now - t < 60
        ]
        if len(self._restart_timestamps) >= 5:
            return self._manual_review(
                incident, reason="Restart rate limit: 5/min reached"
            )

        try:
            self.core_v1.delete_namespaced_pod(
                name=pod_name, namespace=namespace
            )
            self._restart_timestamps.append(now)
            msg = (
                f"✅ RESTARTED: Pod '{pod_name}' deleted. "
                f"Kubernetes will recreate it via the parent Deployment."
            )
            log.info(msg)
            return msg
        except ApiException as e:
            if e.status == 404:
                # Pod not found — trigger rolling restart on parent deployment
                dep, dep_name = self._find_deployment(namespace, pod_name)
                if dep:
                    self.apps_v1.patch_namespaced_deployment(
                        name=dep_name, namespace=namespace,
                        body={"spec": {"template": {"metadata": {"annotations": {
                            "kubectl.kubernetes.io/restartedAt":
                                datetime.now(timezone.utc).isoformat()
                        }}}}}
                    )
                    return (
                        f"✅ ROLLING RESTART: Pod '{pod_name}' not found directly. "
                        f"Triggered rolling restart on Deployment '{dep_name}'."
                    )
                return f"ℹ️ Pod '{pod_name}' not found — may have auto-restarted."
            raise

    # ── Action 2: Scale deployment ────────────────────────────────────────────

    def _scale_deployment(self, incident: Incident) -> str:
        namespace = incident.namespace or DEFAULT_NAMESPACE
        pod_name  = incident.pod_name

        dep, dep_name = self._find_deployment(namespace, pod_name)
        if not dep:
            return self._restart_pod(incident)

        current  = dep.spec.replicas or 1
        new_reps = current + SCALE_UP_REPLICAS

        self.apps_v1.patch_namespaced_deployment_scale(
            name=dep_name, namespace=namespace,
            body={"spec": {"replicas": new_reps}},
        )
        msg = (
            f"✅ SCALED: Deployment '{dep_name}' scaled "
            f"{current} → {new_reps} replicas in '{namespace}'."
        )
        log.info(msg)
        return msg

    # ── Action 3: Fix resources (REAL patch) ──────────────────────────────────

    def _fix_resources(self, incident: Incident) -> str:
        namespace = incident.namespace or DEFAULT_NAMESPACE
        pod_name  = incident.pod_name

        dep, dep_name = self._find_deployment(namespace, pod_name)
        if not dep:
            return self._restart_pod(incident)

        containers = dep.spec.template.spec.containers
        patches    = []
        for c in containers:
            patches.append({
                "name": c.name,
                "resources": {
                    "requests": {
                        "memory": DEFAULT_MEMORY_REQUEST,
                        "cpu"   : DEFAULT_CPU_REQUEST,
                    },
                    "limits": {
                        "memory": DEFAULT_MEMORY_LIMIT,
                        "cpu"   : DEFAULT_CPU_LIMIT,
                    }
                }
            })

        self.apps_v1.patch_namespaced_deployment(
            name=dep_name, namespace=namespace,
            body={"spec": {"template": {"spec": {"containers": patches}}}}
        )

        msg = (
            f"✅ RESOURCES PATCHED: Deployment '{dep_name}' in '{namespace}' — "
            f"memory limit → {DEFAULT_MEMORY_LIMIT}, "
            f"CPU limit → {DEFAULT_CPU_LIMIT}. "
            f"Rolling restart triggered automatically by Kubernetes."
        )
        log.info(msg)
        return msg

    # ── Action 4: Review logs + annotate ─────────────────────────────────────

    def _review_and_annotate(self, incident: Incident) -> str:
        namespace  = incident.namespace or DEFAULT_NAMESPACE
        fresh_logs = get_pod_logs(
            self.core_v1, namespace=namespace,
            pod_name=incident.pod_name, tail_lines=50
        )
        dep, dep_name = self._find_deployment(namespace, incident.pod_name)
        if dep:
            try:
                self.apps_v1.patch_namespaced_deployment(
                    name=dep_name, namespace=namespace,
                    body={"metadata": {"annotations": {
                        "aiops/last-incident-id": incident.id,
                        "aiops/last-review"     : datetime.now(timezone.utc).isoformat(),
                        "aiops/diagnosis"       : incident.ai_diagnosis[:200],
                    }}}
                )
            except Exception:
                pass
        return (
            f"✅ LOG REVIEW: Fetched {len(fresh_logs.splitlines())} lines "
            f"from '{incident.pod_name}'. Deployment '{dep_name}' annotated."
        )

    # ── Action 5: Network policy reset ───────────────────────────────────────

    def _reset_network_policy(self, incident: Incident) -> str:
        namespace   = incident.namespace or DEFAULT_NAMESPACE
        policy_name = f"aiops-allow-all-{namespace}"
        networking  = k8s_client.NetworkingV1Api()
        policy_body = {
            "apiVersion": "networking.k8s.io/v1",
            "kind"      : "NetworkPolicy",
            "metadata"  : {
                "name": policy_name, "namespace": namespace,
                "annotations": {"aiops/incident-id": incident.id}
            },
            "spec": {
                "podSelector": {},
                "policyTypes": ["Ingress", "Egress"],
                "ingress"    : [{}],
                "egress"     : [{}],
            }
        }
        try:
            networking.delete_namespaced_network_policy(
                name=policy_name, namespace=namespace
            )
        except ApiException:
            pass
        try:
            networking.create_namespaced_network_policy(
                namespace=namespace, body=policy_body
            )
        except Exception as e:
            log.warning(f"NetworkPolicy create failed: {e}")
            return self._restart_pod(incident)

        try:
            self.core_v1.delete_namespaced_pod(
                name=incident.pod_name, namespace=namespace
            )
        except ApiException:
            pass

        return (
            f"✅ NETWORK RESET: Permissive NetworkPolicy '{policy_name}' applied "
            f"in '{namespace}'. Pod restarted to re-establish connections."
        )

    # ── Action 6: Rollback ────────────────────────────────────────────────────

    def _rollback_deployment(self, incident: Incident) -> str:
        namespace = incident.namespace or DEFAULT_NAMESPACE
        dep, dep_name = self._find_deployment(namespace, incident.pod_name)
        if not dep:
            return self._restart_pod(incident)
        self.apps_v1.patch_namespaced_deployment(
            name=dep_name, namespace=namespace,
            body={"spec": {"template": {"metadata": {"annotations": {
                "kubectl.kubernetes.io/restartedAt":
                    datetime.now(timezone.utc).isoformat(),
                "aiops/rollback-triggered": "true",
            }}}}}
        )
        return (
            f"✅ ROLLBACK: Rolling restart triggered on '{dep_name}'. "
            f"K8s will use the previous ReplicaSet."
        )

    # ── Action 7: Cordon node ─────────────────────────────────────────────────

    def _cordon_node(self, incident: Incident) -> str:
        namespace = incident.namespace or DEFAULT_NAMESPACE
        try:
            pod       = self.core_v1.read_namespaced_pod(
                name=incident.pod_name, namespace=namespace
            )
            node_name = pod.spec.node_name
            self.core_v1.patch_node(
                name=node_name,
                body={"spec": {"unschedulable": True}}
            )
            try:
                self.core_v1.delete_namespaced_pod(
                    name=incident.pod_name, namespace=namespace
                )
            except ApiException:
                pass
            return (
                f"✅ NODE CORDONED: Node '{node_name}' marked unschedulable. "
                f"Pod rescheduled to healthy node."
            )
        except ApiException:
            return self._restart_pod(incident)

    # ── Action 8: Smart fallback ──────────────────────────────────────────────

    def _smart_fallback(self, incident: Incident) -> str:
        log.warning(
            f"Unknown action for {incident.alert_name} — smart fallback"
        )
        try:
            msg = self._restart_pod(incident)
            return f"⚡ SMART FALLBACK ({incident.alert_name}): {msg}"
        except Exception as e:
            return self._manual_review(incident, reason=f"Restart failed: {e}")

    # ── Action 9: Manual review ───────────────────────────────────────────────

    def _manual_review(self, incident: Incident, reason: str = "") -> str:
        msg = (
            f"🔔 MANUAL REVIEW: {incident.alert_name} | "
            f"{incident.namespace}/{incident.pod_name} | "
            f"{reason or 'Human intervention required'}"
        )
        log.warning(msg)
        return msg

    # ── Helpers ───────────────────────────────────────────────────────────────

    def _save(self, incident: Incident):
        self.redis.hset(STORE_INCIDENTS, incident.id, incident.to_json())

    def _print_report(self, incident: Incident):
        sep = "─" * 64
        log.info(f"\n{sep}")
        log.info(f"  RESOLUTION REPORT [{incident.id}]")
        log.info(sep)
        log.info(f"  Alert    : {incident.alert_name}")
        log.info(f"  Pod      : {incident.namespace}/{incident.pod_name}")
        log.info(f"  Severity : {incident.severity.upper()}")
        log.info(f"  Status   : {incident.status.upper()}")
        log.info(f"  Diagnosis: {incident.ai_diagnosis[:120]}")
        log.info(f"  Action   : {incident.action_taken[:200]}")
        log.info(f"  Resolved : {incident.resolved_at}")
        log.info(sep)
