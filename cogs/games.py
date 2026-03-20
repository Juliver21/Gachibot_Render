import discord
from discord import app_commands
from discord.ext import commands
import random
import asyncio
import json
import os
import aiohttp

DATA_FILE = "data/xp.json"

# ── Anthropic API для /roast ──────────────────────────
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")

def load_xp() -> dict:
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}

def save_xp(data: dict):
    os.makedirs("data", exist_ok=True)
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

# ── Слот-машина символи ───────────────────────────────
SLOTS = ["♂️", "💪", "🏛️", "⚔️", "👑", "🔱", "🎰"]
SLOT_WEIGHTS = [30, 25, 20, 15, 7, 2, 1]  # рідкість (%)

SLOT_PAYOUTS = {
    # (символ, кількість): множник виграшу
    ("♂️",  3): 2,
    ("💪",  3): 3,
    ("🏛️", 3): 5,
    ("⚔️",  3): 8,
    ("👑",  3): 15,
    ("🔱",  3): 25,
    ("🎰",  3): 50,
    ("♂️",  2): 0,   # 2 однакових — повернення ставки
    ("💪",  2): 0,
}

# ── Рулетка ───────────────────────────────────────────
ROULETTE_OUTCOMES = [
    {"label": "💀 Провал",      "xp": -100, "weight": 20, "msg": "Аніка відвернувся від тебе..."},
    {"label": "😬 Невдача",     "xp": -50,  "weight": 25, "msg": "Підземелля не прийняло тебе."},
    {"label": "😐 Нічия",       "xp":   0,  "weight": 15, "msg": "Feel nothing... ♂️"},
    {"label": "✅ Дрібний виграш","xp":  30, "weight": 20, "msg": "Непогано, брате!"},
    {"label": "🎉 Виграш",      "xp":  75,  "weight": 12, "msg": "Аніка схвалює! 💪"},
    {"label": "🔥 Великий виграш","xp": 150, "weight":  6, "msg": "ARE YOU READY?! Ти переміг! ♂️"},
    {"label": "👑 ДЖЕКПОТ",     "xp": 500,  "weight":  2, "msg": "FEEL THE POWER! ЛЕГЕНДА КАСКАДУ!"},
]

# ── Активні дуелі ─────────────────────────────────────
pending_duels: dict[int, dict] = {}   # target_id → {challenger, guild_id, xp_bet}

# ── Гра Правда/Брехня (score tracker) ────────────────
_scores: dict[int, dict[int, int]] = {}

QUESTIONS = [
    {"q": "Billy Herrington народився у США",                        "a": True,  "cat": "♂️ Гачі"},
    {"q": "Billy Herrington помер у 2018 році",                      "a": True,  "cat": "♂️ Гачі"},
    {"q": "Gachi-мем виник у Японії",                                "a": True,  "cat": "♂️ Гачі"},
    {"q": "Van Damme — американський актор",                         "a": False, "cat": "♂️ Гачі"},
    {"q": "Billy Herrington відомий як Aniki в японському інтернеті", "a": True,  "cat": "♂️ Гачі"},
    {"q": "CS2 вийшов у 2023 році",                                  "a": True,  "cat": "🎮 Ігри"},
    {"q": "Dota 2 розроблена Riot Games",                            "a": False, "cat": "🎮 Ігри"},
    {"q": "League of Legends — безкоштовна гра",                     "a": True,  "cat": "🎮 Ігри"},
    {"q": "Minecraft офіційно вийшов у 2011 році",                   "a": True,  "cat": "🎮 Ігри"},
    {"q": "PUBG вийшов раніше за Fortnite Battle Royale",            "a": True,  "cat": "🎮 Ігри"},
    {"q": "Warcraft 3 вийшов у 2002 році",                          "a": True,  "cat": "🎮 Ігри"},
    {"q": "Valve розробила Dota 2",                                  "a": True,  "cat": "🎮 Ігри"},
    {"q": "В League of Legends 5 гравців у команді",                 "a": True,  "cat": "🎮 Ігри"},
    {"q": "Fortnite розробила Epic Games",                           "a": True,  "cat": "🎮 Ігри"},
    {"q": "Steam належить Activision",                               "a": False, "cat": "🎮 Ігри"},
]


class TFView(discord.ui.View):
    def __init__(self, question: dict, channel_id: int):
        super().__init__(timeout=30)
        self.question = question
        self.channel_id = channel_id
        self.answered: set[int] = set()

    async def _handle(self, i: discord.Interaction, guess: bool):
        if i.user.id in self.answered:
            return await i.response.send_message("⚠️ Ти вже відповів!", ephemeral=True)
        self.answered.add(i.user.id)
        correct = guess == self.question["a"]
        ch = _scores.setdefault(self.channel_id, {})
        if correct:
            ch[i.user.id] = ch.get(i.user.id, 0) + 1
        ans_str = "✅ Правда" if self.question["a"] else "❌ Брехня"
        text = (f"✅ **Правильно, {i.user.mention}!** +1 очко 🎉\nВідповідь: {ans_str}"
                if correct else
                f"❌ **Неправильно, {i.user.mention}!**\nВідповідь: {ans_str}")
        embed = discord.Embed(description=text, color=0x00C851 if correct else 0xFF4444)
        embed.set_footer(text=f"Категорія: {self.question['cat']}")
        await i.response.send_message(embed=embed)

    @discord.ui.button(label="✅ Правда", style=discord.ButtonStyle.success)
    async def true_btn(self, i: discord.Interaction, _):
        await self._handle(i, True)

    @discord.ui.button(label="❌ Брехня", style=discord.ButtonStyle.danger)
    async def false_btn(self, i: discord.Interaction, _):
        await self._handle(i, False)


class DuelView(discord.ui.View):
    def __init__(self, challenger: discord.Member, target: discord.Member, xp_bet: int):
        super().__init__(timeout=60)
        self.challenger = challenger
        self.target = target
        self.xp_bet = xp_bet

    @discord.ui.button(label="⚔️ Прийняти виклик", style=discord.ButtonStyle.success)
    async def accept(self, i: discord.Interaction, _):
        if i.user.id != self.target.id:
            return await i.response.send_message("❌ Це не твій виклик!", ephemeral=True)

        xp = load_xp()
        c_xp = xp.get(str(self.challenger.id), 0)
        t_xp = xp.get(str(self.target.id), 0)

        if c_xp < self.xp_bet or t_xp < self.xp_bet:
            return await i.response.send_message("❌ У когось недостатньо XP!", ephemeral=True)

        # Бій — кожен кидає кубик
        c_roll = random.randint(1, 100) + min(c_xp // 100, 20)
        t_roll = random.randint(1, 100) + min(t_xp // 100, 20)
        winner = self.challenger if c_roll >= t_roll else self.target
        loser  = self.target if winner == self.challenger else self.challenger

        xp[str(winner.id)] = xp.get(str(winner.id), 0) + self.xp_bet
        xp[str(loser.id)]  = max(0, xp.get(str(loser.id), 0) - self.xp_bet)
        save_xp(xp)

        embed = discord.Embed(title="⚔️ РЕЗУЛЬТАТ ДУЕЛІ ⚔️", color=0xFFD700)
        embed.add_field(name=f"♂️ {self.challenger.display_name}",
                        value=f"Кубик: **{c_roll}**", inline=True)
        embed.add_field(name="VS", value="⚡", inline=True)
        embed.add_field(name=f"♂️ {self.target.display_name}",
                        value=f"Кубик: **{t_roll}**", inline=True)
        embed.add_field(name="🏆 Переможець",
                        value=f"{winner.mention} +**{self.xp_bet}** XP\n"
                              f"{loser.mention} -**{self.xp_bet}** XP", inline=False)
        embed.set_footer(text="♂️ Feel the power of fair combat!")

        for item in self.children:
            item.disabled = True
        await i.response.edit_message(embed=embed, view=self)

    @discord.ui.button(label="❌ Відхилити", style=discord.ButtonStyle.danger)
    async def decline(self, i: discord.Interaction, _):
        if i.user.id != self.target.id:
            return await i.response.send_message("❌ Це не твій виклик!", ephemeral=True)
        embed = discord.Embed(
            description=f"🏳️ {self.target.mention} відхилив виклик. Боягуз! 😤",
            color=0x888888,
        )
        for item in self.children:
            item.disabled = True
        await i.response.edit_message(embed=embed, view=self)


class Games(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    # ── /spin ─────────────────────────────────────────
    @app_commands.command(name="spin", description="🎰 Однорукий бандит — постав XP на удачу!")
    @app_commands.describe(bet="Скільки XP ставиш (мін 10, макс 500)")
    async def spin(self, i: discord.Interaction, bet: int):
        if bet < 10 or bet > 500:
            return await i.response.send_message("❌ Ставка від 10 до 500 XP!", ephemeral=True)

        xp = load_xp()
        uid = str(i.user.id)
        current = xp.get(uid, 0)

        if current < bet:
            return await i.response.send_message(
                f"❌ Недостатньо XP! У тебе **{current}** XP, а ставка **{bet}**.",
                ephemeral=True,
            )

        await i.response.defer()

        # Анімація прокрутки
        spin_msg = await i.followup.send("🎰 **[ ? | ? | ? ]** — крутимо...")
        await asyncio.sleep(0.8)
        await spin_msg.edit(content="🎰 **[ ♂️ | ? | ? ]** — ...")
        await asyncio.sleep(0.6)
        await spin_msg.edit(content="🎰 **[ ♂️ | 💪 | ? ]** — ...")
        await asyncio.sleep(0.5)

        # Фінальний результат
        result = random.choices(SLOTS, weights=SLOT_WEIGHTS, k=3)
        display = f"🎰 **[ {result[0]} | {result[1]} | {result[2]} ]**"

        # Рахуємо виграш
        counts = {s: result.count(s) for s in set(result)}
        max_sym = max(counts, key=counts.get)
        max_cnt = counts[max_sym]

        payout_key = (max_sym, max_cnt)
        multiplier = SLOT_PAYOUTS.get(payout_key, -1)

        if max_cnt == 3:
            won = bet * multiplier
            xp[uid] = current - bet + won
            save_xp(xp)
            color = 0xFFD700
            result_text = (
                f"🎉 **ДЖЕКПОТ! {max_sym}{max_sym}{max_sym}**\n"
                f"Множник: **×{multiplier}** | Виграш: **+{won - bet} XP**\n"
                f"Баланс: **{xp[uid]:,} XP**"
            )
        elif max_cnt == 2 and multiplier == 0:
            # Повернення ставки
            result_text = (
                f"😐 Два однакових — ставка повертається\n"
                f"Баланс: **{current:,} XP** (без змін)"
            )
            color = 0x888888
        else:
            xp[uid] = current - bet
            save_xp(xp)
            color = 0xFF4444
            result_text = (
                f"💸 Програв **{bet} XP**\n"
                f"Баланс: **{xp[uid]:,} XP**"
            )

        embed = discord.Embed(title=display, description=result_text, color=color)
        embed.set_footer(text=f"Ставка: {bet} XP | ♂️ Аніка дивиться")
        await spin_msg.edit(content=None, embed=embed)

    # ── /рулетка ──────────────────────────────────────
    @app_commands.command(name="рулетка", description="🎲 Рулетка долі — виграй або втрать XP!")
    async def roulette(self, i: discord.Interaction):
        await i.response.defer()

        xp = load_xp()
        uid = str(i.user.id)
        current = xp.get(uid, 0)

        # Крутимо рулетку
        spin_msg = await i.followup.send("🎲 Рулетка крутиться... ♂️")
        await asyncio.sleep(1.5)

        weights = [o["weight"] for o in ROULETTE_OUTCOMES]
        outcome = random.choices(ROULETTE_OUTCOMES, weights=weights, k=1)[0]

        new_xp = max(0, current + outcome["xp"])
        xp[uid] = new_xp
        save_xp(xp)

        delta_str = (f"+{outcome['xp']}" if outcome["xp"] >= 0 else str(outcome["xp"]))
        color = (0xFFD700 if outcome["xp"] > 100
                 else 0x00C851 if outcome["xp"] > 0
                 else 0x888888 if outcome["xp"] == 0
                 else 0xFF4444)

        embed = discord.Embed(
            title=f"🎲 {outcome['label']}",
            description=(
                f"*{outcome['msg']}*\n\n"
                f"XP: **{delta_str}**\n"
                f"Баланс: **{new_xp:,} XP**"
            ),
            color=color,
        )
        embed.set_thumbnail(url=i.user.display_avatar.url)
        embed.set_footer(text="♂️ Доля вирішила!")
        await spin_msg.edit(content=None, embed=embed)

    # ── /дуель ────────────────────────────────────────
    @app_commands.command(name="дуель", description="🏆 Виклик на дуель — переможець забирає XP!")
    @app_commands.describe(
        opponent="Кого викликаєш",
        bet="Скільки XP ставиш (мін 50)"
    )
    async def duel(self, i: discord.Interaction, opponent: discord.Member, bet: int = 50):
        if opponent.bot:
            return await i.response.send_message("❌ Боти не дуелюються!", ephemeral=True)
        if opponent.id == i.user.id:
            return await i.response.send_message("❌ Не можна викликати себе!", ephemeral=True)
        if bet < 50:
            return await i.response.send_message("❌ Мінімальна ставка — 50 XP!", ephemeral=True)

        xp = load_xp()
        c_xp = xp.get(str(i.user.id), 0)
        if c_xp < bet:
            return await i.response.send_message(
                f"❌ У тебе лише **{c_xp}** XP, а ставка **{bet}**!", ephemeral=True
            )

        embed = discord.Embed(
            title="⚔️ ВИКЛИК НА ДУЕЛЬ ⚔️",
            description=(
                f"{i.user.mention} викликає {opponent.mention} на бій!\n\n"
                f"💰 Ставка: **{bet} XP** з кожного\n"
                f"🏆 Переможець забирає **{bet * 2} XP**\n\n"
                f"*{opponent.mention}, маєш 60 секунд на відповідь!*"
            ),
            color=0xFF4500,
        )
        view = DuelView(i.user, opponent, bet)
        await i.response.send_message(embed=embed, view=view)

    # ── /roast ────────────────────────────────────────
    @app_commands.command(name="roast", description="🎤 AI генерує гачі-рознос на юзера!")
    @app_commands.describe(member="Кого рознести?")
    async def roast(self, i: discord.Interaction, member: discord.Member):
        if member.id == i.user.id:
            return await i.response.send_message(
                "♂️ Навіщо розносити себе? Це не шлях Аніки!", ephemeral=True
            )

        await i.response.defer()

        if not ANTHROPIC_API_KEY:
            # Фолбек без API — статичні рознощі
            roasts = [
                f"♂️ {member.mention}! Твоя гачі-сила настільки слабка, що навіть Аніка заснув на півслові!",
                f"💪 {member.mention}, ти такий неактивний на сервері, що бот забув про твоє існування!",
                f"🏛️ {member.mention}! Навіть підземелля не хоче тебе приймати — занадто слабкий!",
                f"⚔️ {member.mention}, твій ранг такий низький, що Warcraft 3 соромиться тебе!",
                f"♂️ {member.mention}! Billy Herrington дивиться на тебе і плаче. А він не плакав НІКОЛИ!",
            ]
            roast_text = random.choice(roasts)
            embed = discord.Embed(
                title=f"🎤 Гачі-Рознос: {member.display_name}",
                description=roast_text,
                color=0xFF4500,
            )
            embed.set_thumbnail(url=member.display_avatar.url)
            embed.set_footer(text=f"Від: {i.user.display_name} | ♂️ Feel the roast!")
            return await i.followup.send(embed=embed)

        # З Anthropic API
        prompt = (
            f"Ти — гачі-бот Discord сервера 'Каскадське Братство'. "
            f"Зроби кумедний, але не образливий рознос користувача на ім'я '{member.display_name}'. "
            f"Використовуй гачі-теми: Аніка, підземелля, м'язи, Billy Herrington, 'Are you ready?', ♂️. "
            f"Відповідай ТІЛЬКИ текстом розносу, без пояснень. Максимум 3 речення. Мовою: українська."
        )

        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    "https://api.anthropic.com/v1/messages",
                    headers={
                        "x-api-key": ANTHROPIC_API_KEY,
                        "anthropic-version": "2023-06-01",
                        "content-type": "application/json",
                    },
                    json={
                        "model": "claude-haiku-4-5-20251001",
                        "max_tokens": 200,
                        "messages": [{"role": "user", "content": prompt}],
                    },
                    timeout=aiohttp.ClientTimeout(total=10),
                ) as resp:
                    data = await resp.json()
                    roast_text = data["content"][0]["text"]
        except Exception as e:
            print(f"Roast API error: {e}")
            roast_text = f"♂️ {member.mention}! Навіть AI відмовився тебе розносити — настільки ти безнадійний!"

        embed = discord.Embed(
            title=f"🎤 AI Гачі-Рознос: {member.display_name}",
            description=roast_text,
            color=0xFF4500,
        )
        embed.set_thumbnail(url=member.display_avatar.url)
        embed.set_footer(text=f"Від: {i.user.display_name} | ♂️ Feel the roast!")
        await i.followup.send(embed=embed)

    # ── /gachi_game ───────────────────────────────────
    @app_commands.command(name="gachi_game", description="🎮 Правда чи Брехня — гачі та ігровий мікс!")
    async def gachi_game(self, i: discord.Interaction):
        q = random.choice(QUESTIONS)
        embed = discord.Embed(
            title=f"{q['cat']} | Правда чи Брехня?",
            description=f"**{q['q']}**",
            color=0x8B0000,
        )
        embed.set_footer(text="30 секунд | Відповісти може кожен!")
        await i.response.send_message(embed=embed, view=TFView(q, i.channel_id))

    # ── /game_score ───────────────────────────────────
    @app_commands.command(name="game_score", description="🏅 Рахунок у грі Правда/Брехня")
    async def game_score(self, i: discord.Interaction):
        scores = _scores.get(i.channel_id, {})
        if not scores:
            return await i.response.send_message("Ще немає результатів!", ephemeral=True)
        top = sorted(scores.items(), key=lambda x: x[1], reverse=True)[:10]
        embed = discord.Embed(title="🏅 Рахунок Правда/Брехня", color=0xFFD700)
        medals = ["🥇", "🥈", "🥉"]
        lines = [
            f"{medals[n] if n < 3 else f'**#{n+1}**'} **{(i.guild.get_member(uid) or {'display_name': str(uid)}).display_name}** — {sc} правильних"
            for n, (uid, sc) in enumerate(top)
        ]
        embed.description = "\n".join(lines)
        await i.response.send_message(embed=embed)

    # ── /game_reset ───────────────────────────────────
    @app_commands.command(name="game_reset", description="🔄 Скинути рахунок гри")
    async def game_reset(self, i: discord.Interaction):
        _scores[i.channel_id] = {}
        await i.response.send_message("🔄 Рахунок скинуто!", ephemeral=True)


async def setup(bot: commands.Bot):
    await bot.add_cog(Games(bot))
