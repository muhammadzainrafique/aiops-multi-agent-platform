"""
FYP Discord Bot
---------------
Slash commands:
  /explain <filename>   - Explains what a specific file does
  /architecture         - High-level overview of the whole project
  /summary              - Recap of the latest commit from CHANGELOG.md
  /help                 - Lists all commands

Setup:
  pip install discord.py requests python-dotenv
  Set env vars: DISCORD_BOT_TOKEN, COPILOT_API_KEY, GITHUB_TOKEN,
                GITHUB_REPO (e.g. username/repo-name), GITHUB_BRANCH (e.g. main)
"""

import os
import base64
import requests
import discord
from discord import app_commands
from discord.ext import commands
from dotenv import load_dotenv

load_dotenv()

DISCORD_BOT_TOKEN = os.environ["DISCORD_BOT_TOKEN"]
COPILOT_API_KEY   = os.environ["COPILOT_API_KEY"]
GITHUB_TOKEN      = os.environ["GITHUB_TOKEN"]
GITHUB_REPO       = os.environ["GITHUB_REPO"]        # e.g. "ali/fyp-project"
GITHUB_BRANCH     = os.environ.get("GITHUB_BRANCH", "main")
COPILOT_API_URL   = "https://models.inference.ai.azure.com/chat/completions"


# ── GitHub helpers ────────────────────────────────────────────────────────────
def get_file_from_github(filepath: str) -> str | None:
    """Fetch a file's content from the GitHub repo."""
    url = f"https://api.github.com/repos/{GITHUB_REPO}/contents/{filepath}?ref={GITHUB_BRANCH}"
    headers = {"Authorization": f"token {GITHUB_TOKEN}", "Accept": "application/vnd.github.v3+json"}
    resp = requests.get(url, headers=headers, timeout=15)
    if resp.status_code != 200:
        return None
    data = resp.json()
    content = base64.b64decode(data["content"]).decode("utf-8", errors="replace")
    return content


def get_repo_tree() -> list[str]:
    """Get list of all Python files in the repo."""
    url = f"https://api.github.com/repos/{GITHUB_REPO}/git/trees/{GITHUB_BRANCH}?recursive=1"
    headers = {"Authorization": f"token {GITHUB_TOKEN}"}
    resp = requests.get(url, headers=headers, timeout=15)
    if resp.status_code != 200:
        return []
    return [
        item["path"] for item in resp.json().get("tree", [])
        if item["type"] == "blob" and item["path"].endswith(".py")
    ]


def get_changelog_latest() -> str | None:
    """Read the latest entry from CHANGELOG.md."""
    content = get_file_from_github("CHANGELOG.md")
    if not content:
        return None
    
    # Split by ## headings to get individual entries
    sections = content.split("\n## ")
    
    # sections[0] is the file header ("# Changelog\n..."), 
    # sections[1] onwards are actual commit entries
    if len(sections) < 2:
        return content[:1500]  # fallback: return raw content
    
    # Return the most recent entry (always sections[1])
    return "## " + sections[1].strip()


# ── Copilot helper ────────────────────────────────────────────────────────────
def call_copilot(system: str, user: str, max_tokens: int = 700) -> str:
    headers = {
        "Authorization": f"Bearer {COPILOT_API_KEY}",
        "Content-Type": "application/json",
        # Remove the Copilot-Integration-Id header entirely
    }
    payload = {
        "model": "gpt-4o",   # or "gpt-4o-mini" if you get model errors
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

"""

The `api.githubcopilot.com` endpoint is for GitHub's internal IDE plugin, not for direct API calls. The correct endpoint for your Student token is `models.inference.ai.azure.com` — this is GitHub Models, which is included in your Copilot subscription and accepts your token directly.

Also, regarding the warning at the top:
"""
# Privileged message content intent is missing

# ── Bot setup ─────────────────────────────────────────────────────────────────
intents = discord.Intents.default()
bot = commands.Bot(command_prefix="!", intents=intents)
tree = bot.tree


@bot.event
async def on_ready():
    await tree.sync()
    print(f"✅ FYP Bot online as {bot.user}")


# ── /explain <filename> ───────────────────────────────────────────────────────
@tree.command(name="explain", description="Explain what a specific file in the project does")
@app_commands.describe(filename="e.g. auth.py or models/user.py")
async def explain(interaction: discord.Interaction, filename: str):
    await interaction.response.defer(thinking=True)

    code = get_file_from_github(filename)
    if not code:
        await interaction.followup.send(
            f"❌ Could not find `{filename}` in `{GITHUB_REPO}` ({GITHUB_BRANCH} branch).\n"
            "Make sure the path is correct, e.g. `models/user.py`"
        )
        return

    # Trim very large files
    if len(code) > 8000:
        code = code[:8000] + "\n\n# ... (file truncated)"

    # Technical explanation
    tech = call_copilot(
        system="You are a senior Python developer doing a code walkthrough.",
        user=(
            f"File: {filename}\n\n```python\n{code}\n```\n\n"
            "Explain this file:\n"
            "- Its purpose and responsibility in the project\n"
            "- Key functions/classes and what they do\n"
            "- Important dependencies or side-effects\n"
            "Be concise. Use bullet points."
        ),
    )

    # Plain-English explanation
    plain = call_copilot(
        system="You explain code files to non-technical people in plain, friendly language.",
        user=(
            f"File: {filename}\n\n```python\n{code}\n```\n\n"
            "Explain what this file does in plain English. "
            "No jargon, no code. Imagine explaining to someone who has never programmed. "
            "2-3 short paragraphs max."
        ),
        max_tokens=400,
    )

    embed1 = discord.Embed(
        title=f"🔧 `{filename}` — Technical Explanation",
        description=tech[:4000],
        color=0x5865F2,
    )
    embed2 = discord.Embed(
        title=f"💬 `{filename}` — Plain English",
        description=plain[:4000],
        color=0x57F287,
    )
    await interaction.followup.send(embeds=[embed1, embed2])


@tree.command(name="architecture", description="Get architecture overview of the project or a specific file/folder")
@app_commands.describe(topic="Optional: specific file, folder, or topic e.g. 'agents/' or 'database layer'")
async def architecture(interaction: discord.Interaction, topic: str = None):
    await interaction.response.defer(thinking=True)

    py_files = get_repo_tree()
    if not py_files:
        await interaction.followup.send("❌ Could not fetch repo file tree. Check GITHUB_TOKEN and GITHUB_REPO.")
        return

    file_tree = "\n".join(py_files[:40])

    # ── Filter files if a topic is mentioned ──────────────────────────────────
    if topic:
        filtered = [f for f in py_files if topic.lower().strip("/") in f.lower()]
        context_files = filtered[:8] if filtered else py_files[:8]
        scope_label = f"Topic: `{topic}`"
    else:
        context_files = [f for f in py_files if "/" not in f][:6]
        scope_label = "Whole project"

    # Read content of relevant files
    snippets = ""
    for fname in context_files:
        content = get_file_from_github(fname) or ""
        snippets += f"\n\n### {fname}\n```python\n{content[:1200]}\n```"

    # ── Prompts change based on whether topic is given ────────────────────────
    if topic:
        tech_prompt = (
            f"Project: {GITHUB_REPO}\n"
            f"Full file tree:\n{file_tree}\n\n"
            f"User is asking about: '{topic}'\n"
            f"Relevant file contents:{snippets}\n\n"
            "Provide a focused technical overview of this specific part:\n"
            "- Purpose and responsibility of this component\n"
            "- Key files and what each does\n"
            "- How it connects to the rest of the project\n"
            "- Any important patterns or dependencies\n"
            "Use bullet points. Max 350 words."
        )
        plain_prompt = (
            f"Project: {GITHUB_REPO}\n"
            f"User is asking about: '{topic}'\n"
            f"Relevant files: {', '.join(context_files)}\n\n"
            "Explain what this part of the project does in plain English. "
            "No jargon. 2-3 short paragraphs."
        )
    else:
        tech_prompt = (
            f"Python project: {GITHUB_REPO}\n\n"
            f"File tree:\n{file_tree}\n\n"
            f"Key file contents:{snippets}\n\n"
            "Provide a technical architecture overview:\n"
            "- Project purpose and main components\n"
            "- How the modules relate to each other\n"
            "- Key data flows\n"
            "- Tech stack and notable dependencies\n"
            "Use bullet points. Max 350 words."
        )
        plain_prompt = (
            f"Project: {GITHUB_REPO}\n"
            f"Files: {', '.join(py_files[:20])}\n\n"
            "Explain what this project does and how it's organised in plain English. "
            "No technical jargon. 2-3 short paragraphs."
        )

    tech_arch = call_copilot(
        system="You are a software architect explaining a project's design.",
        user=tech_prompt,
        max_tokens=900,
    )
    plain_arch = call_copilot(
        system="You explain software projects to non-technical people.",
        user=plain_prompt,
        max_tokens=400,
    )

    title_suffix = f" — `{topic}`" if topic else ""
    embed1 = discord.Embed(
        title=f"🏗️ Architecture{title_suffix} — Technical",
        description=tech_arch[:4000],
        color=0x5865F2,
    )
    embed1.set_footer(text=f"{GITHUB_REPO} • {scope_label} • {len(py_files)} Python files total")

    embed2 = discord.Embed(
        title=f"💬 Architecture{title_suffix} — Plain English",
        description=plain_arch[:4000],
        color=0x57F287,
    )
    await interaction.followup.send(embeds=[embed1, embed2])

# ── /summary ──────────────────────────────────────────────────────────────────
@tree.command(name="summary", description="Show a recap of the latest commit")
async def summary(interaction: discord.Interaction):
    await interaction.response.defer(thinking=True)

    latest = get_changelog_latest()
    if not latest:
        await interaction.followup.send(
            "❌ No CHANGELOG.md found yet. Make a commit first and the agent will create it!"
        )
        return

    embed = discord.Embed(
        title="📋 Latest Commit Summary",
        description=latest[:4000],
        color=0xFEE75C,
    )
    embed.set_footer(text=f"From CHANGELOG.md • {GITHUB_REPO}")
    await interaction.followup.send(embed=embed)


# ── /help ─────────────────────────────────────────────────────────────────────
@tree.command(name="help", description="List all FYP Agent bot commands")
async def help_cmd(interaction: discord.Interaction):
    embed = discord.Embed(
        title="🤖 FYP Agent — Commands",
        color=0x5865F2,
        description=(
            "I automatically post summaries on every commit. You can also ask me things:\n\n"
            "**`/explain <filename>`**\n"
            "→ Explains what a specific file does — both technical and plain English.\n"
            "Example: `/explain auth.py` or `/explain models/user.py`\n\n"
            "**`/architecture`**\n"
            "→ Gives an overview of the whole project structure and how it all fits together.\n\n"
            "**`/summary`**\n"
            "→ Shows the latest commit summary from the CHANGELOG.\n\n"
            "**`/help`**\n"
            "→ You're looking at it 😄"
        ),
    )
    await interaction.response.send_message(embed=embed)

# ── Chapter mapping (FYP IEEE/ACM report structure) ──────────────────────────
# Maps file path keywords → report chapter
CHAPTER_MAP = {
    "Chapter 1 — Introduction": [
        "main.py", "app.py", "run.py", "config", "__init__"
    ],
    "Chapter 2 — Literature Review": [
        "research", "literature", "review", "related", "survey"
    ],
    "Chapter 3 — System Requirements (SRS)": [
        "requirements", "specs", "schema", "models", "database", "db"
    ],
    "Chapter 4 — System Design & Architecture": [
        "agent", "supervisor", "router", "pipeline", "architecture",
        "design", "workflow", "orchestrat"
    ],
    "Chapter 5 — Implementation": [
        "tools", "utils", "helper", "service", "handler", "processor",
        "client", "api", "integrat", "prompt"
    ],
    "Chapter 6 — Testing & Evaluation": [
        "test", "eval", "benchmark", "validate", "check", "assert"
    ],
    "Chapter 7 — Conclusion & Future Work": [
        "readme", "changelog", "docs", "report", "conclusion"
    ],
}

def map_files_to_chapters(changed_files: list[str]) -> dict[str, list[str]]:
    """Return {chapter: [files]} for all changed files."""
    result: dict[str, list[str]] = {}
    for chapter, keywords in CHAPTER_MAP.items():
        matched = [
            f for f in changed_files
            if any(kw.lower() in f.lower() for kw in keywords)
        ]
        if matched:
            result[chapter] = matched
    # Files that didn't match any chapter → Implementation (catch-all)
    matched_all = [f for files in result.values() for f in files]
    unmatched = [f for f in changed_files if f not in matched_all]
    if unmatched:
        result.setdefault("Chapter 5 — Implementation", []).extend(unmatched)
    return result


# ── Helper: parse CHANGELOG.md entries ───────────────────────────────────────
def get_changelog_entries(n: int = None) -> list[str]:
    """
    Return a list of commit entry strings from CHANGELOG.md.
    n=None means all entries, n=2 means last 2.
    """
    content = get_file_from_github("CHANGELOG.md")
    if not content:
        return []
    # Split on ## headings — each is one commit entry
    parts = content.split("\n## ")
    entries = ["## " + p.strip() for p in parts[1:] if p.strip()]
    return entries[:n] if n else entries


# ── /commit ───────────────────────────────────────────────────────────────────
@tree.command(
    name="commit",
    description="Show info about recent commits. Optionally specify how many (e.g. 2)."
)
@app_commands.describe(count="Number of recent commits to show. Leave empty for all.")
async def commit(interaction: discord.Interaction, count: int = None):
    await interaction.response.defer(thinking=True)

    entries = get_changelog_entries(count)
    if not entries:
        await interaction.followup.send(
            "❌ No commits found in CHANGELOG.md yet. Push a commit first!"
        )
        return

    label = f"last {count}" if count else "all"
    header_embed = discord.Embed(
        title=f"📋 Commit History — {label} commit{'s' if not count or count > 1 else ''}",
        description=f"Found **{len(entries)}** entr{'y' if len(entries)==1 else 'ies'} in CHANGELOG.md",
        color=0xFEE75C,
    )
    header_embed.set_footer(text=GITHUB_REPO)
    await interaction.followup.send(embed=header_embed)

    # Send each commit as its own embed (Discord limit: 10 embeds per message)
    # Batch into groups of 5 to stay safe
    batch = []
    for i, entry in enumerate(entries):
        # Extract first line as title (the ## [sha] - date line)
        lines = entry.strip().splitlines()
        title = lines[0].replace("## ", "").strip() if lines else f"Commit #{i+1}"
        body  = "\n".join(lines[1:]).strip()[:1000]  # trim for embed limit

        embed = discord.Embed(
            title=f"🔖 {title}",
            description=body if body else "_No details recorded._",
            color=0x5865F2 if i % 2 == 0 else 0x57F287,
        )
        batch.append(embed)

        if len(batch) == 5:
            await interaction.channel.send(embeds=batch)
            batch = []

    if batch:
        await interaction.channel.send(embeds=batch)


# ── /docs ─────────────────────────────────────────────────────────────────────
@tree.command(
    name="docs",
    description="Tells the documenter which FYP report chapters to update after the latest commit."
)
async def docs(interaction: discord.Interaction):
    await interaction.response.defer(thinking=True)

    # 1. Get latest changelog entry for context
    entries = get_changelog_entries(1)
    if not entries:
        await interaction.followup.send(
            "❌ No commits in CHANGELOG.md yet. Push a commit first!"
        )
        return

    latest_entry = entries[0]

    # 2. Get all Python files to understand what changed
    #    Parse changed files from the latest CHANGELOG entry lines
    changed_files = []
    for line in latest_entry.splitlines():
        # Our changelog entries contain file paths in the diff summaries
        if ".py" in line or "/" in line:
            # Extract anything that looks like a file path
            words = line.split()
            for word in words:
                cleaned = word.strip("*`-•(),")
                if ("/" in cleaned or cleaned.endswith(".py")) and len(cleaned) > 2:
                    changed_files.append(cleaned)

    # Fallback: use full repo tree if we couldn't parse files
    if not changed_files:
        changed_files = get_repo_tree()[:20]

    # 3. Map files to chapters
    chapter_mapping = map_files_to_chapters(changed_files)

    # 4. For each affected chapter, ask Copilot what to write
    chapter_guidance = {}
    for chapter, files in chapter_mapping.items():
        guidance = call_copilot(
            system=(
                "You are an academic writing assistant helping a student write "
                "their Final Year Project report in IEEE/ACM format. "
                "Be specific, practical, and concise."
            ),
            user=(
                f"FYP Project: {GITHUB_REPO}\n"
                f"Report chapter: {chapter}\n"
                f"Files changed in latest commit: {', '.join(files)}\n\n"
                f"Latest commit summary:\n{latest_entry[:800]}\n\n"
                "Based on these code changes, tell the documentation person:\n"
                "1. What to ADD or UPDATE in this chapter (2-3 specific points)\n"
                "2. Topic names they should research on Google/Scholar "
                "(give 3-5 searchable topic names)\n"
                "3. One suggested paragraph opening sentence for this section\n"
                "Be concise. Use bullet points."
            ),
            max_tokens=500,
        )
        chapter_guidance[chapter] = (files, guidance)

    if not chapter_guidance:
        await interaction.followup.send(
            "ℹ️ Could not map any changed files to report chapters. "
            "Try `/architecture` to understand the project structure first."
        )
        return

    # 5. Send header
    chapters_affected = "\n".join([f"• **{ch}**" for ch in chapter_guidance.keys()])
    header = discord.Embed(
        title="📚 Documentation Update Guide",
        description=(
            f"Based on the latest commit, update these chapters in your FYP report:\n\n"
            f"{chapters_affected}\n\n"
            f"Detailed guidance below 👇"
        ),
        color=0xEB459E,
    )
    header.set_footer(text=f"{GITHUB_REPO} • IEEE/ACM FYP Report")
    await interaction.followup.send(embed=header)

    # 6. Send one embed per chapter
    colors = [0x5865F2, 0x57F287, 0xFEE75C, 0xEB459E, 0xED4245, 0x3BA55C, 0xFAA61A]
    for i, (chapter, (files, guidance)) in enumerate(chapter_guidance.items()):
        files_str = ", ".join([f"`{f}`" for f in files[:6]])
        embed = discord.Embed(
            title=f"📖 {chapter}",
            color=colors[i % len(colors)],
        )
        embed.add_field(
            name="📁 Changed files in this chapter",
            value=files_str if files_str else "_general changes_",
            inline=False,
        )
        embed.add_field(
            name="✍️ What to write / update",
            value=guidance[:900],
            inline=False,
        )
        await interaction.channel.send(embed=embed)

"""
FYP Documentation Brain
========================
Add this entire file's contents to discord_bot.py (above bot.run line)
Also requires: DOCUMENTER_DISCORD_ID in your .env file

New commands:
  /docs init          - Scans full repo, creates docs/chapters/ files in GitHub
  /docs               - Latest commit → which chapters to update
  /docs count:<n>     - Last N commits documentation guide
  /docs chapter:<n>   - Deep dive into one specific chapter
  /docs status        - Shows all pending topics across all chapters
"""

import re
from datetime import datetime, timezone

# ── FYP Project Context ───────────────────────────────────────────────────────
FYP_PROJECT_DESCRIPTION = (
    "AI-powered DevOps multi-agent platform for autonomous IT operations. "
    "Uses multiple AI agents (supervisor, monitoring, healing, deployment) "
    "to automate infrastructure management, incident response, and IT workflows."
)

# ── IEEE/ACM Chapter Structure for this FYP ──────────────────────────────────
CHAPTERS = {
    1: {
        "title": "Introduction",
        "description": "Problem statement, motivation, objectives, scope, report structure",
        "keywords": ["main.py", "app.py", "run.py", "config", "__init__", "readme"],
        "topics": [
            "Autonomous IT Operations",
            "DevOps automation challenges",
            "Multi-agent systems in IT",
            "Problem statement: manual IT operations",
            "Research objectives and scope",
        ],
    },
    2: {
        "title": "Literature Review",
        "description": "Related work, existing tools, research gaps, theoretical background",
        "keywords": ["research", "literature", "survey", "related"],
        "topics": [
            "Multi-agent systems (MAS) in cloud computing",
            "AIOps: AI for IT operations",
            "Existing DevOps tools: Kubernetes, Prometheus, PagerDuty",
            "Large Language Models for automation",
            "Autonomous healing systems",
            "Comparison of existing platforms",
        ],
    },
    3: {
        "title": "System Requirements & Analysis",
        "description": "Functional/non-functional requirements, use cases, SRS",
        "keywords": ["schema", "models", "database", "db", "requirements", "specs", "config"],
        "topics": [
            "Functional requirements of autonomous DevOps",
            "Non-functional requirements: scalability, reliability",
            "Use case diagrams for IT operations",
            "System actors and interactions",
            "Data models and schema design",
            "Technology stack justification",
        ],
    },
    4: {
        "title": "System Design & Architecture",
        "description": "Architecture diagrams, agent design, data flow, component design",
        "keywords": [
            "agent", "supervisor", "router", "pipeline", "orchestrat",
            "architecture", "workflow", "coordinator", "manager", "dispatcher",
        ],
        "topics": [
            "Multi-agent architecture pattern",
            "Supervisor agent design",
            "Agent communication protocols",
            "System architecture diagram (UML)",
            "Data flow diagrams",
            "Microservices vs agent-based design",
            "Redis pub/sub for agent messaging",
            "Kubernetes operator pattern",
        ],
    },
    5: {
        "title": "Implementation",
        "description": "Code walkthrough, tools used, key algorithms, integration details",
        "keywords": [
            "tools", "utils", "helper", "service", "handler", "processor",
            "client", "api", "integrat", "prompt", "llm", "groq", "openai",
            "monitor", "deploy", "heal", "alert", "metric",
        ],
        "topics": [
            "Agent implementation in Python",
            "LLM integration with Groq/OpenAI API",
            "Kubernetes Python client usage",
            "Redis for inter-agent communication",
            "Prometheus metrics collection",
            "Autonomous healing algorithms",
            "Deployment pipeline automation",
            "Prompt engineering for DevOps agents",
        ],
    },
    6: {
        "title": "Testing & Evaluation",
        "description": "Test cases, results, performance evaluation, comparison",
        "keywords": ["test", "eval", "benchmark", "validate", "check", "assert", "mock"],
        "topics": [
            "Unit testing AI agents",
            "Integration testing multi-agent systems",
            "Performance benchmarking",
            "Fault injection testing",
            "MTTD and MTTR metrics",
            "Comparison with manual operations",
            "Evaluation methodology",
        ],
    },
    7: {
        "title": "Conclusion & Future Work",
        "description": "Summary of contributions, limitations, future enhancements",
        "keywords": ["readme", "changelog", "docs", "conclusion", "future"],
        "topics": [
            "Summary of research contributions",
            "Limitations of current system",
            "Future enhancements",
            "Broader impact of autonomous DevOps",
            "Ethical considerations of AI in IT ops",
        ],
    },
}

DOCUMENTER_DISCORD_ID = os.environ.get("DOCUMENTER_DISCORD_ID", "")


# ── GitHub write helper ───────────────────────────────────────────────────────
def push_file_to_github(filepath: str, content: str, commit_msg: str) -> bool:
    """Create or update a file in the GitHub repo via API."""
    url = f"https://api.github.com/repos/{GITHUB_REPO}/contents/{filepath}"
    headers = {
        "Authorization": f"token {GITHUB_TOKEN}",
        "Accept": "application/vnd.github.v3+json",
    }
    # Check if file exists (need its SHA to update)
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


def map_files_to_chapters(changed_files: list) -> dict:
    """Return {chapter_num: [files]} for changed files."""
    result = {}
    for ch_num, ch in CHAPTERS.items():
        matched = [
            f for f in changed_files
            if any(kw.lower() in f.lower() for kw in ch["keywords"])
        ]
        if matched:
            result[ch_num] = matched
    # Unmatched → Chapter 5 (Implementation catch-all)
    matched_all = {f for files in result.values() for f in files}
    unmatched = [f for f in changed_files if f not in matched_all]
    if unmatched:
        result.setdefault(5, []).extend(unmatched)
    return result


def get_chapter_file(chapter_num: int) -> str | None:
    """Fetch existing chapter doc file content."""
    path = f"docs/chapters/chapter_{chapter_num:02d}_{CHAPTERS[chapter_num]['title'].lower().replace(' ', '_').replace('&','and')}.md"
    return get_file_from_github(path)


def chapter_filepath(chapter_num: int) -> str:
    title_slug = CHAPTERS[chapter_num]["title"].lower().replace(" ", "_").replace("&", "and").replace("/", "_")
    return f"docs/chapters/chapter_{chapter_num:02d}_{title_slug}.md"


# ── /docs init ────────────────────────────────────────────────────────────────
@tree.command(
    name="docs_init",
    description="One-time setup: scans full repo and creates docs/chapters/ files in GitHub"
)
async def docs_init(interaction: discord.Interaction):
    await interaction.response.defer(thinking=True)

    await interaction.followup.send(
        "🔍 Scanning your full repo and generating documentation brain...\n"
        "This may take ~1 minute. I'll post each chapter as it's created."
    )

    py_files = get_repo_tree()
    file_tree = "\n".join(py_files[:60])

    # Read key files for context
    snippets = ""
    root_files = [f for f in py_files if "/" not in f][:5]
    for fname in root_files:
        content = get_file_from_github(fname) or ""
        snippets += f"\n\n### {fname}\n```python\n{content[:800]}\n```"

    created = []
    for ch_num, ch in CHAPTERS.items():
        # Generate rich content for this chapter
        guidance = call_copilot(
            system=(
                "You are an academic writing assistant for a Final Year Project (FYP) report "
                "in IEEE/ACM format. The project is: " + FYP_PROJECT_DESCRIPTION +
                " Be specific, detailed, and practical. Use markdown formatting."
            ),
            user=(
                f"Generate a documentation guide for Chapter {ch_num}: {ch['title']}\n"
                f"Chapter covers: {ch['description']}\n\n"
                f"Project file structure:\n{file_tree}\n\n"
                f"Key source files:\n{snippets}\n\n"
                "Provide:\n"
                "1. A brief description of what this chapter should cover for THIS specific project\n"
                "2. A list of 6-8 section headings the documenter should write\n"
                "3. For each section: 2-3 bullet points of what to include\n"
                "4. 5-7 specific Google/Google Scholar search topics relevant to this project\n"
                "5. Suggested tools/diagrams to include (e.g. UML, flowcharts, tables)\n"
                "Format everything in clean markdown."
            ),
            max_tokens=1000,
        )

        # Build the chapter markdown file
        now = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        chapter_content = f"""# Chapter {ch_num}: {ch['title']}

> **FYP Project:** {FYP_PROJECT_DESCRIPTION}
> **Last updated:** {now}
> **Status:** 🔄 In Progress

---

## 📋 Chapter Overview
{ch['description']}

---

## 📊 Topic Status Tracker

| Topic | Status | Notes |
|-------|--------|-------|
{"".join([f"| {topic} | ⬜ Pending | |\n" for topic in ch['topics']])}

---

## 🤖 AI-Generated Writing Guide

{guidance}

---

## 📝 Commit Updates Log

| Date | Commit | What Changed | Action Taken |
|------|--------|--------------|--------------|
| {now} | (init) | Initial chapter created | Review topics above |

---

*This file is auto-maintained by FYP Agent. Update the Status Tracker as you write.*
"""
        filepath = chapter_filepath(ch_num)
        success = push_file_to_github(
            filepath,
            chapter_content,
            f"docs: init chapter {ch_num} - {ch['title']} [skip ci]"
        )

        status = "✅" if success else "❌"
        created.append(f"{status} `{filepath}`")

        embed = discord.Embed(
            title=f"📖 Chapter {ch_num}: {ch['title']} {'created' if success else 'FAILED'}",
            description=f"**Topics to cover:**\n" + "\n".join([f"• ⬜ {t}" for t in ch['topics']]),
            color=0x57F287 if success else 0xED4245,
        )
        await interaction.channel.send(embed=embed)

    # Final summary
    summary_embed = discord.Embed(
        title="✅ Documentation Brain Initialized!",
        description=(
            "Created in your repo under `docs/chapters/`:\n\n" +
            "\n".join(created) +
            "\n\n**Next steps for your documenter:**\n"
            "1. Open each file in GitHub\n"
            "2. Use the Topic Status Tracker (⬜ = pending)\n"
            "3. Search each topic on Google Scholar\n"
            "4. Run `/docs` after every commit to get update instructions"
        ),
        color=0xEB459E,
    )
    summary_embed.set_footer(text=f"{GITHUB_REPO} • docs/chapters/")
    await interaction.channel.send(embed=summary_embed)


# ── /docs (with optional params) ─────────────────────────────────────────────
@tree.command(
    name="docs",
    description="Documentation guide. Use: /docs | /docs count:3 | /docs chapter:4 | /docs status"
)
@app_commands.describe(
    mode="'status' to see all pending topics, or leave empty for latest commit guide",
    count="Number of recent commits to analyze (e.g. 3)",
    chapter="Specific chapter number to focus on (1-7)",
)
async def docs(
    interaction: discord.Interaction,
    mode: str = None,
    count: int = None,
    chapter: int = None,
):
    await interaction.response.defer(thinking=True)

    # ── /docs status ──────────────────────────────────────────────────────────
    if mode and mode.lower() == "status":
        embeds = []
        for ch_num, ch in CHAPTERS.items():
            content = get_chapter_file(ch_num)
            if not content:
                continue
            # Parse pending topics from the status tracker table
            pending = re.findall(r"\| (.+?) \| ⬜ Pending \|", content)
            done    = re.findall(r"\| (.+?) \| ✅ Done \|",    content)
            if not pending and not done:
                continue
            pct = int(len(done) / max(len(done) + len(pending), 1) * 100)
            bar = "█" * (pct // 10) + "░" * (10 - pct // 10)
            desc = f"`{bar}` {pct}%\n\n"
            if pending:
                desc += "**⬜ Pending:**\n" + "\n".join([f"• {t}" for t in pending[:6]])
            if done:
                desc += "\n**✅ Done:**\n" + "\n".join([f"• {t}" for t in done[:4]])
            embeds.append(discord.Embed(
                title=f"Chapter {ch_num}: {ch['title']}",
                description=desc[:1000],
                color=0x57F287 if pct == 100 else (0xFEE75C if pct > 0 else 0xED4245),
            ))

        if not embeds:
            await interaction.followup.send(
                "❌ No chapter files found. Run `/docs_init` first!"
            )
            return

        header = discord.Embed(
            title="📊 Documentation Status — All Chapters",
            description=f"FYP Report progress across {len(embeds)} chapters",
            color=0xEB459E,
        )
        await interaction.followup.send(embed=header)
        for e in embeds:
            await interaction.channel.send(embed=e)
        return

    # ── /docs chapter:<n> ─────────────────────────────────────────────────────
    if chapter:
        if chapter not in CHAPTERS:
            await interaction.followup.send("❌ Chapter must be between 1 and 7.")
            return

        ch = CHAPTERS[chapter]
        existing = get_chapter_file(chapter) or ""
        py_files = get_repo_tree()

        # Find files relevant to this chapter
        relevant = [
            f for f in py_files
            if any(kw.lower() in f.lower() for kw in ch["keywords"])
        ][:8]

        snippets = ""
        for fname in relevant[:3]:
            content = get_file_from_github(fname) or ""
            snippets += f"\n### {fname}\n```python\n{content[:600]}\n```"

        deep_guide = call_copilot(
            system=(
                "You are an expert academic writing coach for IEEE/ACM FYP reports. "
                "Project: " + FYP_PROJECT_DESCRIPTION
            ),
            user=(
                f"Give a deep writing guide for Chapter {chapter}: {ch['title']}\n"
                f"Chapter purpose: {ch['description']}\n"
                f"Relevant project files: {', '.join(relevant)}\n"
                f"File snippets:{snippets}\n\n"
                "Provide:\n"
                "1. Exact section headings to use (numbered)\n"
                "2. What to write in each section (3-4 points each)\n"
                "3. Specific diagrams or tables to include\n"
                "4. 6 precise Google Scholar search queries for this chapter\n"
                "5. Common mistakes to avoid in this chapter\n"
                "6. An example paragraph opener for the introduction of this chapter\n"
                "Use markdown, be very specific to the AI DevOps project."
            ),
            max_tokens=1000,
        )

        embed1 = discord.Embed(
            title=f"📖 Deep Guide — Chapter {chapter}: {ch['title']}",
            description=deep_guide[:4000],
            color=0x5865F2,
        )
        embed1.set_footer(text=f"Run /docs status to see your overall progress")
        await interaction.followup.send(embed=embed1)
        return

    # ── /docs (latest commit) or /docs count:<n> ──────────────────────────────
    n = count if count else 1
    entries = get_changelog_entries(n)
    if not entries:
        await interaction.followup.send(
            "❌ No commits in CHANGELOG.md yet. Push a commit first!"
        )
        return

    combined_text = "\n\n".join(entries)

    # Extract changed files from changelog entries
    changed_files = []
    for line in combined_text.splitlines():
        words = line.split()
        for word in words:
            cleaned = word.strip("*`-•(),:")
            if ("/" in cleaned or cleaned.endswith(".py")) and 2 < len(cleaned) < 80:
                changed_files.append(cleaned)

    if not changed_files:
        changed_files = get_repo_tree()[:15]

    chapter_mapping = map_files_to_chapters(list(set(changed_files)))

    if not chapter_mapping:
        await interaction.followup.send("ℹ️ Could not map changes to chapters. Try `/docs_init` first.")
        return

    label = f"last {n} commits" if n > 1 else "latest commit"

    # Header embed
    chapters_list = "\n".join([
        f"• **Chapter {cn}: {CHAPTERS[cn]['title']}** ({len(files)} file{'s' if len(files)>1 else ''} changed)"
        for cn, files in chapter_mapping.items()
    ])
    header = discord.Embed(
        title=f"📚 Documentation Update — {label}",
        description=(
            f"These chapters need attention:\n\n{chapters_list}\n\n"
            f"{'<@' + DOCUMENTER_DISCORD_ID + '> please update these sections 👇' if DOCUMENTER_DISCORD_ID else '📝 Documenter: update these sections 👇'}"
        ),
        color=0xEB459E,
    )
    await interaction.followup.send(embed=header)

    # Per-chapter guidance
    colors = [0x5865F2, 0x57F287, 0xFEE75C, 0xEB459E, 0xED4245, 0x3BA55C, 0xFAA61A]
    for i, (ch_num, files) in enumerate(chapter_mapping.items()):
        ch = CHAPTERS[ch_num]

        guidance = call_copilot(
            system=(
                "You are an academic writing assistant for an IEEE/ACM FYP report. "
                "Project: " + FYP_PROJECT_DESCRIPTION +
                " Be specific and concise. Use bullet points."
            ),
            user=(
                f"Chapter {ch_num}: {ch['title']}\n"
                f"Changed files: {', '.join(files)}\n\n"
                f"Commit context:\n{combined_text[:600]}\n\n"
                "Based on these code changes, tell the documenter:\n"
                "1. Exactly what to ADD or UPDATE in this chapter (3 specific points)\n"
                "2. Which existing section to update (if chapter exists)\n"
                "3. 3-4 Google Scholar search topics relevant to these changes\n"
                "4. One suggested sentence to start the new/updated paragraph\n"
                "Be very specific to this AI DevOps platform project."
            ),
            max_tokens=500,
        )

        # Update the chapter file in GitHub with a new log entry
        existing_content = get_chapter_file(ch_num)
        if existing_content:
            now = datetime.now(timezone.utc).strftime("%Y-%m-%d")
            sha_short = entries[0].split("]")[0].replace("## [", "").strip() if entries else "unknown"
            log_row = f"| {now} | {sha_short} | {', '.join(files[:2])} | Review guidance in Discord |\n"
            updated = existing_content.replace(
                "| (init) | Initial chapter created | Review topics above |",
                f"(init) | Initial chapter created | Review topics above |\n{log_row}"
            ) if "(init)" in existing_content else existing_content + f"\n| {now} | {sha_short} | {', '.join(files[:2])} | Review guidance in Discord |\n"
            push_file_to_github(
                chapter_filepath(ch_num),
                updated,
                f"docs: update chapter {ch_num} log for commit {sha_short} [skip ci]"
            )

        files_str = " ".join([f"`{f}`" for f in files[:5]])
        embed = discord.Embed(
            title=f"📖 Chapter {ch_num}: {ch['title']}",
            color=colors[i % len(colors)],
        )
        embed.add_field(name="📁 Changed files", value=files_str, inline=False)
        embed.add_field(name="✍️ What to write / update", value=guidance[:900], inline=False)
        embed.set_footer(text=f"See docs/chapters/chapter_0{ch_num}_*.md in your repo for full guide")
        await interaction.channel.send(embed=embed)

# ── Run ───────────────────────────────────────────────────────────────────────
bot.run(DISCORD_BOT_TOKEN)