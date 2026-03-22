import discord
from discord.ext import commands
import asyncio
import os
import sys
from dotenv import load_dotenv
load_dotenv()
from keep_alive import keep_alive


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

    token = os.getenv("TOKEN")
    if not token:
        print("❌ TOKEN не знайдено! Додай у Environment Variables.")
        sys.exit(1)

    try:
        await bot.start(token)
    except discord.LoginFailure:
        print("❌ Невірний TOKEN!")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Bot error: {e}")
        raise


# Глобальний обробник незловлених помилок aiohttp
import aiohttp
_orig_connector = aiohttp.TCPConnector.__del__ if hasattr(aiohttp.TCPConnector, '__del__') else None


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("⏹ Зупинено вручну")
    except Exception as e:
        print(f"❌ Fatal error: {e}")
        sys.exit(1)
