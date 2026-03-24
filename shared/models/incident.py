# shared/models/incident.py
"""
Core data model that flows through the entire agent pipeline.

Life cycle:
  Supervisor creates  →  Evaluator enriches  →  Resolver resolves

All fields are plain Python types so the object serialises cleanly
to/from JSON for Redis queue transport.
"""
import json
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Optional


@dataclass
class Incident:
    # ── Identity ─────────────────────────────────────────────────────────────
    alert_name : str        # e.g. "PodCrashLooping", "HighMemoryUsage"
    namespace  : str        # Kubernetes namespace
    pod_name   : str        # Name of the affected pod
    severity   : str        # "critical" | "warning" | "info"

    # ── Auto-generated ───────────────────────────────────────────────────────
    id         : str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    created_at : str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )

    # ── Populated by Supervisor ──────────────────────────────────────────────
    raw_logs   : str = ""

    # ── Populated by Evaluator (LLM) ────────────────────────────────────────
    ai_diagnosis       : str = ""
    recommended_action : str = ""

    # ── Populated by Resolver ────────────────────────────────────────────────
    action_taken : str = ""

    # ── Lifecycle state ──────────────────────────────────────────────────────
    status      : str            = "open"   # open|in_progress|resolved|failed
    resolved_at : Optional[str]  = None

    # ── Serialisation helpers ────────────────────────────────────────────────
    def to_json(self) -> str:
        return json.dumps(asdict(self))

    @classmethod
    def from_json(cls, data: str) -> "Incident":
        return cls(**json.loads(data))

    def summary(self) -> str:
        """One-line human-readable description for logs and alerts."""
        return (
            f"[{self.id}] {self.severity.upper()} | "
            f"{self.alert_name} | "
            f"{self.namespace}/{self.pod_name} | "
            f"status={self.status}"
        )
