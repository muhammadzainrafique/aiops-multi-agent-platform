"""
commands/explain.py
-------------------
/explain <filename> — explains what a file does (technical + plain English)
"""

import discord
from discord import app_commands
from core.github  import get_file
from core.copilot import ask
from core.config  import GITHUB_REPO, GITHUB_BRANCH


def setup(tree: app_commands.CommandTree):

    @tree.command(name="explain", description="Explain what a specific file in the project does")
    @app_commands.describe(filename="e.g. agents/supervisor/main.py")
    async def explain(interaction: discord.Interaction, filename: str):
        await interaction.response.defer(thinking=True)

        code = get_file(filename)
        if not code:
            await interaction.followup.send(
                f"❌ Could not find `{filename}` in `{GITHUB_REPO}` ({GITHUB_BRANCH} branch).\n"
                "Make sure the path is correct, e.g. `agents/supervisor/main.py`"
            )
            return

        if len(code) > 8000:
            code = code[:8000] + "\n\n# ... (file truncated)"

        tech = ask(
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

        plain = ask(
            system="You explain code files to non-technical people in plain, friendly language.",
            user=(
                f"File: {filename}\n\n```python\n{code}\n```\n\n"
                "Explain what this file does in plain English. "
                "No jargon, no code. 2-3 short paragraphs max."
            ),
            max_tokens=400,
        )

        await interaction.followup.send(embeds=[
            discord.Embed(title=f"🔧 `{filename}` — Technical", description=tech[:4000], color=0x5865F2),
            discord.Embed(title=f"💬 `{filename}` — Plain English", description=plain[:4000], color=0x57F287),
        ])