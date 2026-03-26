"""
FYP Agent Discord Bot
---------------------
Entry point — run this file to start the bot.
  python main.py
"""

import os
import discord
from discord.ext import commands
from dotenv import load_dotenv

load_dotenv()

# ── Bot setup ─────────────────────────────────────────────────────────────────
intents = discord.Intents.default()
bot = commands.Bot(command_prefix="!", intents=intents)
tree = bot.tree


@bot.event
async def on_ready():
    try:
        synced = await tree.sync()
        print(f"✅ Synced {len(synced)} commands: {[c.name for c in synced]}")
    except Exception as e:
        print(f"❌ Sync failed: {e}")
    print(f"✅ FYP Bot online as {bot.user}")


# ── Register all command modules ──────────────────────────────────────────────
from commands.explain      import setup as setup_explain
from commands.architecture import setup as setup_architecture
from commands.summary      import setup as setup_summary
from commands.commit       import setup as setup_commit
from commands.docs         import setup as setup_docs
from commands.help_cmd     import setup as setup_help

setup_explain(tree)
setup_architecture(tree)
setup_summary(tree)
setup_commit(tree)
setup_docs(tree)
setup_help(tree)

# ── Run ───────────────────────────────────────────────────────────────────────
bot.run(os.environ["DISCORD_BOT_TOKEN"])