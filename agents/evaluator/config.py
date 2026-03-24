# agents/evaluator/config.py
"""
Configuration for the Evaluator agent.
All values loaded from environment variables.
"""
import os
from dotenv import load_dotenv

load_dotenv()

# ── Groq LLM ──────────────────────────────────────────────────────────────────
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
GROQ_MODEL   = os.getenv("GROQ_MODEL", "llama3-8b-8192")
LLM_MAX_TOKENS     = int(os.getenv("LLM_MAX_TOKENS", 1024))
LLM_TEMPERATURE    = float(os.getenv("LLM_TEMPERATURE", 0.2))

# ── Redis ─────────────────────────────────────────────────────────────────────
REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT = int(os.getenv("REDIS_PORT", 6379))
REDIS_DB   = int(os.getenv("REDIS_DB", 0))

# ── Queue behaviour ───────────────────────────────────────────────────────────
# BRPOP timeout in seconds — 0 means block forever
QUEUE_BLOCK_TIMEOUT = int(os.getenv("QUEUE_BLOCK_TIMEOUT", 5))

# ── Prompt template ───────────────────────────────────────────────────────────
SYSTEM_PROMPT = """You are an expert Site Reliability Engineer (SRE) and Kubernetes specialist.
You will be given details about a Kubernetes incident including the alert name, affected pod, and raw logs.

Your job is to:
1. Diagnose the root cause clearly and concisely.
2. Provide a specific, actionable remediation step that can be executed immediately.
3. Assess the risk level if the issue is left unresolved.

Always respond in the following exact JSON format with no extra text:
{
  "diagnosis": "<clear explanation of the root cause in 2-3 sentences>",
  "recommended_action": "<single most impactful action to take right now>",
  "action_type": "<one of: restart_pod | scale_deployment | check_resources | review_logs | manual_review>",
  "risk_if_unresolved": "<brief risk description>",
  "confidence": "<high | medium | low>"
}"""
