"""
core/copilot.py
---------------
Single function for all GitHub Copilot (Azure) API calls.
"""

import requests
from core.config import COPILOT_API_KEY, COPILOT_API_URL, COPILOT_MODEL


def ask(system: str, user: str, max_tokens: int = 700) -> str:
    """
    Send a prompt to GitHub Copilot and return the response text.

    Args:
        system:     System/role prompt
        user:       User message / question
        max_tokens: Max tokens in the response

    Returns:
        Response string from the model
    """
    headers = {
        "Authorization": f"Bearer {COPILOT_API_KEY}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": COPILOT_MODEL,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user",   "content": user},
        ],
        "max_tokens": max_tokens,
        "temperature": 0.3,
    }
    resp = requests.post(COPILOT_API_URL, headers=headers, json=payload, timeout=60)
    resp.raise_for_status()
    return resp.json()["choices"][0]["message"]["content"].strip()