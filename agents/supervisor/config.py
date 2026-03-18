# agents/supervisor/config.py
"""
All configuration for the Supervisor agent loaded from environment variables.
Import this everywhere instead of calling os.getenv() directly.
"""
import os
from dotenv import load_dotenv

load_dotenv()

# ── Webhook server ────────────────────────────────────────────────────────────
WEBHOOK_HOST = os.getenv("WEBHOOK_HOST", "0.0.0.0")
WEBHOOK_PORT = int(os.getenv("ALERT_WEBHOOK_PORT", 5001))

# ── Redis ─────────────────────────────────────────────────────────────────────
REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT = int(os.getenv("REDIS_PORT", 6379))
REDIS_DB   = int(os.getenv("REDIS_DB", 0))

# ── Kubernetes ────────────────────────────────────────────────────────────────
POD_LOG_TAIL_LINES = int(os.getenv("POD_LOG_TAIL_LINES", 80))

# ── Polling ───────────────────────────────────────────────────────────────────
POLL_INTERVAL = int(os.getenv("SUPERVISOR_POLL_INTERVAL", 15))

# ── Severity mapping from Prometheus labels ───────────────────────────────────
SEVERITY_MAP = {
    "critical" : "critical",
    "warning"  : "warning",
    "page"     : "critical",
    "info"     : "info",
}
DEFAULT_SEVERITY = "warning"
