"""
FYP Agent - runs inside GitHub Actions on every push.
1. Gets the git diff for the commit
2. Calls GitHub Copilot API to generate:
   - Technical summary  (for documenter)
   - Plain-English summary  (for non-tech member)
3. Posts both to Discord via webhook
4. Appends an entry to CHANGELOG.md
"""

import os
import subprocess
import requests
import json
from datetime import datetime, timezone

# ── Environment variables set by GitHub Actions ──────────────────────────────
COPILOT_API_KEY   = os.environ["COPILOT_API_KEY"]
DISCORD_WEBHOOK   = os.environ["DISCORD_WEBHOOK_URL"]
COMMIT_SHA        = os.environ["COMMIT_SHA"]
COMMIT_MESSAGE    = os.environ["COMMIT_MESSAGE"]
COMMITTER_NAME    = os.environ["COMMITTER_NAME"]
REPO_NAME         = os.environ["REPO_NAME"]
BRANCH_NAME       = os.environ["BRANCH_NAME"]

COPILOT_API_URL   = "https://models.inference.ai.azure.com/chat/completions"
SHORT_SHA         = COMMIT_SHA[:7]
COMMIT_URL        = f"https://github.com/{REPO_NAME}/commit/{COMMIT_SHA}"


# ── 1. Get git diff ───────────────────────────────────────────────────────────
def get_diff() -> str:
    result = subprocess.run(
        ["git", "diff", "HEAD~1", "HEAD", "--unified=5", "--", "*.py"],
        capture_output=True, text=True
    )
    diff = result.stdout.strip()
    # Copilot has a context limit - trim if very large
    if len(diff) > 12000:
        diff = diff[:12000] + "\n\n... (diff truncated for brevity)"
    return diff if diff else "No Python file changes detected in this commit."

# ── 2. Call Copilot API ───────────────────────────────────────────────────────
def call_copilot(system_prompt: str, user_prompt: str) -> str:
    headers = {
        "Authorization": f"Bearer {COPILOT_API_KEY}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": "gpt-4o",
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user",   "content": user_prompt},
        ],
        "max_tokens": 900,
        "temperature": 0.3,
    }
    resp = requests.post(COPILOT_API_URL, headers=headers, json=payload, timeout=60)
    resp.raise_for_status()
    return resp.json()["choices"][0]["message"]["content"].strip()


def get_technical_summary(diff: str) -> str:
    system = (
        "You are a senior software engineer writing a code review summary. "
        "Be concise, precise, and structured. Use bullet points."
    )
    user = (
        f"Commit: {COMMIT_MESSAGE}\n"
        f"Author: {COMMITTER_NAME}\n\n"
        f"Git diff:\n{diff}\n\n"
        "Write a technical summary covering:\n"
        "- What was changed and why\n"
        "- Which functions/classes were added, modified, or removed\n"
        "- Any notable patterns, risks, or dependencies introduced\n"
        "Keep it under 300 words."
    )
    return call_copilot(system, user)


def get_plain_summary(diff: str) -> str:
    system = (
        "You explain software changes to a non-technical person. "
        "Use simple everyday language. No code, no jargon. "
        "Think of explaining to a smart friend who has never programmed."
    )
    user = (
        f"Commit message: {COMMIT_MESSAGE}\n\n"
        f"Git diff:\n{diff}\n\n"
        "Explain in plain English:\n"
        "- What feature or fix this commit delivers\n"
        "- Why it matters for the project\n"
        "- Any impact the team or end-users might notice\n"
        "Keep it under 150 words."
    )
    return call_copilot(system, user)


# ── 3. Post to Discord ────────────────────────────────────────────────────────
def discord_embed(title: str, description: str, color: int) -> dict:
    """Build a Discord embed object."""
    return {
        "title": title,
        "description": description[:4000],   # Discord limit
        "color": color,
        "footer": {"text": f"{REPO_NAME} • {BRANCH_NAME} • {SHORT_SHA}"},
        "url": COMMIT_URL,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


def post_to_discord(tech_summary: str, plain_summary: str):
    payload = {
        "content": f"📦 **New commit by {COMMITTER_NAME}** → [`{SHORT_SHA}`]({COMMIT_URL})\n> {COMMIT_MESSAGE}",
        "embeds": [
            discord_embed(
                title="🔧 Technical Summary  *(for documenter)*",
                description=tech_summary,
                color=0x5865F2,   # Discord blurple
            ),
            discord_embed(
                title="💬 Plain-English Summary  *(for everyone)*",
                description=plain_summary,
                color=0x57F287,   # green
            ),
        ],
    }
    resp = requests.post(DISCORD_WEBHOOK, json=payload, timeout=30)
    resp.raise_for_status()
    print("✅ Posted to Discord.")


# ── 4. Update CHANGELOG.md ────────────────────────────────────────────────────
def update_changelog(tech_summary: str, plain_summary: str):
    date_str = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    entry = (
        f"\n## [{SHORT_SHA}] - {date_str}\n"
        f"**Commit:** {COMMIT_MESSAGE}  \n"
        f"**Author:** {COMMITTER_NAME}  \n"
        f"**Branch:** {BRANCH_NAME}  \n\n"
        f"### Technical Summary\n{tech_summary}\n\n"
        f"### Plain-English Summary\n{plain_summary}\n\n"
        f"---\n"
    )

    changelog_path = "CHANGELOG.md"
    if os.path.exists(changelog_path):
        with open(changelog_path, "r") as f:
            existing = f.read()
    else:
        existing = "# Changelog\n\nAuto-generated by FYP Agent.\n"

    # Insert new entry after the first heading
    if "\n## " in existing:
        insert_point = existing.index("\n## ")
        updated = existing[:insert_point] + entry + existing[insert_point:]
    else:
        updated = existing + entry

    with open(changelog_path, "w") as f:
        f.write(updated)

    print("✅ CHANGELOG.md updated.")

"""
Addition to fyp_agent.py — auto-update chapter doc files on every commit.
Add this function and call it from __main__ block.
"""

def auto_update_chapter_docs(tech_summary: str, changed_files: list):
    """
    Called from GitHub Actions on every commit.
    Posts to Discord which chapters need updating and @mentions the documenter.
    """
    DISCORD_WEBHOOK   = os.environ["DISCORD_WEBHOOK_URL"]
    DOCUMENTER_ID     = os.environ.get("DOCUMENTER_DISCORD_ID", "")
    GITHUB_TOKEN      = os.environ.get("GITHUB_TOKEN", os.environ.get("COPILOT_API_KEY"))
    GITHUB_REPO       = os.environ["REPO_NAME"]
    GITHUB_BRANCH     = os.environ.get("BRANCH_NAME", "main")

    # Map changed files to chapters
    chapter_mapping = {}
    for ch_num, ch in CHAPTERS.items():
        matched = [
            f for f in changed_files
            if any(kw.lower() in f.lower() for kw in ch["keywords"])
        ]
        if matched:
            chapter_mapping[ch_num] = matched
    unmatched = [f for files in chapter_mapping.values() for f in files]
    leftover  = [f for f in changed_files if f not in unmatched]
    if leftover:
        chapter_mapping.setdefault(5, []).extend(leftover)

    if not chapter_mapping:
        return

    mention = f"<@{DOCUMENTER_ID}>" if DOCUMENTER_ID else "📝 **Documenter**"
    chapters_str = ", ".join([
        f"Ch.{n} {CHAPTERS[n]['title']}" for n in chapter_mapping
    ])

    embeds = [
        {
            "title": "📚 Documentation Update Required",
            "description": (
                f"{mention} — a new commit needs documentation updates!\n\n"
                f"**Chapters affected:** {chapters_str}\n\n"
                f"Run `/docs` in Discord for detailed guidance on what to write."
            ),
            "color": 0xEB459E,
            "fields": [
                {
                    "name": f"📖 Chapter {ch_num}: {CHAPTERS[ch_num]['title']}",
                    "value": "Files: " + ", ".join([f"`{f}`" for f in files[:4]]),
                    "inline": False,
                }
                for ch_num, files in chapter_mapping.items()
            ],
            "footer": {"text": f"{GITHUB_REPO} • Run /docs status to see overall progress"},
        }
    ]

    payload = {
        "content": f"{mention} New commit needs documentation! Run `/docs` for details.",
        "embeds": embeds,
    }
    resp = requests.post(DISCORD_WEBHOOK, json=payload, timeout=30)
    if resp.status_code in (200, 204):
        print("✅ Doc update alert posted to Discord.")
    else:
        print(f"⚠️ Discord doc alert failed: {resp.status_code}")


# ── Chapter structure (copy from docs_system.py) ─────────────────────────────
# Paste the CHAPTERS dict here (same as in docs_system.py)
CHAPTERS = {
    1: {"title": "Introduction",                   "keywords": ["main.py","app.py","run.py","config","__init__","readme"]},
    2: {"title": "Literature Review",              "keywords": ["research","literature","survey","related"]},
    3: {"title": "System Requirements & Analysis", "keywords": ["schema","models","database","db","requirements","specs","config"]},
    4: {"title": "System Design & Architecture",   "keywords": ["agent","supervisor","router","pipeline","orchestrat","architecture","workflow","coordinator","manager","dispatcher"]},
    5: {"title": "Implementation",                 "keywords": ["tools","utils","helper","service","handler","processor","client","api","integrat","prompt","llm","groq","monitor","deploy","heal","alert","metric"]},
    6: {"title": "Testing & Evaluation",           "keywords": ["test","eval","benchmark","validate","check","assert","mock"]},
    7: {"title": "Conclusion & Future Work",       "keywords": ["readme","changelog","docs","conclusion","future"]},
}


# ── Add this to the __main__ block of fyp_agent.py ───────────────────────────
# After update_changelog(tech, plain), add:
#
#   print("📚 Posting doc update alert...")
#   changed = get_changed_files()
#   auto_update_chapter_docs(tech, changed)
#
# And add this helper function:

def get_changed_files() -> list:
    """Get list of Python files changed in this commit."""
    result = subprocess.run(
        ["git", "diff", "HEAD~1", "HEAD", "--name-only", "--", "*.py"],
        capture_output=True, text=True
    )
    return [f.strip() for f in result.stdout.strip().splitlines() if f.strip()]

# ── Main ──────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    print(f"🤖 FYP Agent running for commit {SHORT_SHA}...")

    diff = get_diff()
    print(f"📄 Diff size: {len(diff)} chars")

    print("🧠 Generating technical summary...")
    tech = get_technical_summary(diff)

    print("🧠 Generating plain-English summary...")
    plain = get_plain_summary(diff)

    print("📨 Posting to Discord...")
    post_to_discord(tech, plain)

    print("📝 Updating CHANGELOG.md...")
    update_changelog(tech, plain)

    print("✅ FYP Agent done.")