"""
commands/commit.py
------------------
/commit [count] — show info about recent commits from CHANGELOG.md
"""

import discord
from discord import app_commands
from core.github import get_changelog_entries
from core.config import GITHUB_REPO


def setup(tree: app_commands.CommandTree):

    @tree.command(name="commit", description="Show recent commits. Optionally specify how many (e.g. 3)")
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
        await interaction.followup.send(embed=
            discord.Embed(
                title=f"📋 Commit History — {label} commit{'s' if not count or count > 1 else ''}",
                description=f"Found **{len(entries)}** entr{'y' if len(entries) == 1 else 'ies'} in CHANGELOG.md",
                color=0xFEE75C,
            ).set_footer(text=GITHUB_REPO)
        )

        # Send in batches of 5 (Discord embed limit per message)
        batch = []
        for i, entry in enumerate(entries):
            lines = entry.strip().splitlines()
            title = lines[0].replace("## ", "").strip() if lines else f"Commit #{i+1}"
            body  = "\n".join(lines[1:]).strip()[:1000]
            batch.append(discord.Embed(
                title=f"🔖 {title}",
                description=body or "_No details recorded._",
                color=0x5865F2 if i % 2 == 0 else 0x57F287,
            ))
            if len(batch) == 5:
                await interaction.channel.send(embeds=batch)
                batch = []

        if batch:
            await interaction.channel.send(embeds=batch)