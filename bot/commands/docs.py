"""
commands/docs.py
----------------
/docs_init              — one-time setup, creates docs/chapters/ in GitHub
/docs                   — latest commit → which chapters need updating
/docs count:<n>         — last N commits documentation guide
/docs chapter:<n>       — deep dive into a specific chapter (1-7)
/docs mode:status       — progress tracker across all chapters
"""

import re
import discord
from discord import app_commands
from datetime import datetime, timezone

from core.github  import get_file, get_repo_tree, push_file, get_changelog_entries
from core.copilot import ask
from core.config  import GITHUB_REPO, FYP_PROJECT_DESCRIPTION, DOCUMENTER_DISCORD_ID
from docs.chapters import CHAPTERS, chapter_filepath, map_files_to_chapters, build_chapter_file


# ── Helpers ───────────────────────────────────────────────────────────────────
def get_chapter_file(ch_num: int) -> str | None:
    return get_file(chapter_filepath(ch_num))


EMBED_COLORS = [0x5865F2, 0x57F287, 0xFEE75C, 0xEB459E, 0xED4245, 0x3BA55C, 0xFAA61A]


def setup(tree: app_commands.CommandTree):

    # ── /docs_init ────────────────────────────────────────────────────────────
    @tree.command(
        name="docs_init",
        description="One-time setup: scans full repo and creates docs/chapters/ files in GitHub"
    )
    async def docs_init(interaction: discord.Interaction):
        await interaction.response.defer(thinking=True)
        await interaction.followup.send(
            "🔍 Scanning repo and generating documentation brain...\n"
            "This takes ~1 minute. I'll post each chapter as it's created."
        )

        py_files  = get_repo_tree()
        file_tree = "\n".join(py_files[:60])

        snippets = ""
        for fname in [f for f in py_files if "/" not in f][:5]:
            content = get_file(fname) or ""
            snippets += f"\n\n### {fname}\n```python\n{content[:800]}\n```"

        created = []
        for ch_num, ch in CHAPTERS.items():
            guidance = ask(
                system=(
                    "You are an academic writing assistant for a Final Year Project (FYP) report "
                    "in IEEE/ACM format. Project: " + FYP_PROJECT_DESCRIPTION +
                    " Be specific, detailed, and practical. Use markdown."
                ),
                user=(
                    f"Generate a documentation guide for Chapter {ch_num}: {ch['title']}\n"
                    f"Chapter covers: {ch['description']}\n\n"
                    f"Project file structure:\n{file_tree}\n\n"
                    f"Key source files:\n{snippets}\n\n"
                    "Provide:\n"
                    "1. What this chapter should cover for THIS specific project\n"
                    "2. 6-8 section headings the documenter should write\n"
                    "3. For each section: 2-3 bullet points of what to include\n"
                    "4. 5-7 specific Google/Google Scholar search topics\n"
                    "5. Suggested diagrams/tools to include\n"
                    "Format in clean markdown."
                ),
                max_tokens=1000,
            )

            filepath = chapter_filepath(ch_num)
            success  = push_file(
                filepath,
                build_chapter_file(ch_num, guidance),
                f"docs: init chapter {ch_num} - {ch['title']} [skip ci]",
            )
            created.append(f"{'✅' if success else '❌'} `{filepath}`")

            await interaction.channel.send(embed=discord.Embed(
                title=f"📖 Chapter {ch_num}: {ch['title']} {'created' if success else 'FAILED'}",
                description="**Topics to cover:**\n" + "\n".join([f"• ⬜ {t}" for t in ch["topics"]]),
                color=0x57F287 if success else 0xED4245,
            ))

        await interaction.channel.send(embed=discord.Embed(
            title="✅ Documentation Brain Initialized!",
            description=(
                "Created under `docs/chapters/`:\n\n" + "\n".join(created) +
                "\n\n**Next steps:**\n"
                "1. Open each file in GitHub\n"
                "2. Use the Topic Status Tracker (⬜ = pending, ✅ = done)\n"
                "3. Search topics on Google Scholar\n"
                "4. Run `/docs` after every commit for update guidance"
            ),
            color=0xEB459E,
        ).set_footer(text=f"{GITHUB_REPO} • docs/chapters/"))

    # ── /docs ─────────────────────────────────────────────────────────────────
    @tree.command(
        name="docs",
        description="Documentation guide. Options: mode:status | count:3 | chapter:4"
    )
    @app_commands.describe(
        mode="Use 'status' to see all pending topics",
        count="Analyze last N commits (e.g. 3)",
        chapter="Focus on a specific chapter number 1-7",
    )
    async def docs(
        interaction: discord.Interaction,
        mode: str = None,
        count: int = None,
        chapter: int = None,
    ):
        await interaction.response.defer(thinking=True)

        # ── /docs mode:status ─────────────────────────────────────────────────
        if mode and mode.lower() == "status":
            embeds = []
            for ch_num, ch in CHAPTERS.items():
                content = get_chapter_file(ch_num)
                if not content:
                    continue
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
                await interaction.followup.send("❌ No chapter files found. Run `/docs_init` first!")
                return

            await interaction.followup.send(embed=discord.Embed(
                title="📊 Documentation Status — All Chapters",
                description=f"FYP Report progress across {len(embeds)} chapters",
                color=0xEB459E,
            ))
            for e in embeds:
                await interaction.channel.send(embed=e)
            return

        # ── /docs chapter:<n> ─────────────────────────────────────────────────
        if chapter:
            if chapter not in CHAPTERS:
                await interaction.followup.send("❌ Chapter must be between 1 and 7.")
                return

            ch       = CHAPTERS[chapter]
            py_files = get_repo_tree()
            relevant = [f for f in py_files if any(kw.lower() in f.lower() for kw in ch["keywords"])][:8]

            snippets = ""
            for fname in relevant[:3]:
                content = get_file(fname) or ""
                snippets += f"\n### {fname}\n```python\n{content[:600]}\n```"

            deep_guide = ask(
                system="You are an expert academic writing coach for IEEE/ACM FYP reports. Project: " + FYP_PROJECT_DESCRIPTION,
                user=(
                    f"Deep writing guide for Chapter {chapter}: {ch['title']}\n"
                    f"Purpose: {ch['description']}\n"
                    f"Relevant files: {', '.join(relevant)}\n"
                    f"File snippets:{snippets}\n\n"
                    "Provide:\n"
                    "1. Exact numbered section headings\n"
                    "2. What to write in each section (3-4 points)\n"
                    "3. Diagrams or tables to include\n"
                    "4. 6 precise Google Scholar search queries\n"
                    "5. Common mistakes to avoid\n"
                    "6. Example paragraph opener\n"
                    "Specific to the AI DevOps platform project."
                ),
                max_tokens=1000,
            )

            await interaction.followup.send(embed=discord.Embed(
                title=f"📖 Deep Guide — Chapter {chapter}: {ch['title']}",
                description=deep_guide[:4000],
                color=0x5865F2,
            ).set_footer(text="Run /docs mode:status to see overall progress"))
            return

        # ── /docs [count:<n>] — latest commit(s) guide ────────────────────────
        n       = count if count else 1
        entries = get_changelog_entries(n)
        if not entries:
            await interaction.followup.send("❌ No commits in CHANGELOG.md yet. Push a commit first!")
            return

        combined = "\n\n".join(entries)

        # Extract changed files from changelog text
        changed_files = []
        for line in combined.splitlines():
            for word in line.split():
                cleaned = word.strip("*`-•(),:")
                if ("/" in cleaned or cleaned.endswith(".py")) and 2 < len(cleaned) < 80:
                    changed_files.append(cleaned)
        if not changed_files:
            changed_files = get_repo_tree()[:15]

        chapter_mapping = map_files_to_chapters(list(set(changed_files)))
        if not chapter_mapping:
            await interaction.followup.send("ℹ️ Could not map changes to chapters. Try `/docs_init` first.")
            return

        label        = f"last {n} commits" if n > 1 else "latest commit"
        chapters_str = "\n".join([
            f"• **Chapter {cn}: {CHAPTERS[cn]['title']}** — {len(files)} file{'s' if len(files)>1 else ''} changed"
            for cn, files in chapter_mapping.items()
        ])
        mention = f"<@{DOCUMENTER_DISCORD_ID}>" if DOCUMENTER_DISCORD_ID else "📝 **Documenter**"

        await interaction.followup.send(embed=discord.Embed(
            title=f"📚 Documentation Update — {label}",
            description=f"Chapters needing attention:\n\n{chapters_str}\n\n{mention} — please update these sections 👇",
            color=0xEB459E,
        ))

        for i, (ch_num, files) in enumerate(chapter_mapping.items()):
            ch = CHAPTERS[ch_num]
            guidance = ask(
                system=(
                    "You are an academic writing assistant for an IEEE/ACM FYP report. "
                    "Project: " + FYP_PROJECT_DESCRIPTION + " Be specific. Use bullet points."
                ),
                user=(
                    f"Chapter {ch_num}: {ch['title']}\n"
                    f"Changed files: {', '.join(files)}\n\n"
                    f"Commit context:\n{combined[:600]}\n\n"
                    "Tell the documenter:\n"
                    "1. What to ADD or UPDATE in this chapter (3 specific points)\n"
                    "2. Which section to update\n"
                    "3. 3-4 Google Scholar search topics\n"
                    "4. One suggested opening sentence\n"
                    "Specific to the AI DevOps platform."
                ),
                max_tokens=500,
            )

            # Append to chapter log file in GitHub
            existing = get_chapter_file(ch_num)
            if existing:
                now       = datetime.now(timezone.utc).strftime("%Y-%m-%d")
                sha_short = entries[0].split("]")[0].replace("## [", "").strip() if entries else "unknown"
                log_row   = f"| {now} | {sha_short} | {', '.join(files[:2])} | See Discord for guidance |\n"
                updated   = existing + log_row
                push_file(chapter_filepath(ch_num), updated, f"docs: update ch{ch_num} log [skip ci]")

            await interaction.channel.send(embed=
                discord.Embed(
                    title=f"📖 Chapter {ch_num}: {ch['title']}",
                    color=EMBED_COLORS[i % len(EMBED_COLORS)],
                )
                .add_field(name="📁 Changed files", value=" ".join([f"`{f}`" for f in files[:5]]), inline=False)
                .add_field(name="✍️ What to write / update", value=guidance[:900], inline=False)
                .set_footer(text=f"See docs/chapters/chapter_0{ch_num}_*.md in your repo")
            )