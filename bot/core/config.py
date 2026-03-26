"""
core/config.py
--------------
Single place for all environment variables and constants.
Every other module imports from here — never from os.environ directly.
"""

import os

# ── API credentials ───────────────────────────────────────────────────────────
DISCORD_BOT_TOKEN     = os.environ["DISCORD_BOT_TOKEN"]
COPILOT_API_KEY       = os.environ["COPILOT_API_KEY"]
GITHUB_TOKEN          = os.environ["GITHUB_TOKEN"]

# ── GitHub repo settings ──────────────────────────────────────────────────────
GITHUB_REPO           = os.environ["GITHUB_REPO"]          # e.g. "ali/fyp-project"
GITHUB_BRANCH         = os.environ.get("GITHUB_BRANCH", "main")

# ── Discord settings ──────────────────────────────────────────────────────────
DOCUMENTER_DISCORD_ID = os.environ.get("DOCUMENTER_DISCORD_ID", "")

# ── API endpoints ─────────────────────────────────────────────────────────────
COPILOT_API_URL       = "https://models.inference.ai.azure.com/chat/completions"
COPILOT_MODEL         = "gpt-4o"

# ── FYP project description (used in all AI prompts) ─────────────────────────
FYP_PROJECT_DESCRIPTION = (
    "AI-powered DevOps multi-agent platform for autonomous IT operations. "
    "Uses multiple AI agents (supervisor, monitoring, healing, deployment) "
    "to automate infrastructure management, incident response, and IT workflows."
)