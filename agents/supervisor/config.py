import os
from dotenv import load_dotenv

load_dotenv()

WEBHOOK_HOST = os.getenv("WEBHOOK_HOST", "0.0.0.0")
WEBHOOK_PORT = int(os.getenv("ALERT_WEBHOOK_PORT", 5001))

REDIS_HOST = os.getenv("REDIS_HOST", "redis")

# Kubernetes injects REDIS_PORT as "tcp://ip:port" — extract just the number
_redis_port = os.getenv("REDIS_PORT", "6379")
REDIS_PORT = int(_redis_port.split(":")[-1]) if "tcp" in str(_redis_port) else int(_redis_port)

REDIS_DB   = int(os.getenv("REDIS_DB", 0))

POD_LOG_TAIL_LINES = int(os.getenv("POD_LOG_TAIL_LINES", 80))
POLL_INTERVAL      = int(os.getenv("SUPERVISOR_POLL_INTERVAL", 15))

SEVERITY_MAP = {
    "critical": "critical",
    "warning":  "warning",
    "page":     "critical",
    "info":     "info",
}
DEFAULT_SEVERITY = "warning"
