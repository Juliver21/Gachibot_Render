import discord
from discord import app_commands
from discord.ext import commands
from discord.ext import tasks
import asyncio
import random
import json
import os
from datetime import datetime, timedelta, timezone

from config import (
    EMOJI_ROLE_MAP, ROLE_MESSAGE_ID, MAFIA_EMOJI_ID, MAFIA_ROLE_ID,
    WELCOME_CHANNEL_NAME, MEME_TRIGGERS,
    VOICE_COMPLIMENTS, CHANNEL_GREETINGS,
    CASCADE_TEST, GACHI_REMIX_URLS, ROOM_SOUNDS,
)

GACHI_QUOTES = [
    "Give me your strongest potions, potion seller. 💪",
    "He's a jolly good fellow! ♂️",
    "Are you ready? 😏",
    "Break your limits, Aniki! ♂️",
    "Will you join us? The Dungeon awaits... 🏛️",
    "You look like you work out. 👀",
    "Feel the power! ✨♂️",
    "Unbelievable... simply unbelievable. 💪",
]

# ── Персистентні дані ─────────────────────────────────
TEST_DATA_FILE = "data/test_attempts.json"

def load_test_data() -> dict:
    if os.path.exists(TEST_DATA_FILE):
        with open(TEST_DATA_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}

def save_test_data(data: dict):
    os.makedirs("data", exist_ok=True)
    with open(TEST_DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

# ── Стан ─────────────────────────────────────────────
solo_guilds:    set[int] = set()
solo_kicked:    dict[int, set[int]] = {}
test_sessions:  dict[int, dict] = {}      # user_id → {score, q_idx}
test_data:      dict = load_test_data()   # user_id → last_attempt ISO date


def can_take_test(user_id: int) -> tuple[bool, str]:
    """Перевіряє чи може юзер проходити тест (1 спроба на день)"""
    uid = str(user_id)
    if uid not in test_data:
        return True, ""
    last = datetime.fromisoformat(test_data[uid]["last_attempt"])
    now = datetime.now(timezone.utc)
    diff = now - last
    if diff.total_seconds() < 86400:
        remaining = timedelta(seconds=86400) - diff
        hours = int(remaining.total_seconds() // 3600)
        minutes = int((remaining.total_seconds() % 3600) // 60)
        return False, f"{hours}г {minutes}хв"
    return True, ""

def record_attempt(user_id: int):
    uid = str(user_id)
    test_data[uid] = {"last_attempt": datetime.now(timezone.utc).isoformat()}
    save_test_data(test_data)


# ── Каскадський тест — View ───────────────────────────
class CascadeView(discord.ui.View):
    def __init__(self, user_id: int, q_idx: int, bot: commands.Bot, guild_id: int):
        super().__init__(timeout=180)
        self.user_id = user_id
        self.q_idx = q_idx
        self.bot = bot
        self.guild_id = guild_id
        self._build_buttons()

    def _build_buttons(self):
        self.clear_items()
        q = CASCADE_TEST[self.q_idx]
        for opt in q["options"]:
            letter = opt[0]
            style = discord.ButtonStyle.secondary
            btn = discord.ui.Button(label=opt, style=style, custom_id=f"cascade_{letter}")
            btn.callback = self._make_cb(letter)
            self.add_item(btn)

    def _make_cb(self, letter: str):
        async def cb(interaction: discord.Interaction):
            if interaction.user.id != self.user_id:
                return await interaction.response.send_message("❌ Це не твій тест!", ephemeral=True)

            # Дезактивуємо кнопки
            for item in self.children:
                item.disabled = True
            await interaction.response.edit_message(view=self)

            state = test_sessions.get(self.user_id, {"score": 0})
            q = CASCADE_TEST[self.q_idx]
            correct = letter == q["answer"]

            if correct:
                state["score"] = state.get("score", 0) + 1
                fb = f"✅ **Правильно!** {q['explanation']}"
                color = 0x00C851
            else:
                fb = f"❌ **Неправильно.** {q['explanation']}\nПравильна відповідь: **{q['answer']}**"
                color = 0xFF4444
            test_sessions[self.user_id] = state

            await interaction.followup.send(
                embed=discord.Embed(description=fb, color=color)
            )

            next_idx = self.q_idx + 1
            await asyncio.sleep(1)

            if next_idx >= len(CASCADE_TEST):
                # ── Кінець тесту ──
                score = state["score"]
                total = len(CASCADE_TEST)
                passed = score >= round(total * 0.6)

                result_embed = discord.Embed(
                    title="✅ Тест пройдено!" if passed else "❌ Тест не пройдено",
                    description=(
                        f"Результат: **{score}/{total}** правильних відповідей\n\n"
                        + (
                            "🎉 Вітаємо! Ти прийнятий до **Каскадської Мафії**!\n*Аніка схвалює тебе!* ♂️💼"
                            if passed else
                            f"Спробуй ще раз завтра! Потрібно мінімум **{round(total*0.6)}/{total}**."
                        )
                    ),
                    color=0x00C851 if passed else 0xFF4444,
                )
                await interaction.followup.send(embed=result_embed)

                if passed:
                    guild = self.bot.get_guild(self.guild_id)
                    if guild:
                        member = guild.get_member(self.user_id)
                        role = discord.utils.get(guild.roles, id=MAFIA_ROLE_ID)
                        if role and member:
                            try:
                                await member.add_roles(role, reason="Пройшов Каскадський тест ✅")
                                # Повідомлення в загальному каналі
                                ch = discord.utils.get(guild.text_channels, name=WELCOME_CHANNEL_NAME)
                                if ch:
                                    await ch.send(
                                        f"🕶️ {member.mention} пройшов Каскадський тест і вступив до "
                                        f"**Каскадської Мафії**! Вітаємо, Брате! ♂️"
                                    )
                            except Exception as e:
                                print(f"Role error: {e}")

                test_sessions.pop(self.user_id, None)
            else:
                # ── Наступне питання ──
                nq = CASCADE_TEST[next_idx]
                embed = discord.Embed(
                    title=f"📜 Питання {next_idx+1}/{len(CASCADE_TEST)}",
                    description=f"**{nq['q']}**",
                    color=0x8B0000,
                )
                embed.set_footer(text="Обери правильну відповідь")
                view = CascadeView(self.user_id, next_idx, self.bot, self.guild_id)
                await interaction.followup.send(embed=embed, view=view)

        return cb


# ── Events Cog ───────────────────────────────────────
class Events(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self._compliment_task.start()
        self._greeting_task.start()

    def cog_unload(self):
        self._compliment_task.cancel()
        self._greeting_task.cancel()

    # ── Фонові задачі ─────────────────────────────────

    @tasks.loop(minutes=90)
    async def _compliment_task(self):
        """Заходить у VC, грає MP3-комплімент, пінгує юзера в тексті"""
        for guild in self.bot.guilds:
            if guild.voice_client:
                continue
            channels_with_humans = [
                c for c in guild.voice_channels
                if any(not m.bot for m in c.members)
            ]
            if not channels_with_humans:
                continue
            vc_ch = random.choice(channels_with_humans)
            txt_ch = (
                discord.utils.get(guild.text_channels, name="загальний")
                or (guild.text_channels[0] if guild.text_channels else None)
            )
            if not txt_ch:
                continue
            compliment_dir = "sounds/compliments"
            mp3_files = []
            if os.path.isdir(compliment_dir):
                mp3_files = [
                    os.path.join(compliment_dir, f)
                    for f in os.listdir(compliment_dir)
                    if f.endswith(".mp3")
                ]
            try:
                vc = await vc_ch.connect()
                humans = [m for m in vc_ch.members if not m.bot]
                target = random.choice(humans) if humans else None
                mention = target.mention if target else "брати"
                if mp3_files:
                    sound = random.choice(mp3_files)
                    sound_name = os.path.splitext(os.path.basename(sound))[0]
                    vc.play(discord.FFmpegPCMAudio(sound))
                    await txt_ch.send(f"♂️ {mention} — *{sound_name}* 🎙️")
                    while vc.is_playing():
                        await asyncio.sleep(1)
                else:
                    await txt_ch.send(f"♂️ {mention} — {random.choice(VOICE_COMPLIMENTS)}")
                    await asyncio.sleep(3)
                await asyncio.sleep(1)
                await vc.disconnect()
            except Exception as e:
                print(f"Compliment task error: {e}")

    @_compliment_task.before_loop
    async def _before_compliment(self):
        await self.bot.wait_until_ready()
        await asyncio.sleep(random.randint(3600, 7200))

    @tasks.loop(hours=3)
    async def _greeting_task(self):
        for guild in self.bot.guilds:
            writeable = [
                c for c in guild.text_channels
                if c.permissions_for(guild.me).send_messages
                and c.name not in ("bot-log", "logs", "audit")
            ]
            if writeable:
                ch = random.choice(writeable)
                try:
                    await ch.send(random.choice(CHANNEL_GREETINGS))
                except Exception:
                    pass

    @_greeting_task.before_loop
    async def _before_greeting(self):
        await self.bot.wait_until_ready()
        await asyncio.sleep(random.randint(7200, 14400))

    # ── Listeners ─────────────────────────────────────

    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        ch = (
            discord.utils.get(member.guild.text_channels, name=WELCOME_CHANNEL_NAME)
            or member.guild.system_channel
        )
        if ch:
            embed = discord.Embed(
                title="♂️ Новий Брат Прибув! ♂️",
                description=(
                    f"Вітаємо, {member.mention}!\n\n"
                    f"*\"{random.choice(GACHI_QUOTES)}\"*\n\n"
                    "Ознайомся з правилами та обери ігрову роль в каналі ролей! 💪"
                ),
                color=0x8B0000,
            )
            embed.set_thumbnail(url=member.display_avatar.url)
            embed.set_footer(text="Каскадське Братство | Welcome ♂️")
            await ch.send(embed=embed)

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.bot or not message.guild:
            return
        content = message.content.lower()
        for trigger, meme_url in MEME_TRIGGERS.items():
            if trigger in content:
                embed = discord.Embed(color=0xFF4500)
                embed.set_image(url=meme_url)
                embed.set_footer(text=f"♂️ тригер: {trigger}")
                await message.channel.send(embed=embed)
                break

    @commands.Cog.listener()
    async def on_voice_state_update(self, member: discord.Member, before, after):
        guild = member.guild
        gid = guild.id

        # ── Звуки при вході в ігровий канал ──────────
        if (
            not member.bot
            and after.channel
            and after.channel.name in ROOM_SOUNDS
            and not guild.voice_client
        ):
            humans = [m for m in after.channel.members if not m.bot]
            if len(humans) == 1:
                sound = ROOM_SOUNDS[after.channel.name]
                if os.path.exists(sound):
                    try:
                        vc = await after.channel.connect()
                        vc.play(discord.FFmpegPCMAudio(sound))
                        while vc.is_playing():
                            await asyncio.sleep(1)
                        await vc.disconnect()
                    except Exception as e:
                        print(f"Room sound error: {e}")

        # ── Solo Mode ─────────────────────────────────
        vc = guild.voice_client
        if vc and gid in solo_guilds and not member.bot and after.channel == vc.channel:
            if vc.is_playing():
                vc.stop()
            txt = (
                discord.utils.get(guild.text_channels, name="загальний")
                or (guild.text_channels[0] if guild.text_channels else None)
            )
            kicked_set = solo_kicked.setdefault(gid, set())
            if member.id in kicked_set:
                if txt:
                    await txt.send(
                        f"♂️ Ох щіт, ай сорі {member.mention}... 🙏\n*Наш Батько повернувся!*"
                    )
                kicked_set.discard(member.id)
                solo_guilds.discard(gid)
            else:
                if txt:
                    await txt.send(
                        f"😤 {member.mention} — **Неси свій зад подальше!** ♂️"
                    )
                kicked_set.add(member.id)
                try:
                    await member.move_to(None)
                except Exception:
                    pass

    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload: discord.RawReactionActionEvent):
        if payload.user_id == self.bot.user.id:
            return
        if payload.message_id != ROLE_MESSAGE_ID:
            return

        guild = self.bot.get_guild(payload.guild_id)
        if not guild:
            return
        member = guild.get_member(payload.user_id)
        if not member:
            return

        emoji_id = payload.emoji.id  # None для unicode емодзі

        # ── Видаємо роль по емодзі ID ─────────────────
        if emoji_id in EMOJI_ROLE_MAP:
            role_id = EMOJI_ROLE_MAP[emoji_id]
            role = guild.get_role(role_id)
            if role:
                try:
                    await member.add_roles(role, reason=f"Роль по реакції: {payload.emoji.name}")
                    print(f"✅ {member.name} отримав роль: {role.name}")
                except discord.Forbidden:
                    print(f"❌ Немає прав видати роль {role.name}")

        # ── Мафія: надсилаємо тест ────────────────────
        if emoji_id == MAFIA_EMOJI_ID:
            await self._send_mafia_test(member, guild)

    @commands.Cog.listener()
    async def on_raw_reaction_remove(self, payload: discord.RawReactionActionEvent):
        if payload.message_id != ROLE_MESSAGE_ID:
            return
        guild = self.bot.get_guild(payload.guild_id)
        if not guild:
            return
        member = guild.get_member(payload.user_id)
        if not member:
            return

        emoji_id = payload.emoji.id
        if emoji_id in EMOJI_ROLE_MAP:
            role_id = EMOJI_ROLE_MAP[emoji_id]
            role = guild.get_role(role_id)
            if role:
                try:
                    await member.remove_roles(role, reason="Зняв реакцію")
                except discord.Forbidden:
                    pass

    async def _send_mafia_test(self, member: discord.Member, guild: discord.Guild):
        """Надсилає Каскадський тест у DM (1 спроба на день)"""
        can_test, remaining = can_take_test(member.id)

        if not can_test:
            try:
                embed = discord.Embed(
                    title="⏳ Зачекай!",
                    description=(
                        f"Ти вже проходив тест сьогодні.\n"
                        f"Наступна спроба через: **{remaining}**\n\n"
                        f"*Аніка спостерігає за тобою...* 👀"
                    ),
                    color=0xFF4444,
                )
                await member.send(embed=embed)
            except discord.Forbidden:
                pass
            return

        # Записуємо спробу
        record_attempt(member.id)
        test_sessions[member.id] = {"score": 0}

        try:
            q = CASCADE_TEST[0]
            embed = discord.Embed(
                title=f"🕶️ Каскадський Тест — Питання 1/{len(CASCADE_TEST)}",
                description=(
                    f"Вітаю, **{member.display_name}**!\n"
                    f"Ти хочеш вступити до **Каскадської Мафії** 💼\n\n"
                    f"Пройди тест — потрібно **{round(len(CASCADE_TEST)*0.6)}/{len(CASCADE_TEST)}** правильних.\n"
                    f"⚠️ **1 спроба на день!**\n\n"
                    f"**{q['q']}**"
                ),
                color=0x8B0000,
            )
            embed.set_footer(text="Обери правильну відповідь нижче")
            view = CascadeView(member.id, 0, self.bot, guild.id)
            await member.send(embed=embed, view=view)
        except discord.Forbidden:
            print(f"❌ DM закриті: {member.name}")

    # ── Slash команди ──────────────────────────────────

    @app_commands.command(name="solo_mode", description="♂️ Увімкнути/вимкнути режим особистого гачі")
    async def solo_mode_cmd(self, i: discord.Interaction):
        gid = i.guild_id
        if gid in solo_guilds:
            solo_guilds.discard(gid)
            vc = i.guild.voice_client
            if vc:
                vc.stop()
                await vc.disconnect()
            return await i.response.send_message("⏹️ Режим особистого гачі вимкнено.")

        if not i.user.voice:
            return await i.response.send_message("❌ Зайди в голосовий канал!", ephemeral=True)

        await i.response.defer()
        vc = i.guild.voice_client or await i.user.voice.channel.connect()
        solo_guilds.add(gid)
        solo_kicked.setdefault(gid, set()).clear()

        from cogs.music import resolve_track, FFMPEG_OPTS
        import asyncio as _asyncio
        query = random.choice(GACHI_REMIX_URLS)
        track = await resolve_track(query)

        if track and vc.is_connected():
            def after_cb(err):
                _asyncio.run_coroutine_threadsafe(
                    _solo_loop(vc, gid, self.bot), self.bot.loop
                )
            try:
                source = discord.PCMVolumeTransformer(
                    discord.FFmpegPCMAudio(track["url"], **FFMPEG_OPTS), volume=0.6
                )
                vc.play(source, after=after_cb)
            except Exception as e:
                print(f"Solo start error: {e}")

        await i.followup.send(
            "♂️ **Режим Особистого Гачі** увімкнено!\n"
            "*Хтось зайде — отримає попередження!* 😤"
        )

    @app_commands.command(name="cascade_test", description="📜 Пройти Каскадський тест вручну")
    async def cascade_test_cmd(self, i: discord.Interaction):
        can_test, remaining = can_take_test(i.user.id)
        if not can_test:
            embed = discord.Embed(
                title="⏳ Зачекай!",
                description=f"Наступна спроба через: **{remaining}**",
                color=0xFF4444,
            )
            return await i.response.send_message(embed=embed, ephemeral=True)

        record_attempt(i.user.id)
        test_sessions[i.user.id] = {"score": 0}
        q = CASCADE_TEST[0]
        embed = discord.Embed(
            title=f"📜 Каскадський Тест — Питання 1/{len(CASCADE_TEST)}",
            description=f"**{q['q']}**",
            color=0x8B0000,
        )
        embed.set_footer(text=f"⚠️ 1 спроба на день! | Потрібно {round(len(CASCADE_TEST)*0.6)}/{len(CASCADE_TEST)}")
        view = CascadeView(i.user.id, 0, self.bot, i.guild_id)
        await i.response.send_message(embed=embed, view=view, ephemeral=True)

    @app_commands.command(name="help", description="📖 Список всіх команд бота")
    async def help_cmd(self, i: discord.Interaction):
        embed = discord.Embed(
            title="♂️ Команди Гачі-Бота ♂️",
            color=0x8B0000,
        )
        sections = {
            "🎵 Музика": [
                ("/play [назва або посилання]", "SoundCloud / Spotify"),
                ("/pause · /resume · /stop · /skip", "Керування"),
                ("/queue", "Інтерактивна черга з кнопками"),
                ("/queue_remove [#]", "Видалити трек"),
                ("/gachi_remix", "Рандомний гачі-ремікс ♂️"),
            ],
            "🏆 Ранги": [
                ("/ranking [@юзер]", "Ранг, XP і прогрес"),
                ("/top", "Топ-15 братів"),
                ("/ranks", "Всі 15 рангів і вимоги"),
                ("/scan_server", "Сканувати сервер і видати всі ранги (адмін)"),
            ],
            "🎮 Ігри": [
                ("/gachi_game", "Правда чи Брехня — гачі + ігри"),
                ("/game_score · /game_reset", "Рахунок гри"),
            ],
            "⚙️ Інше": [
                ("/solo_mode", "Режим особистого гачі 😤"),
                ("/cascade_test", "Каскадський тест (1 спроба/день)"),
                ("!архів [@юзер]", "Архів після 6 місяців на сервері"),
            ],
        }
        for section, cmds in sections.items():
            embed.add_field(
                name=section,
                value="\n".join(f"`{c}` — {d}" for c, d in cmds),
                inline=False,
            )
        embed.set_footer(text="XP за кожне повідомлення 💪 | Аніка завжди поряд ♂️")
        await i.response.send_message(embed=embed)

    @commands.command(name="архів")
    async def archive_cmd(self, ctx: commands.Context, member: discord.Member = None):
        from datetime import datetime, timedelta, timezone
        member = member or ctx.author
        joined = member.joined_at
        if not joined:
            return await ctx.send("❌ Не можу визначити дату приєднання.")
        now = datetime.now(timezone.utc)
        if now - joined > timedelta(days=180):
            role = discord.utils.get(ctx.guild.roles, name="archive")
            if role:
                await member.add_roles(role)
                await ctx.send(f"📜 {member.mention} — доступ до **Архіву Братства** відкрито! 🗂️")
            else:
                await ctx.send("❌ Роль `archive` не знайдена.")
        else:
            left = timedelta(days=180) - (now - joined)
            await ctx.send(f"⏳ {member.mention} ще не пройшов 6 місяців. Залишилось: **{left.days} днів**")


# ── Solo loop ─────────────────────────────────────────
async def _solo_loop(vc: discord.VoiceClient, gid: int, bot: commands.Bot):
    if gid not in solo_guilds or not vc.is_connected():
        return
    from cogs.music import resolve_track, FFMPEG_OPTS
    query = random.choice(GACHI_REMIX_URLS)
    track = await resolve_track(query)
    if not track:
        return

    def after_cb(err):
        asyncio.run_coroutine_threadsafe(_solo_loop(vc, gid, bot), bot.loop)

    try:
        source = discord.PCMVolumeTransformer(
            discord.FFmpegPCMAudio(track["url"], **FFMPEG_OPTS), volume=0.6
        )
        vc.play(source, after=after_cb)
    except Exception as e:
        print(f"Solo loop error: {e}")


async def setup(bot: commands.Bot):
    await bot.add_cog(Events(bot))
