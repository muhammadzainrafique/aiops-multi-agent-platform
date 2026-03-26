"""
commands/help_cmd.py
--------------------
/help — lists all available bot commands
"""

import discord
from discord import app_commands


def setup(tree: app_commands.CommandTree):

    @tree.command(name="help", description="List all FYP Agent bot commands")
    async def help_cmd(interaction: discord.Interaction):
        await interaction.response.send_message(embed=discord.Embed(
            title="🤖 FYP Agent — All Commands",
            color=0x5865F2,
            description=(
                "**`/explain <filename>`**\n"
                "→ Explains a file — technical + plain English\n"
                "→ Example: `/explain agents/supervisor/main.py`\n\n"

                "**`/architecture [topic]`**\n"
                "→ Full project overview, or focus on a folder/topic\n"
                "→ Example: `/architecture agents/` or `/architecture database layer`\n\n"

                "**`/summary`**\n"
                "→ Latest commit recap from CHANGELOG\n\n"

                "**`/commit [count]`**\n"
                "→ Recent commit history\n"
                "→ Example: `/commit 3` for last 3 commits\n\n"

                "**`/docs_init`**\n"
                "→ One-time setup — creates all 7 chapter guide files in GitHub\n\n"

                "**`/docs`**\n"
                "→ After latest commit — which chapters need updating and what to write\n\n"

                "**`/docs count:3`**\n"
                "→ Documentation guide for last 3 commits combined\n\n"

                "**`/docs chapter:4`**\n"
                "→ Deep writing guide for a specific chapter (1-7)\n\n"

                "**`/docs mode:status`**\n"
                "→ Progress tracker — pending vs done topics across all chapters\n\n"

                "**`/help`**\n"
                "→ You're looking at it 😄"
            ),
        ))