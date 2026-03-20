import discord
from discord import app_commands
from discord.ext import commands
import json
import os
import random
import asyncio
from config import RANKS

DATA_FILE = "data/xp.json"

# ── XP Storage ───────────────────────────────────────
def load_xp() -> dict:
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}

def save_xp(data: dict):
    os.makedirs("data", exist_ok=True)
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

def get_rank(xp: int) -> dict:
    current = RANKS[0]
    for r in RANKS:
        if xp >= r["xp"]:
            current = r
    return current

def get_next_rank(xp: int) -> dict | None:
    for r in RANKS:
        if xp < r["xp"]:
            return r
    return None

def xp_bar(xp: int) -> tuple[str, int, int]:
    rank = get_rank(xp)
    next_r = get_next_rank(xp)
    if not next_r:
        return "█" * 10, 0, 0
    progress = xp - rank["xp"]
    needed = next_r["xp"] - rank["xp"]
    filled = int((progress / needed) * 10)
    bar = "█" * filled + "░" * (10 - filled)
    return bar, progress, needed


class Ranking(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.xp: dict = load_xp()

    def _add_xp(self, user_id: int, amount: int) -> tuple[int, bool]:
        uid = str(user_id)
        old_xp = self.xp.get(uid, 0)
        old_rank = get_rank(old_xp)
        self.xp[uid] = old_xp + amount
        save_xp(self.xp)
        return self.xp[uid], get_rank(self.xp[uid])["name"] != old_rank["name"]

    def _rank_embed(self, member: discord.Member, xp: int, rank: dict, level_up: bool = False) -> discord.Embed:
        bar, progress, needed = xp_bar(xp)
        next_r = get_next_rank(xp)

        sorted_users = sorted(self.xp.items(), key=lambda x: x[1], reverse=True)
        position = next((i+1 for i, (uid, _) in enumerate(sorted_users) if uid == str(member.id)), "?")

        rank_index = next((i for i, r in enumerate(RANKS) if r["name"] == rank["name"]), 0)
        color = rank.get("color", 0x8B0000)
        title = "🎉 НОВИЙ РАНГ!" if level_up else f"♂️ Профіль: {member.display_name}"

        embed = discord.Embed(title=title, color=color)
        embed.set_thumbnail(url=member.display_avatar.url)
        embed.add_field(name="🏅 Звання",    value=rank["name"],                    inline=True)
        embed.add_field(name="📊 Рівень",    value=f"**{rank_index + 1}** / {len(RANKS)}", inline=True)
        embed.add_field(name="⚡ XP",        value=f"**{xp:,}**",                   inline=True)
        embed.add_field(name="🏆 Місце",     value=f"**#{position}**",              inline=True)
        embed.add_field(name="💬 Повідомлень", value=f"**{xp // 6}** ~",            inline=True)

        if next_r:
            embed.add_field(
                name=f"До наступного → {next_r['name']}",
                value=f"`{bar}` {progress}/{needed} XP",
                inline=False,
            )
        else:
            embed.add_field(name="Статус", value="🔮 **МАКСИМАЛЬНИЙ РАНГ!** Аніка пишається!", inline=False)

        if level_up:
            embed.description = (
                f"{member.mention} досяг нового звання!\n"
                f"✨ **{rank['name']}**\n\n"
                f"*♂️ Аніка пишається тобою!*"
            )
        return embed

    async def _update_rank_role(self, member: discord.Member, rank: dict):
        rank_role_names = {r["role"] for r in RANKS}
        to_remove = [r for r in member.roles if r.name in rank_role_names]
        try:
            if to_remove:
                await member.remove_roles(*to_remove, reason="Оновлення рангу")
            role = discord.utils.get(member.guild.roles, name=rank["role"])
            if role:
                await member.add_roles(role, reason=f"Новий ранг: {rank['name']}")
        except discord.Forbidden:
            pass

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.bot or not message.guild:
            return
        new_xp, leveled_up = self._add_xp(message.author.id, random.randint(3, 10))

        if leveled_up:
            rank = get_rank(new_xp)
            embed = self._rank_embed(message.author, new_xp, rank, level_up=True)
            await message.channel.send(embed=embed)
            await self._update_rank_role(message.author, rank)

    # ── /ranking ─────────────────────────────────────
    @app_commands.command(name="ranking", description="🏆 Переглянути свій ранг і XP")
    @app_commands.describe(member="Учасник (за замовчуванням — ти)")
    async def ranking(self, i: discord.Interaction, member: discord.Member = None):
        member = member or i.user
        xp = self.xp.get(str(member.id), 0)
        rank = get_rank(xp)
        embed = self._rank_embed(member, xp, rank)
        await i.response.send_message(embed=embed)

    # ── /top ─────────────────────────────────────────
    @app_commands.command(name="top", description="🏆 Топ-15 найактивніших братів")
    async def top(self, i: discord.Interaction):
        if not self.xp:
            return await i.response.send_message("Ще немає даних!", ephemeral=True)

        top15 = sorted(self.xp.items(), key=lambda x: x[1], reverse=True)[:15]
        embed = discord.Embed(title="🏆 Топ Братів Каскаду", color=0xFFD700)

        medals = ["🥇", "🥈", "🥉"]
        lines = []
        for idx, (uid, xp) in enumerate(top15):
            m = i.guild.get_member(int(uid))
            name = m.display_name if m else f"<ID:{uid}>"
            rank = get_rank(xp)
            medal = medals[idx] if idx < 3 else f"**#{idx+1}**"
            lines.append(f"{medal} **{name}**\n└ {rank['name']} · `{xp:,} XP`")

        embed.description = "\n".join(lines)
        embed.set_footer(text="XP нараховується за кожне повідомлення 💪")
        await i.response.send_message(embed=embed)

    # ── /ranks ────────────────────────────────────────
    @app_commands.command(name="ranks", description="📋 Список всіх рангів і вимоги XP")
    async def ranks_list(self, i: discord.Interaction):
        embed = discord.Embed(
            title="📋 Всі ранги Каскадського Братства",
            color=0x8B0000,
        )
        lines = []
        for idx, r in enumerate(RANKS):
            next_xp = RANKS[idx+1]["xp"] if idx+1 < len(RANKS) else "MAX"
            lines.append(f"`{idx+1:02d}.` {r['name']} — від **{r['xp']:,} XP**")
        embed.description = "\n".join(lines)
        embed.set_footer(text="Пиши повідомлення — отримуй XP автоматично!")
        await i.response.send_message(embed=embed)

    # ── /scan_server ──────────────────────────────────
    @app_commands.command(name="scan_server", description="🔍 Сканувати всі повідомлення і нарахувати XP (тільки адмін)")
    async def scan_server(self, i: discord.Interaction):
        # Перевірка прав
        if not i.user.guild_permissions.administrator:
            return await i.response.send_message("❌ Тільки для адміністраторів!", ephemeral=True)

        await i.response.defer(ephemeral=True)
        await i.followup.send("🔍 Починаю сканування сервера... Це може зайняти кілька хвилин.")

        guild = i.guild
        user_msg_count: dict[int, int] = {}
        scanned_channels = 0
        total_messages = 0

        for channel in guild.text_channels:
            # Перевіряємо чи бот може читати канал
            if not channel.permissions_for(guild.me).read_message_history:
                continue
            try:
                async for message in channel.history(limit=10000):
                    if message.author.bot:
                        continue
                    uid = message.author.id
                    user_msg_count[uid] = user_msg_count.get(uid, 0) + 1
                    total_messages += 1
                scanned_channels += 1
            except Exception as e:
                print(f"Scan error in {channel.name}: {e}")

        # Нараховуємо XP — 6 XP за кожне повідомлення
        updated = 0
        for uid, count in user_msg_count.items():
            earned_xp = count * 6
            uid_str = str(uid)
            current_xp = self.xp.get(uid_str, 0)
            # Якщо у юзера вже є більше XP — не перезаписуємо
            if earned_xp > current_xp:
                self.xp[uid_str] = earned_xp
                updated += 1

        save_xp(self.xp)

        # Видаємо ролі всім
        roles_given = 0
        for uid_str, xp in self.xp.items():
            member = guild.get_member(int(uid_str))
            if member:
                rank = get_rank(xp)
                await self._update_rank_role(member, rank)
                roles_given += 1
                await asyncio.sleep(0.3)  # Щоб не флудити Discord API

        embed = discord.Embed(
            title="✅ Сканування завершено!",
            color=0x00C851,
        )
        embed.add_field(name="📢 Каналів проскановано", value=str(scanned_channels), inline=True)
        embed.add_field(name="💬 Повідомлень знайдено", value=f"{total_messages:,}", inline=True)
        embed.add_field(name="👥 Користувачів оновлено", value=str(updated), inline=True)
        embed.add_field(name="🏅 Ролей видано", value=str(roles_given), inline=True)
        embed.set_footer(text="Ранги видані всім учасникам на основі активності!")
        await i.followup.send(embed=embed)


async def setup(bot: commands.Bot):
    await bot.add_cog(Ranking(bot))
