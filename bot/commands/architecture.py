"""
commands/architecture.py
------------------------
/architecture [topic] — project or focused architecture overview
"""

import discord
from discord import app_commands
from core.github  import get_file, get_repo_tree
from core.copilot import ask
from core.config  import GITHUB_REPO


def setup(tree: app_commands.CommandTree):

    @tree.command(name="architecture", description="Project architecture overview, or focus on a file/folder/topic")
    @app_commands.describe(topic="Optional: e.g. 'agents/' or 'database layer' or 'supervisor'")
    async def architecture(interaction: discord.Interaction, topic: str = None):
        await interaction.response.defer(thinking=True)

        py_files = get_repo_tree()
        if not py_files:
            await interaction.followup.send("❌ Could not fetch repo file tree. Check GITHUB_TOKEN and GITHUB_REPO.")
            return

        file_tree = "\n".join(py_files[:40])

        if topic:
            context_files = [f for f in py_files if topic.lower().strip("/") in f.lower()][:8] or py_files[:8]
            scope_label = f"Topic: `{topic}`"
        else:
            context_files = [f for f in py_files if "/" not in f][:6]
            scope_label = "Whole project"

        snippets = ""
        for fname in context_files:
            content = get_file(fname) or ""
            snippets += f"\n\n### {fname}\n```python\n{content[:1200]}\n```"

        if topic:
            tech_prompt = (
                f"Project: {GITHUB_REPO}\nFull file tree:\n{file_tree}\n\n"
                f"Focus on: '{topic}'\nRelevant files:{snippets}\n\n"
                "Technical overview of this component:\n"
                "- Purpose and responsibility\n- Key files and what each does\n"
                "- How it connects to the rest of the project\n- Patterns or dependencies\n"
                "Bullet points. Max 350 words."
            )
            plain_prompt = (
                f"Project: {GITHUB_REPO}\nFocus: '{topic}'\n"
                f"Files: {', '.join(context_files)}\n\n"
                "Explain this part in plain English. No jargon. 2-3 short paragraphs."
            )
        else:
            tech_prompt = (
                f"Python project: {GITHUB_REPO}\nFile tree:\n{file_tree}\n\n"
                f"Key files:{snippets}\n\n"
                "Technical architecture overview:\n"
                "- Project purpose and main components\n- How modules relate\n"
                "- Key data flows\n- Tech stack and dependencies\n"
                "Bullet points. Max 350 words."
            )
            plain_prompt = (
                f"Project: {GITHUB_REPO}\nFiles: {', '.join(py_files[:20])}\n\n"
                "Explain what this project does and how it's organised. No jargon. 2-3 paragraphs."
            )

        tech_arch  = ask(system="You are a software architect explaining a project's design.", user=tech_prompt, max_tokens=900)
        plain_arch = ask(system="You explain software projects to non-technical people.", user=plain_prompt, max_tokens=400)

        suffix = f" — `{topic}`" if topic else ""
        await interaction.followup.send(embeds=[
            discord.Embed(title=f"🏗️ Architecture{suffix} — Technical",    description=tech_arch[:4000],  color=0x5865F2)
                .set_footer(text=f"{GITHUB_REPO} • {scope_label} • {len(py_files)} Python files"),
            discord.Embed(title=f"💬 Architecture{suffix} — Plain English", description=plain_arch[:4000], color=0x57F287),
        ])