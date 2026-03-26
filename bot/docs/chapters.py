"""
docs/chapters.py
----------------
IEEE/ACM FYP report chapter definitions and file-to-chapter mapping logic.
Edit CHAPTERS here to add/remove topics or change keywords.
"""

from core.config import FYP_PROJECT_DESCRIPTION

# ── Chapter definitions ───────────────────────────────────────────────────────
CHAPTERS: dict[int, dict] = {
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
        "title": "System Requirements and Analysis",
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
        "title": "System Design and Architecture",
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
        "title": "Testing and Evaluation",
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
        "title": "Conclusion and Future Work",
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


# ── Helpers ───────────────────────────────────────────────────────────────────
def chapter_filepath(ch_num: int) -> str:
    """Return the docs/chapters/ path for a chapter file."""
    slug = (
        CHAPTERS[ch_num]["title"]
        .lower()
        .replace(" ", "_")
        .replace("&", "and")
        .replace("/", "_")
    )
    return f"docs/chapters/chapter_{ch_num:02d}_{slug}.md"


def map_files_to_chapters(changed_files: list[str]) -> dict[int, list[str]]:
    """
    Given a list of changed file paths, return {chapter_num: [files]}.
    Files that don't match any chapter go to Chapter 5 (Implementation).
    """
    result: dict[int, list[str]] = {}

    for ch_num, ch in CHAPTERS.items():
        matched = [
            f for f in changed_files
            if any(kw.lower() in f.lower() for kw in ch["keywords"])
        ]
        if matched:
            result[ch_num] = matched

    matched_all = {f for files in result.values() for f in files}
    unmatched = [f for f in changed_files if f not in matched_all]
    if unmatched:
        result.setdefault(5, []).extend(unmatched)

    return result


def build_chapter_file(ch_num: int, ai_guidance: str) -> str:
    """Build the full markdown content for a chapter file."""
    from datetime import datetime, timezone
    ch = CHAPTERS[ch_num]
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    topics_table = "".join(
        [f"| {topic} | ⬜ Pending | |\n" for topic in ch["topics"]]
    )

    return f"""# Chapter {ch_num}: {ch['title']}

> **FYP Project:** {FYP_PROJECT_DESCRIPTION}
> **Last updated:** {now}
> **Status:** 🔄 In Progress

---

## 📋 Chapter Overview
{ch['description']}

---

## 📊 Topic Status Tracker
Update this table as you write. Change ⬜ Pending → ✅ Done when complete.

| Topic | Status | Notes |
|-------|--------|-------|
{topics_table}
---

## 🤖 AI-Generated Writing Guide

{ai_guidance}

---

## 📝 Commit Updates Log

| Date | Commit | Files Changed | Action Taken |
|------|--------|---------------|--------------|
| {now} | (init) | Initial chapter created | Review topics above |

---

*This file is auto-maintained by FYP Agent. Run `/docs` after each commit for updates.*
"""