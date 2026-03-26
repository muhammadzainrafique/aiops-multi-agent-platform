"""
commands/summary.py
-------------------
/summary — shows the latest commit summary from CHANGELOG.md
"""

import discord
from discord import app_commands
from core.github import get_changelog_entries
from core.config import GITHUB_REPO


def setup(tree: app_commands.CommandTree):

    @tree.command(name="summary", description="Show a recap of the latest commit")
    async def summary(interaction: discord.Interaction):
        await interaction.response.defer(thinking=True)

        entries = get_changelog_entries(1)
        if not entries:
            await interaction.followup.send(
                "❌ No CHANGELOG.md found yet. Push a commit first and the agent will create it!"
            )
            return

        await interaction.followup.send(embed=
            discord.Embed(
                title="📋 Latest Commit Summary",
                description=entries[0][:4000],
                color=0xFEE75C,
            ).set_footer(text=f"From CHANGELOG.md • {GITHUB_REPO}")
        )