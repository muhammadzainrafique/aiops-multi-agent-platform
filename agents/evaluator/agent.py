# agents/evaluator/agent.py
"""
Evaluator Agent — the AI brain of the AIOps pipeline.

Responsibilities:
  1. Continuously consume incidents from the Redis queue.
  2. Build a structured prompt using the incident's alert name, 
     namespace, pod name, severity, and raw logs.
  3. Send the prompt to Groq (Llama 3) and parse the JSON response.
  4. Enrich the Incident with ai_diagnosis and recommended_action.
  5. Push the enriched Incident to the Resolver queue.
"""
import json
import time
from groq import Groq

from shared.utils.logger import get_logger
from shared.utils.redis_client import (
    get_redis_client,
    QUEUE_SUPERVISOR_TO_EVALUATOR,
    QUEUE_EVALUATOR_TO_RESOLVER,
    STORE_INCIDENTS,
)
from shared.models.incident import Incident
from agents.evaluator.config import (
    GROQ_API_KEY, GROQ_MODEL,
    LLM_MAX_TOKENS, LLM_TEMPERATURE,
    QUEUE_BLOCK_TIMEOUT, SYSTEM_PROMPT,
)

log = get_logger("evaluator")


class EvaluatorAgent:
    """
    Listens to the supervisor queue, analyses each incident with an LLM,
    and forwards enriched incidents to the resolver queue.
    """

    def __init__(self):
        self.redis  = get_redis_client()
        self.client = Groq(api_key=GROQ_API_KEY)
        log.info(f"Evaluator agent initialised — model: {GROQ_MODEL}")

    # ── Main loop ─────────────────────────────────────────────────────────────

    def run(self):
        """
        Blocking loop — waits for incidents on the queue and processes them.
        Runs forever until the process is killed.
        """
        log.info(f"Listening on queue: {QUEUE_SUPERVISOR_TO_EVALUATOR}")

        while True:
            try:
                self._consume_one()
            except KeyboardInterrupt:
                log.info("Evaluator agent shutting down")
                break
            except Exception as e:
                log.error(f"Unexpected error in consumer loop: {e}")
                time.sleep(3)   # brief back-off before retrying

    def _consume_one(self):
        """
        Blocks on BRPOP for up to QUEUE_BLOCK_TIMEOUT seconds.
        If an incident arrives, processes it fully before returning.
        """
        result = self.redis.brpop(
            QUEUE_SUPERVISOR_TO_EVALUATOR,
            timeout=QUEUE_BLOCK_TIMEOUT,
        )

        if result is None:
            return   # timeout — loop again

        _, raw = result
        try:
            incident = Incident.from_json(raw)
        except Exception as e:
            log.error(f"Failed to deserialise incident: {e} — raw: {raw[:120]}")
            return

        log.info(f"Received incident: {incident.summary()}")
        self._evaluate(incident)

    # ── Core evaluation logic ─────────────────────────────────────────────────

    def _evaluate(self, incident: Incident):
        """
        Full evaluation pipeline for one incident:
          build prompt → call LLM → parse response → enrich → re-queue
        """
        incident.status = "in_progress"
        self._save(incident)

        try:
            llm_response = self._call_llm(incident)
            parsed       = self._parse_llm_response(llm_response)
            self._enrich_incident(incident, parsed)
            incident.status = "evaluated"

        except Exception as e:
            log.error(f"LLM evaluation failed for {incident.id}: {e}")
            incident.ai_diagnosis      = f"Evaluation failed: {e}"
            incident.recommended_action = "Manual review required — LLM unavailable"
            incident.status            = "evaluation_failed"

        finally:
            self._save(incident)
            # Always forward to Resolver — even on failure so it can flag it
            self.redis.lpush(QUEUE_EVALUATOR_TO_RESOLVER, incident.to_json())
            log.info(f"Incident {incident.id} forwarded to Resolver → {incident.status}")

    def _call_llm(self, incident: Incident) -> str:
        """
        Builds the user prompt and calls the Groq API.
        Returns the raw LLM text response.
        """
        user_prompt = f"""
INCIDENT DETAILS
────────────────
Alert Name : {incident.alert_name}
Namespace  : {incident.namespace}
Pod Name   : {incident.pod_name}
Severity   : {incident.severity.upper()}

RAW POD LOGS (last 80 lines)
─────────────────────────────
{incident.raw_logs or "No logs available — pod may not be running."}

Please diagnose this incident and provide your remediation recommendation.
"""

        log.info(f"Calling Groq API for incident {incident.id} ...")

        response = self.client.chat.completions.create(
            model=GROQ_MODEL,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user",   "content": user_prompt},
            ],
            max_tokens=LLM_MAX_TOKENS,
            temperature=LLM_TEMPERATURE,
        )

        raw_text = response.choices[0].message.content.strip()
        log.info(f"Groq response received for {incident.id} ({len(raw_text)} chars)")
        return raw_text

    def _parse_llm_response(self, raw_text: str) -> dict:
        """
        Parses the LLM JSON response.
        Strips markdown code fences if Groq wraps the response in them.
        Returns a dict with diagnosis, recommended_action, action_type, etc.
        """
        # Strip ```json ... ``` fences if present
        cleaned = raw_text.strip()
        if cleaned.startswith("```"):
            lines   = cleaned.split("\n")
            cleaned = "\n".join(lines[1:-1])

        try:
            return json.loads(cleaned)
        except json.JSONDecodeError as e:
            log.warning(f"JSON parse failed, using raw text as diagnosis: {e}")
            return {
                "diagnosis"         : raw_text,
                "recommended_action": "Review the LLM output above manually",
                "action_type"       : "manual_review",
                "risk_if_unresolved": "Unknown",
                "confidence"        : "low",
            }

    def _enrich_incident(self, incident: Incident, parsed: dict):
        """Writes LLM output fields back onto the Incident object."""
        incident.ai_diagnosis       = parsed.get("diagnosis", "")
        incident.recommended_action = parsed.get("recommended_action", "")

        # Store extra LLM fields as part of the action_taken field temporarily
        # (Resolver will overwrite action_taken with what it actually did)
        incident.action_taken = json.dumps({
            "action_type"       : parsed.get("action_type", "manual_review"),
            "risk_if_unresolved": parsed.get("risk_if_unresolved", ""),
            "confidence"        : parsed.get("confidence", "low"),
        })

        log.info(
            f"Incident {incident.id} enriched | "
            f"action_type={parsed.get('action_type')} | "
            f"confidence={parsed.get('confidence')}"
        )

    def _save(self, incident: Incident):
        """Persists the current incident state to the Redis hash store."""
        self.redis.hset(STORE_INCIDENTS, incident.id, incident.to_json())
