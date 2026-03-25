# agents/resolver/config.py
"""
Configuration for the Resolver agent.
"""
import os
from dotenv import load_dotenv

load_dotenv()

# ── Redis ─────────────────────────────────────────────────────────────────────
REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT = int(os.getenv("REDIS_PORT", 6379))
REDIS_DB   = int(os.getenv("REDIS_DB", 0))

# ── Queue behaviour ───────────────────────────────────────────────────────────
QUEUE_BLOCK_TIMEOUT = int(os.getenv("QUEUE_BLOCK_TIMEOUT", 5))

# ── Remediation settings ──────────────────────────────────────────────────────
# Maximum pods the Resolver is allowed to restart per minute (safety cap)
MAX_RESTARTS_PER_MINUTE = int(os.getenv("MAX_RESTARTS_PER_MINUTE", 5))

# Default namespace if not specified in the incident
DEFAULT_NAMESPACE = os.getenv("DEFAULT_NAMESPACE", "default")

# Scale-up factor when action_type is scale_deployment
SCALE_UP_REPLICAS = int(os.getenv("SCALE_UP_REPLICAS", 2))
