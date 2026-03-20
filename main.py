import discord
from discord.ext import commands
import asyncio
import os
from dotenv import load_dotenv
from keep_alive import keep_alive

load_dotenv()

async def main():
    intents = discord.Intents.all()
    bot = commands.Bot(command_prefix="!", intents=intents)

    @bot.event
    async def on_ready():
        try:
            synced = await bot.tree.sync()
            print(f"✅ Синхронізовано {len(synced)} slash команд")
        except Exception as e:
            print(f"❌ Помилка синхронізації: {e}")
        print(f"✅ {bot.user} онлайн! ♂️")

    for cog in ["cogs.music", "cogs.ranking", "cogs.games", "cogs.events"]:
        try:
            await bot.load_extension(cog)
            print(f"✅ {cog} завантажено")
        except Exception as e:
            print(f"❌ {cog} помилка: {e}")

    keep_alive()
    await bot.start(os.getenv("TOKEN"))

asyncio.run(main())
