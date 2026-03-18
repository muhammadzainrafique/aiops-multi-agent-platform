# agents/supervisor/tests/test_supervisor.py
"""
Unit tests for the Supervisor agent.
Uses mocks so Redis and Kubernetes are not required to run tests.
"""
import json
import pytest
from unittest.mock import MagicMock, patch

from shared.models.incident import Incident


# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture
def mock_agent():
    """Returns a SupervisorAgent with Redis and K8s fully mocked."""
    with patch("agents.supervisor.agent.get_redis_client") as mock_redis, \
         patch("agents.supervisor.agent.get_k8s_clients") as mock_k8s, \
         patch("agents.supervisor.agent.get_pod_logs", return_value="ERROR: pod restarted"):

        mock_redis.return_value = MagicMock()
        mock_k8s.return_value   = (MagicMock(), MagicMock())

        from agents.supervisor.agent import SupervisorAgent
        agent = SupervisorAgent()
        yield agent


@pytest.fixture
def sample_payload():
    """A realistic Prometheus AlertManager webhook payload."""
    return {
        "alerts": [
            {
                "labels": {
                    "alertname" : "PodCrashLooping",
                    "namespace"  : "production",
                    "pod"        : "api-server-7d9f8b-xkj2p",
                    "severity"   : "critical",
                },
                "annotations": {
                    "summary": "Pod has been restarting repeatedly",
                }
            }
        ]
    }


# ── Tests ─────────────────────────────────────────────────────────────────────

def test_handle_alert_returns_processed_count(mock_agent, sample_payload):
    """Supervisor should process exactly 1 alert from the payload."""
    result = mock_agent.handle_alert(sample_payload)
    assert result["processed"] == 1


def test_incident_fields_are_correctly_mapped(mock_agent, sample_payload):
    """Alert labels should map correctly onto the Incident fields."""
    mock_agent.handle_alert(sample_payload)

    # Grab what was pushed to the Redis queue
    pushed = mock_agent.redis.lpush.call_args[0][1]
    incident = Incident.from_json(pushed)

    assert incident.alert_name == "PodCrashLooping"
    assert incident.namespace  == "production"
    assert incident.pod_name   == "api-server-7d9f8b-xkj2p"
    assert incident.severity   == "critical"
    assert incident.status     == "open"


def test_empty_payload_returns_zero(mock_agent):
    """Empty alerts list should process nothing and not raise."""
    result = mock_agent.handle_alert({"alerts": []})
    assert result["processed"] == 0


def test_incident_is_pushed_to_correct_queue(mock_agent, sample_payload):
    """Incident must be pushed to QUEUE_SUPERVISOR_TO_EVALUATOR."""
    from shared.utils.redis_client import QUEUE_SUPERVISOR_TO_EVALUATOR
    mock_agent.handle_alert(sample_payload)
    queue_key = mock_agent.redis.lpush.call_args[0][0]
    assert queue_key == QUEUE_SUPERVISOR_TO_EVALUATOR


def test_incident_is_stored_in_redis_hash(mock_agent, sample_payload):
    """Incident must also be saved to the incidents hash store."""
    from shared.utils.redis_client import STORE_INCIDENTS
    mock_agent.handle_alert(sample_payload)
    assert mock_agent.redis.hset.called
    store_key = mock_agent.redis.hset.call_args[0][0]
    assert store_key == STORE_INCIDENTS


def test_health_returns_healthy_when_redis_ok(mock_agent):
    """Health check should return 'healthy' when Redis responds to ping."""
    mock_agent.redis.ping.return_value = True
    result = mock_agent.health()
    assert result["status"]  == "healthy"
    assert result["redis"]   == "ok"


def test_health_returns_degraded_when_redis_down(mock_agent):
    """Health check should return 'degraded' when Redis is unreachable."""
    mock_agent.redis.ping.side_effect = Exception("Connection refused")
    result = mock_agent.health()
    assert result["status"] == "degraded"
