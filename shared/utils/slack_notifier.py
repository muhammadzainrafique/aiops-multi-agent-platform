# shared/utils/slack_notifier.py
"""
Slack notification utility for the AIOps platform.
Sends rich formatted messages when incidents are resolved or critical.
"""
import os
import json
import urllib.request
import urllib.error
from shared.utils.logger import get_logger

log = get_logger("slack")


def _send(payload: dict) -> bool:
    """Sends a payload to the Slack webhook URL. Returns True on success."""
    url = os.getenv("SLACK_WEBHOOK_URL", "")
    if not url:
        log.warning("SLACK_WEBHOOK_URL not set — skipping notification")
        return False
    try:
        data = json.dumps(payload).encode("utf-8")
        req  = urllib.request.Request(
            url,
            data=data,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=5) as resp:
            ok = resp.status == 200
            if ok:
                log.info("Slack notification sent")
            return ok
    except Exception as e:
        log.error(f"Slack notification failed: {e}")
        return False


def notify_incident_created(incident) -> bool:
    """Fires when Supervisor creates a new critical incident."""
    if incident.severity != "critical":
        return False          # Only notify on critical

    SEV_EMOJI = {"critical": "🔴", "warning": "🟡", "info": "🔵"}
    emoji     = SEV_EMOJI.get(incident.severity, "⚪")

    payload = {
        "text": f"{emoji} *New {incident.severity.upper()} Incident Detected*",
        "attachments": [
            {
                "color"   : "#dc2626",
                "blocks"  : [
                    {
                        "type": "section",
                        "fields": [
                            {"type": "mrkdwn", "text": f"*Alert*\n{incident.alert_name}"},
                            {"type": "mrkdwn", "text": f"*Severity*\n{incident.severity.upper()}"},
                            {"type": "mrkdwn", "text": f"*Pod*\n`{incident.namespace}/{incident.pod_name}`"},
                            {"type": "mrkdwn", "text": f"*Incident ID*\n`{incident.id}`"},
                        ]
                    },
                    {
                        "type": "section",
                        "text": {
                            "type": "mrkdwn",
                            "text": f"*Raw Logs (last 3 lines)*\n```{chr(10).join((incident.raw_logs or 'No logs').strip().splitlines()[-3:])}```"
                        }
                    },
                    {
                        "type": "context",
                        "elements": [
                            {"type": "mrkdwn", "text": f"🕐 {incident.created_at} · AIOps Multi-Agent Platform · MUST FYP 2026"}
                        ]
                    }
                ]
            }
        ]
    }
    return _send(payload)


def notify_incident_resolved(incident) -> bool:
    """Fires when Resolver marks an incident as resolved."""
    from datetime import datetime, timezone

    # Calculate resolution time
    try:
        created  = datetime.fromisoformat(incident.created_at)
        resolved = datetime.fromisoformat(incident.resolved_at)
        secs     = int((resolved - created).total_seconds())
        dur      = f"{secs}s" if secs < 60 else f"{secs//60}m {secs%60}s"
    except Exception:
        dur = "—"

    # Determine action emoji
    action = incident.action_taken or ""
    if "RESOURCES PATCHED" in action:
        action_emoji = "📦 Resource limits patched"
    elif "SCALED" in action:
        action_emoji = "📈 Deployment scaled up"
    elif "RESTARTED" in action:
        action_emoji = "🔄 Pod restarted"
    elif "NETWORK RESET" in action:
        action_emoji = "🌐 Network policy reset"
    elif "ROLLBACK" in action:
        action_emoji = "⏪ Deployment rolled back"
    elif "MANUAL" in action.upper():
        action_emoji = "👤 Flagged for manual review"
    else:
        action_emoji = "🔧 Automated action executed"

    payload = {
        "text": f"✅ *Incident Resolved in {dur}*",
        "attachments": [
            {
                "color" : "#059669",
                "blocks": [
                    {
                        "type": "header",
                        "text": {"type": "plain_text", "text": f"✅ {incident.alert_name} — RESOLVED"}
                    },
                    {
                        "type": "section",
                        "fields": [
                            {"type": "mrkdwn", "text": f"*Pod*\n`{incident.namespace}/{incident.pod_name}`"},
                            {"type": "mrkdwn", "text": f"*Resolved In*\n`{dur}`"},
                            {"type": "mrkdwn", "text": f"*Severity*\n{incident.severity.upper()}"},
                            {"type": "mrkdwn", "text": f"*Incident ID*\n`{incident.id}`"},
                        ]
                    },
                    {
                        "type": "section",
                        "text": {
                            "type": "mrkdwn",
                            "text": f"*🧠 AI Diagnosis*\n{incident.ai_diagnosis or 'N/A'}"
                        }
                    },
                    {
                        "type": "section",
                        "text": {
                            "type": "mrkdwn",
                            "text": f"*{action_emoji}*\n{action[:300] if action else 'N/A'}"
                        }
                    },
                    {
                        "type": "divider"
                    },
                    {
                        "type": "context",
                        "elements": [
                            {
                                "type": "mrkdwn",
                                "text": f"🤖 Auto-resolved by AIOps Resolver Agent · MUST FYP 2026 · {incident.resolved_at}"
                            }
                        ]
                    }
                ]
            }
        ]
    }
    return _send(payload)


def notify_evaluation_failed(incident) -> bool:
    """Fires when Groq LLM fails to evaluate an incident."""
    payload = {
        "text": f"⚠️ *AI Evaluation Failed — Manual Review Required*",
        "attachments": [
            {
                "color": "#d97706",
                "blocks": [
                    {
                        "type": "section",
                        "fields": [
                            {"type": "mrkdwn", "text": f"*Alert*\n{incident.alert_name}"},
                            {"type": "mrkdwn", "text": f"*Pod*\n`{incident.namespace}/{incident.pod_name}`"},
                            {"type": "mrkdwn", "text": f"*Error*\n{(incident.ai_diagnosis or '')[:200]}"},
                            {"type": "mrkdwn", "text": f"*ID*\n`{incident.id}`"},
                        ]
                    },
                    {
                        "type": "context",
                        "elements": [{"type": "mrkdwn", "text": "⚠️ Groq API failed · AIOps Platform · Check API key and quota"}]
                    }
                ]
            }
        ]
    }
    return _send(payload)
