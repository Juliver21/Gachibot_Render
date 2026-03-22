import discord
from discord import app_commands
from discord.ext import commands
import wavelink
import asyncio
import random
import os

# ── Lavalink на Oracle Cloud ──────────────────────────
# Бот на Render підключається до Lavalink на Oracle через HTTP
LAVALINK_NODES = [
    # Твій локальний Lavalink на Oracle (замінити на публічний IP!)
    {
        "uri": f"http://{os.getenv('LAVALINK_HOST', '92.5.65.48')}:2333",
        "password": os.getenv("LAVALINK_PASS", "gachi_password"),
    },
    # Публічні резервні сервери
    {"uri": "http://lavalink.serenetia.com:80",  "password": "https://dsc.gg/ajidevserver"},
    {"uri": "http://lavalink.jirayu.net:13592",  "password": "youshallnotpass"},
]

GACHI_QUERIES = [
    "billy herrington gachi remix",
    "feel the power gachi remix",
    "dungeon master gachi remix",
    "are you ready gachi remix",
    "van damme gachi remix",
    "gachi muchi remix",
]


def fmt_duration(ms: int) -> str:
    if not ms:
        return "??:??"
    sec = ms // 1000
    m, s = divmod(sec, 60)
    h, m = divmod(m, 60)
    return f"{h}:{m:02d}:{s:02d}" if h else f"{m}:{s:02d}"


class GachiPlayer(wavelink.Player):
    async def on_voice_server_update(self, data: dict) -> None:
        print(f"📡 Voice server update — форсуємо connected")
        await super().on_voice_server_update(data)
        if hasattr(self, '_connected') and not self._connected.is_set():
            self._connected.set()
            print(f"✅ _connected встановлено")

    async def connect(self, *, timeout: float = 30.0, reconnect: bool = True,
                      self_deaf: bool = True, self_mute: bool = False) -> None:
        try:
            await super().connect(
                timeout=timeout, reconnect=reconnect,
                self_deaf=self_deaf, self_mute=self_mute,
            )
        except Exception as e:
            if "timeout" in str(e).lower() or "exceeded" in str(e).lower():
                print(f"⚠️ connect таймаут — продовжуємо")
            else:
                raise


class QueueView(discord.ui.View):
    def __init__(self, player: GachiPlayer):
        super().__init__(timeout=120)
        self.player = player

    def build_embed(self) -> discord.Embed:
        embed = discord.Embed(title="🎵 Черга відтворення", color=0x8B0000)
        if self.player.current:
            t = self.player.current
            embed.add_field(
                name="▶️ Зараз грає",
                value=f"**[{t.title}]({t.uri})** `{fmt_duration(t.length)}`",
                inline=False,
            )
        total = len(self.player.queue)
        if total == 0:
            embed.add_field(name="Черга порожня", value="Додай через `/play назва` 🎵", inline=False)
        else:
            lines = [
                f"`{i+1}.` [{t.title}]({t.uri}) `{fmt_duration(t.length)}`"
                for i, t in enumerate(list(self.player.queue)[:10])
            ]
            embed.add_field(name=f"В черзі: {total}", value="\n".join(lines), inline=False)
            loop_on = self.player.queue.mode == wavelink.QueueMode.loop_all
            embed.set_footer(text=f"🔁 Loop: {'ON' if loop_on else 'OFF'}")
        return embed

    @discord.ui.button(label="🔄 Оновити", style=discord.ButtonStyle.primary)
    async def refresh(self, i: discord.Interaction, _):
        await i.response.edit_message(embed=self.build_embed(), view=self)

    @discord.ui.button(label="⏭️ Пропустити", style=discord.ButtonStyle.danger)
    async def skip_btn(self, i: discord.Interaction, _):
        if self.player.playing:
            await self.player.skip()
            await i.response.send_message("⏭️ Пропущено!", ephemeral=True)
        else:
            await i.response.send_message("❌ Нічого не грає.", ephemeral=True)

    @discord.ui.button(label="🔁 Loop", style=discord.ButtonStyle.secondary)
    async def loop_btn(self, i: discord.Interaction, _):
        if self.player.queue.mode == wavelink.QueueMode.loop_all:
            self.player.queue.mode = wavelink.QueueMode.normal
            await i.response.send_message("🔁 Loop: **OFF ❌**", ephemeral=True)
        else:
            self.player.queue.mode = wavelink.QueueMode.loop_all
            await i.response.send_message("🔁 Loop: **ON ✅**", ephemeral=True)

    @discord.ui.button(label="🗑️ Очистити", style=discord.ButtonStyle.danger)
    async def clear_btn(self, i: discord.Interaction, _):
        self.player.queue.clear()
        await i.response.edit_message(embed=self.build_embed(), view=self)


class Music(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_ready(self):
        await self._connect_lavalink()

    async def _connect_lavalink(self):
        nodes = [wavelink.Node(uri=n["uri"], password=n["password"]) for n in LAVALINK_NODES]
        try:
            await wavelink.Pool.connect(nodes=nodes, client=self.bot, cache_capacity=None)
            print(f"✅ Lavalink: підключаємось до {len(nodes)} серверів...")
        except Exception as e:
            # Не крашимо бота якщо Lavalink недоступний
            print(f"⚠️ Lavalink недоступний: {e}")
            print("⚠️ Музика не працюватиме поки Lavalink не підключиться")

    @commands.Cog.listener()
    async def on_wavelink_node_ready(self, payload: wavelink.NodeReadyEventPayload):
        print(f"✅ Lavalink Node готовий: {payload.node.uri}")

    @commands.Cog.listener()
    async def on_wavelink_track_start(self, payload: wavelink.TrackStartEventPayload):
        player: GachiPlayer = payload.player
        track = payload.track
        print(f"🎵 Track start: {track.title}")
        if not hasattr(player, "text_channel") or not player.text_channel:
            return
        embed = discord.Embed(
            title="♂️ Зараз грає",
            description=(
                f"**[{track.title}]({track.uri})**\n"
                f"⏱ `{fmt_duration(track.length)}` | "
                f"👤 {getattr(track, 'requester', '?')}"
            ),
            color=0x8B0000,
        )
        if hasattr(track, 'artwork') and track.artwork:
            embed.set_thumbnail(url=track.artwork)
        await player.text_channel.send(embed=embed)

    @commands.Cog.listener()
    async def on_wavelink_track_end(self, payload: wavelink.TrackEndEventPayload):
        player: GachiPlayer = payload.player
        print(f"⏹ Track end: reason={payload.reason}")
        # Автоматично грає наступний трек з черги
        if player.queue:
            try:
                next_track = player.queue.get()
                await player.play(next_track)
                print(f"▶️ Авто-наступний: {next_track.title}")
            except Exception as e:
                print(f"❌ Авто-наступний error: {e}")

    @commands.Cog.listener()
    async def on_wavelink_inactive_player(self, player: wavelink.Player):
        """Не відключаємось автоматично"""
        print(f"⚠️ Inactive player — залишаємось в каналі")

    async def _search_track(self, query: str) -> "wavelink.Playable | None":
        # Перевіряємо чи є підключені ноди
        try:
            nodes = wavelink.Pool.nodes
            if not nodes:
                print("❌ Немає підключених Lavalink нодів")
                return None
        except Exception:
            return None

        print(f"🔎 Шукаю: {query[:80]}")
        try:
            if "utm" in query:
                query = query.split("?")[0]
            if query.startswith("http"):
                tracks = await wavelink.Playable.search(query)
            else:
                tracks = await wavelink.Playable.search(
                    query, source=wavelink.TrackSource.SoundCloud
                )
            if not tracks:
                tracks = await wavelink.Playable.search(query)
            if not tracks:
                return None
            track = tracks.tracks[0] if isinstance(tracks, wavelink.Playlist) else tracks[0]
            print(f"✅ Знайдено: {track.title}")
            return track
        except Exception as e:
            print(f"❌ Пошук: {e}")
            return None

    async def _connect_player(self, channel: discord.VoiceChannel, text_channel) -> "GachiPlayer | None":
        guild = channel.guild
        player: GachiPlayer = guild.voice_client  # type: ignore

        if not player:
            print(f"🔌 Підключаюсь до: {channel.name}")
            try:
                player = await channel.connect(cls=GachiPlayer, self_deaf=True)
            except Exception as e:
                err = str(e).lower()
                if "timeout" in err or "exceeded" in err:
                    await asyncio.sleep(0.5)
                    player = guild.voice_client
                    if not player:
                        print(f"❌ Player не знайдено після таймауту")
                        return None
                    print(f"✅ Player знайдено після таймауту")
                else:
                    print(f"❌ connect error: {e}")
                    return None
            try:
                player.text_channel = text_channel
                player.autoplay = wavelink.AutoPlayMode.disabled
            except Exception:
                pass
            print(f"✅ Підключено!")
        elif player.channel != channel:
            await player.move_to(channel)

        return player

    @app_commands.command(name="play", description="▶️ Грати музику — введи назву або посилання")
    @app_commands.describe(query="Назва треку або посилання")
    async def play(self, interaction: discord.Interaction, query: str):
        if not interaction.user.voice:
            return await interaction.response.send_message("❌ Зайди в голосовий канал!", ephemeral=True)

        await interaction.response.defer()

        # 1️⃣ Спочатку шукаємо
        search_msg = await interaction.followup.send(f"🔍 Шукаю: **{query[:60]}**...")
        track = await self._search_track(query)
        if not track:
            await search_msg.edit(content="❌ Нічого не знайдено!")
            return

        track.requester = interaction.user.display_name
        await search_msg.edit(content=f"✅ **{track.title}** — підключаюсь...")

        # 2️⃣ Перевіряємо чи вже грає
        existing: GachiPlayer = interaction.guild.voice_client  # type: ignore
        if existing and (existing.playing or existing.paused):
            existing.queue.put(track)
            await search_msg.edit(content=None)
            embed = discord.Embed(
                title="➕ Додано до черги",
                description=f"**[{track.title}]({track.uri})**\n`{fmt_duration(track.length)}` | Позиція: **#{len(existing.queue)}**",
                color=0x555555,
            )
            await interaction.followup.send(embed=embed)
            return

        # 3️⃣ Підключаємось і граємо
        player = await self._connect_player(interaction.user.voice.channel, interaction.channel)
        if not player:
            await search_msg.edit(content="❌ Не вдалося підключитись!")
            return

        try:
            player.text_channel = interaction.channel
            await player.play(track)
            await search_msg.edit(content=f"▶️ Відтворюю: **{track.title}**")
        except Exception as e:
            print(f"‼ play() error: {e}")
            await search_msg.edit(content=f"❌ Помилка відтворення: {e}")

    @app_commands.command(name="pause", description="⏸️ Пауза")
    async def pause(self, i: discord.Interaction):
        player: GachiPlayer = i.guild.voice_client  # type: ignore
        if player and player.playing:
            await player.pause(True)
            await i.response.send_message("⏸️ Пауза!")
        else:
            await i.response.send_message("❌ Нічого не грає.", ephemeral=True)

    @app_commands.command(name="resume", description="▶️ Продовжити відтворення")
    async def resume(self, i: discord.Interaction):
        player: GachiPlayer = i.guild.voice_client  # type: ignore
        if player and player.paused:
            await player.pause(False)
            await i.response.send_message("▶️ Продовжую!")
        else:
            await i.response.send_message("❌ Музика не на паузі.", ephemeral=True)

    @app_commands.command(name="stop", description="⏹️ Зупинити та відключитись")
    async def stop(self, i: discord.Interaction):
        player: GachiPlayer = i.guild.voice_client  # type: ignore
        if player:
            player.queue.clear()
            await player.stop()
            await player.disconnect()
            await i.response.send_message("⏹️ Зупинено та відключено!")
        else:
            await i.response.send_message("❌ Бот не в каналі.", ephemeral=True)

    @app_commands.command(name="skip", description="⏭️ Пропустити поточний трек")
    async def skip(self, i: discord.Interaction):
        player: GachiPlayer = i.guild.voice_client  # type: ignore
        if player and player.playing:
            await player.skip()
            await i.response.send_message("⏭️ Пропущено!")
        else:
            await i.response.send_message("❌ Нічого не грає.", ephemeral=True)

    @app_commands.command(name="queue", description="📋 Переглянути та керувати чергою")
    async def queue(self, i: discord.Interaction):
        player: GachiPlayer = i.guild.voice_client  # type: ignore
        if not player:
            return await i.response.send_message("❌ Бот не грає музику.", ephemeral=True)
        await i.response.send_message(embed=QueueView(player).build_embed(), view=QueueView(player))

    @app_commands.command(name="queue_remove", description="🗑️ Видалити трек з черги за номером")
    @app_commands.describe(position="Номер треку в черзі (починаючи з 1)")
    async def queue_remove(self, i: discord.Interaction, position: int):
        player: GachiPlayer = i.guild.voice_client  # type: ignore
        if not player:
            return await i.response.send_message("❌ Бот не грає музику.", ephemeral=True)
        try:
            queue_list = list(player.queue)
            if position < 1 or position > len(queue_list):
                return await i.response.send_message(f"❌ Немає треку #{position}.", ephemeral=True)
            title = queue_list[position - 1].title
            del player.queue[position - 1]
            await i.response.send_message(f"🗑️ Видалено: **{title}**")
        except Exception as e:
            await i.response.send_message(f"❌ Помилка: {e}", ephemeral=True)

    @app_commands.command(name="gachi_remix", description="♂️ Рандомний гачі-ремікс!")
    async def gachi_remix(self, i: discord.Interaction):
        if not i.user.voice:
            return await i.response.send_message("❌ Зайди в голосовий канал!", ephemeral=True)

        await i.response.defer()

        query = random.choice(GACHI_QUERIES)
        search_msg = await i.followup.send(f"🔍 Шукаю ремікс: **{query}**...")

        track = await self._search_track(query)
        if not track:
            await search_msg.edit(content="❌ Не вдалося знайти ремікс!")
            return

        track.requester = "♂️ Гачі-Бот"
        existing: GachiPlayer = i.guild.voice_client  # type: ignore

        if existing and (existing.playing or existing.paused):
            existing.queue.put(track)
            await search_msg.edit(content=f"♂️ Ремікс додано: **{track.title}**")
            return

        player = await self._connect_player(i.user.voice.channel, i.channel)
        if not player:
            await search_msg.edit(content="❌ Не вдалося підключитись!")
            return

        try:
            player.text_channel = i.channel
            await player.play(track)
            await search_msg.edit(content=f"♂️ **FEEL THE POWER!** ♂️\nГраю: **{track.title}**")
        except Exception as e:
            print(f"‼ gachi_remix error: {e}")
            await search_msg.edit(content=f"❌ Помилка: {e}")


async def setup(bot: commands.Bot):
    await bot.add_cog(Music(bot))
