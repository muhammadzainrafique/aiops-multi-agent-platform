# agents/evaluator/tests/test_evaluator.py
"""
Unit tests for the Evaluator agent.
Mocks Redis and Groq so no external services are needed.
"""
import json
import pytest
from unittest.mock import MagicMock, patch, PropertyMock

from shared.models.incident import Incident


# ── Helpers ───────────────────────────────────────────────────────────────────

def make_incident(**kwargs) -> Incident:
    defaults = dict(
        alert_name="PodCrashLooping",
        namespace="production",
        pod_name="api-7d9f-xkj2p",
        severity="critical",
        raw_logs="Error: OOMKilled\nkilled process 1234",
    )
    defaults.update(kwargs)
    return Incident(**defaults)


def make_groq_response(content: str):
    """Builds a minimal mock that looks like a Groq API response."""
    msg      = MagicMock()
    msg.content = content
    choice      = MagicMock()
    choice.message = msg
    resp           = MagicMock()
    resp.choices   = [choice]
    return resp


VALID_LLM_JSON = json.dumps({
    "diagnosis"         : "Pod was OOMKilled due to memory limit breach.",
    "recommended_action": "Increase memory limit in the deployment manifest.",
    "action_type"       : "scale_deployment",
    "risk_if_unresolved": "Pod will keep restarting causing service downtime.",
    "confidence"        : "high",
})


# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture
def mock_agent():
    with patch("agents.evaluator.agent.get_redis_client") as mock_redis, \
         patch("agents.evaluator.agent.Groq") as mock_groq:

        mock_redis.return_value = MagicMock()
        mock_groq.return_value  = MagicMock()

        from agents.evaluator.agent import EvaluatorAgent
        agent = EvaluatorAgent()
        yield agent


# ── Tests ─────────────────────────────────────────────────────────────────────

def test_parse_valid_json_response(mock_agent):
    """LLM JSON response should be parsed into a clean dict."""
    result = mock_agent._parse_llm_response(VALID_LLM_JSON)
    assert result["action_type"] == "scale_deployment"
    assert result["confidence"]  == "high"
    assert "OOMKilled" in result["diagnosis"]


def test_parse_response_with_markdown_fences(mock_agent):
    """Response wrapped in ```json ... ``` fences should still parse."""
    fenced = f"```json\n{VALID_LLM_JSON}\n```"
    result = mock_agent._parse_llm_response(fenced)
    assert result["confidence"] == "high"


def test_parse_invalid_json_falls_back_gracefully(mock_agent):
    """Malformed JSON should fall back to manual_review, not raise."""
    result = mock_agent._parse_llm_response("Sorry, I cannot help with that.")
    assert result["action_type"] == "manual_review"
    assert result["confidence"]  == "low"


def test_enrich_incident_sets_correct_fields(mock_agent):
    """Enrichment should write diagnosis and recommended_action onto incident."""
    incident = make_incident()
    parsed   = json.loads(VALID_LLM_JSON)
    mock_agent._enrich_incident(incident, parsed)

    assert "OOMKilled" in incident.ai_diagnosis
    assert "memory limit" in incident.recommended_action


def test_evaluate_pushes_to_resolver_queue(mock_agent):
    """After evaluation, incident must be pushed to QUEUE_EVALUATOR_TO_RESOLVER."""
    from shared.utils.redis_client import QUEUE_EVALUATOR_TO_RESOLVER

    mock_agent.client.chat.completions.create.return_value = \
        make_groq_response(VALID_LLM_JSON)

    incident = make_incident()
    mock_agent._evaluate(incident)

    queue_key = mock_agent.redis.lpush.call_args[0][0]
    assert queue_key == QUEUE_EVALUATOR_TO_RESOLVER


def test_evaluate_still_forwards_on_llm_failure(mock_agent):
    """Even if Groq fails, the incident should still reach the Resolver queue."""
    from shared.utils.redis_client import QUEUE_EVALUATOR_TO_RESOLVER

    mock_agent.client.chat.completions.create.side_effect = \
        Exception("Groq API timeout")

    incident = make_incident()
    mock_agent._evaluate(incident)

    # Resolver queue should still have received the incident
    assert mock_agent.redis.lpush.called
    queue_key = mock_agent.redis.lpush.call_args[0][0]
    assert queue_key == QUEUE_EVALUATOR_TO_RESOLVER
    assert incident.status == "evaluation_failed"


def test_evaluate_sets_status_evaluated_on_success(mock_agent):
    """Successful LLM call should set incident status to 'evaluated'."""
    mock_agent.client.chat.completions.create.return_value = \
        make_groq_response(VALID_LLM_JSON)

    incident = make_incident()
    mock_agent._evaluate(incident)
    assert incident.status == "evaluated"
