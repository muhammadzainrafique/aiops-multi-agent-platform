# agents/resolver/tests/test_resolver.py
"""
Unit tests for the Resolver agent.
Mocks Redis and Kubernetes so no live cluster is needed.
"""
import json
import pytest
from unittest.mock import MagicMock, patch

from shared.models.incident import Incident


# ── Helpers ───────────────────────────────────────────────────────────────────

def make_incident(action_type: str = "restart_pod", **kwargs) -> Incident:
    defaults = dict(
        alert_name   = "PodCrashLooping",
        namespace    = "default",
        pod_name     = "crash-test",
        severity     = "critical",
        ai_diagnosis = "Pod is OOMKilled repeatedly.",
        recommended_action = "Restart the pod and increase memory limit.",
        action_taken = json.dumps({
            "action_type"        : action_type,
            "risk_if_unresolved" : "Service downtime",
            "confidence"         : "high",
        }),
    )
    defaults.update(kwargs)
    return Incident(**defaults)


@pytest.fixture
def mock_agent():
    with patch("agents.resolver.agent.get_redis_client") as mock_redis, \
         patch("agents.resolver.agent.get_k8s_clients") as mock_k8s, \
         patch("agents.resolver.agent.get_pod_logs", return_value="log line 1\nlog line 2"):

        mock_redis.return_value      = MagicMock()
        mock_core, mock_apps         = MagicMock(), MagicMock()
        mock_k8s.return_value        = (mock_core, mock_apps)

        from agents.resolver.agent import ResolverAgent
        agent = ResolverAgent()
        yield agent


# ── Tests ─────────────────────────────────────────────────────────────────────

def test_restart_pod_calls_delete(mock_agent):
    """Restart action must call delete_namespaced_pod exactly once."""
    incident = make_incident("restart_pod")
    mock_agent._restart_pod(incident)
    mock_agent.core_v1.delete_namespaced_pod.assert_called_once_with(
        name="crash-test", namespace="default"
    )


def test_restart_pod_returns_human_readable_message(mock_agent):
    """Restart summary must mention the pod name."""
    incident = make_incident("restart_pod")
    result   = mock_agent._restart_pod(incident)
    assert "crash-test" in result
    assert "recreate" in result.lower()


def test_manual_review_takes_no_k8s_action(mock_agent):
    """Manual review must NOT call any Kubernetes API."""
    incident = make_incident("manual_review")
    mock_agent._manual_review(incident)
    mock_agent.core_v1.delete_namespaced_pod.assert_not_called()
    mock_agent.apps_v1.patch_namespaced_deployment_scale.assert_not_called()


def test_resolve_sets_status_resolved(mock_agent):
    """After a successful restart, incident status must be 'resolved'."""
    incident = make_incident("restart_pod")
    mock_agent._resolve(incident)
    assert incident.status == "resolved"


def test_resolve_sets_resolved_at_timestamp(mock_agent):
    """Resolved incident must have a resolved_at timestamp."""
    incident = make_incident("restart_pod")
    mock_agent._resolve(incident)
    assert incident.resolved_at is not None


def test_resolve_saves_incident_to_redis(mock_agent):
    """Incident must be saved back to Redis after resolution."""
    incident = make_incident("restart_pod")
    mock_agent._resolve(incident)
    assert mock_agent.redis.hset.called


def test_restart_rate_limit_engages(mock_agent):
    """After 5 restarts in under 60s, further restarts should be blocked."""
    import time
    now = time.time()
    mock_agent._restart_timestamps = [now] * 5   # simulate 5 recent restarts

    incident = make_incident("restart_pod")
    result   = mock_agent._restart_pod(incident)

    # Should NOT have called delete
    mock_agent.core_v1.delete_namespaced_pod.assert_not_called()
    assert "rate limit" in result.lower()


def test_review_logs_does_not_mutate_cluster(mock_agent):
    """Log review must not call any mutating Kubernetes API."""
    incident = make_incident("review_logs")
    mock_agent._review_logs(incident)
    mock_agent.core_v1.delete_namespaced_pod.assert_not_called()
    mock_agent.apps_v1.patch_namespaced_deployment_scale.assert_not_called()
