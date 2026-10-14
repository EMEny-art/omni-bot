import os
import discord
from discord.ext import commands
from dotenv import load_dotenv

load_dotenv()

TOKEN = os.getenv("DISCORD_TOKEN")

if not TOKEN:
    print("ERRORE: DISCORD_TOKEN non trovato! Mettilo nei Secrets di Fly.io")
    exit(1)

intents = discord.Intents.default()
intents.message_content = True
intents.members = True

bot = commands.Bot(command_prefix="!", intents=intents)

@bot.event
async def on_ready():
    print(f"✅ Bot connesso come {bot.user}")
    print(f"Bot online su {len(bot.guilds)} server!")

# ---- INSERISCI QUI I TUOI COMANDI ----
# Esempio:
@bot.command()
async def ping(ctx):
    await ctx.send(f"Pong! {round(bot.latency * 1000)}ms")

# -------------------------------

bot.run(TOKEN)
