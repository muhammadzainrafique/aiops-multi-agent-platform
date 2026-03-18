# shared/utils/redis_client.py
"""
Shared Redis client for message queue and distributed state storage.
Agents communicate by pushing/popping JSON from named queues.
"""
import os
import redis
from shared.utils.logger import get_logger

logger = get_logger("redis_client")

# ── Queue key constants (used by all agents) ─────────────────────────────────
QUEUE_SUPERVISOR_TO_EVALUATOR = "queue:supervisor:evaluator"
QUEUE_EVALUATOR_TO_RESOLVER   = "queue:evaluator:resolver"
STORE_INCIDENTS               = "store:incidents"


def get_redis_client() -> redis.Redis:
    """
    Returns a connected Redis client using environment variables.
    Raises ConnectionError if Redis is unreachable.
    """
    host = os.getenv("REDIS_HOST", "localhost")
    port = int(os.getenv("REDIS_PORT", 6379))
    db   = int(os.getenv("REDIS_DB", 0))

    r = redis.Redis(
        host=host,
        port=port,
        db=db,
        decode_responses=True,
        socket_connect_timeout=5,
    )
    try:
        r.ping()
        logger.info(f"Redis connected → {host}:{port}")
    except redis.ConnectionError as e:
        logger.error(f"Redis connection failed: {e}")
        raise

    return r
