"""
core/github.py
--------------
All GitHub REST API calls in one place.
"""

import base64
import requests
from core.config import GITHUB_TOKEN, GITHUB_REPO, GITHUB_BRANCH


def get_file(filepath: str) -> str | None:
    """Fetch a file's decoded text content from the repo."""
    url = f"https://api.github.com/repos/{GITHUB_REPO}/contents/{filepath}?ref={GITHUB_BRANCH}"
    headers = {
        "Authorization": f"token {GITHUB_TOKEN}",
        "Accept": "application/vnd.github.v3+json",
    }
    resp = requests.get(url, headers=headers, timeout=15)
    if resp.status_code != 200:
        return None
    return base64.b64decode(resp.json()["content"]).decode("utf-8", errors="replace")


def push_file(filepath: str, content: str, commit_msg: str) -> bool:
    """Create or update a file in the repo. Returns True on success."""
    url = f"https://api.github.com/repos/{GITHUB_REPO}/contents/{filepath}"
    headers = {
        "Authorization": f"token {GITHUB_TOKEN}",
        "Accept": "application/vnd.github.v3+json",
    }
    # Need existing SHA to update a file
    resp = requests.get(url + f"?ref={GITHUB_BRANCH}", headers=headers, timeout=15)
    sha = resp.json().get("sha") if resp.status_code == 200 else None

    payload = {
        "message": commit_msg,
        "content": base64.b64encode(content.encode()).decode(),
        "branch": GITHUB_BRANCH,
    }
    if sha:
        payload["sha"] = sha

    resp = requests.put(url, headers=headers, json=payload, timeout=30)
    return resp.status_code in (200, 201)


def get_repo_tree() -> list[str]:
    """Return list of all .py file paths in the repo."""
    url = f"https://api.github.com/repos/{GITHUB_REPO}/git/trees/{GITHUB_BRANCH}?recursive=1"
    headers = {"Authorization": f"token {GITHUB_TOKEN}"}
    resp = requests.get(url, headers=headers, timeout=15)
    if resp.status_code != 200:
        return []
    return [
        item["path"]
        for item in resp.json().get("tree", [])
        if item["type"] == "blob" and item["path"].endswith(".py")
    ]


def get_changelog_entries(n: int = None) -> list[str]:
    """
    Parse CHANGELOG.md and return commit entries as a list of strings.
    n=None → all entries. n=3 → last 3 entries.
    """
    content = get_file("CHANGELOG.md")
    if not content:
        return []
    parts = content.split("\n## ")
    entries = ["## " + p.strip() for p in parts[1:] if p.strip()]
    return entries[:n] if n else entries