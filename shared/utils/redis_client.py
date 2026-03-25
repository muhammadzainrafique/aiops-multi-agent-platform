import os
import time
import redis
from shared.utils.logger import get_logger

logger = get_logger("redis_client")

QUEUE_SUPERVISOR_TO_EVALUATOR = "queue:supervisor:evaluator"
QUEUE_EVALUATOR_TO_RESOLVER   = "queue:evaluator:resolver"
STORE_INCIDENTS               = "store:incidents"


def get_redis_client() -> redis.Redis:
    host = os.getenv("REDIS_HOST", "redis")

    # Kubernetes injects REDIS_PORT as "tcp://ip:port" — extract just the number
    _port = os.getenv("REDIS_PORT", "6379")
    port  = int(_port.split(":")[-1]) if "tcp" in str(_port) else int(_port)

    db = int(os.getenv("REDIS_DB", 0))

    for attempt in range(1, 11):
        try:
            r = redis.Redis(
                host=host, port=port, db=db,
                decode_responses=True,
                socket_connect_timeout=5,
            )
            r.ping()
            logger.info(f"Redis connected → {host}:{port}")
            return r
        except redis.ConnectionError:
            logger.warning(f"Redis not ready, retrying {attempt}/10 in 3s...")
            time.sleep(3)

    raise RuntimeError(f"Cannot connect to Redis at {host}:{port} after 10 attempts")
