import discord
from discord import app_commands
from discord.ext import commands
import wavelink
import asyncio
import random
from config import LAVALINK_HOST, LAVALINK_PORT, LAVALINK_PASS, LAVALINK_SSL


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


class QueueView(discord.ui.View):
    def __init__(self, player: wavelink.Player):
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
            embed.add_field(name="Черга порожня", value="Додай треки через `/play назва` 🎵", inline=False)
        else:
            lines = [
                f"`{i+1}.` [{t.title}]({t.uri}) `{fmt_duration(t.length)}`"
                for i, t in enumerate(list(self.player.queue)[:10])
            ]
            embed.add_field(name=f"В черзі: {total}", value="\n".join(lines), inline=False)
            loop_status = "ON" if self.player.queue.mode == wavelink.QueueMode.loop_all else "OFF"
            embed.set_footer(text=f"🔁 Loop: {loop_status}")
        return embed

    @discord.ui.button(label="🔄 Оновити", style=discord.ButtonStyle.primary, row=0)
    async def refresh(self, i: discord.Interaction, _):
        await i.response.edit_message(embed=self.build_embed(), view=self)

    @discord.ui.button(label="⏭️ Пропустити", style=discord.ButtonStyle.danger, row=0)
    async def skip_btn(self, i: discord.Interaction, _):
        if self.player.playing:
            await self.player.skip()
            await i.response.send_message("⏭️ Пропущено!", ephemeral=True)
        else:
            await i.response.send_message("❌ Нічого не грає.", ephemeral=True)

    @discord.ui.button(label="🔁 Loop", style=discord.ButtonStyle.secondary, row=0)
    async def loop_btn(self, i: discord.Interaction, _):
        if self.player.queue.mode == wavelink.QueueMode.loop_all:
            self.player.queue.mode = wavelink.QueueMode.normal
            await i.response.send_message("🔁 Loop: **OFF ❌**", ephemeral=True)
        else:
            self.player.queue.mode = wavelink.QueueMode.loop_all
            await i.response.send_message("🔁 Loop: **ON ✅**", ephemeral=True)

    @discord.ui.button(label="🗑️ Очистити", style=discord.ButtonStyle.danger, row=0)
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
        proto = "https" if LAVALINK_SSL else "http"
        uri = f"{proto}://{LAVALINK_HOST}:{LAVALINK_PORT}"
        node = wavelink.Node(uri=uri, password=LAVALINK_PASS)
        try:
            await wavelink.Pool.connect(nodes=[node], client=self.bot)
            print(f"✅ Lavalink підключено: {uri}")
        except Exception as e:
            print(f"❌ Lavalink помилка: {e}")

    @commands.Cog.listener()
    async def on_wavelink_node_ready(self, payload: wavelink.NodeReadyEventPayload):
        print(f"✅ Lavalink Node готовий: {payload.node.uri}")

    @commands.Cog.listener()
    async def on_wavelink_track_start(self, payload: wavelink.TrackStartEventPayload):
        player: wavelink.Player = payload.player
        track = payload.track
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
        if track.artwork:
            embed.set_thumbnail(url=track.artwork)
        await player.text_channel.send(embed=embed)

    @commands.Cog.listener()
    async def on_wavelink_track_end(self, payload: wavelink.TrackEndEventPayload):
        player: wavelink.Player = payload.player
        if not player.queue and not player.playing:
            await asyncio.sleep(300)
            if not player.playing:
                await player.disconnect()

    async def _get_player(self, interaction: discord.Interaction) -> wavelink.Player | None:
        if not interaction.user.voice:
            await interaction.followup.send("❌ Зайди в голосовий канал!", ephemeral=True)
            return None
        channel = interaction.user.voice.channel
        player: wavelink.Player = interaction.guild.voice_client  # type: ignore
        if not player:
            try:
                player = await channel.connect(cls=wavelink.Player, timeout=30.0)
                player.text_channel = interaction.channel
                player.autoplay = wavelink.AutoPlayMode.disabled
            except Exception as e:
                await interaction.followup.send(f"❌ Не вдалося підключитись: {e}", ephemeral=True)
                return None
        elif player.channel != channel:
            await player.move_to(channel)
        return player

    @app_commands.command(name="play", description="▶️ Грати музику — введи назву або SoundCloud посилання")
    @app_commands.describe(query="Назва треку або SoundCloud посилання")
    async def play(self, interaction: discord.Interaction, query: str):
        await interaction.response.defer()
        player = await self._get_player(interaction)
        if not player:
            return

        print(f"🔎 Шукаю: {query}")
        try:
            if query.startswith("https://soundcloud.com"):
                tracks = await wavelink.Playable.search(query)
            else:
                tracks = await wavelink.Playable.search(query, source=wavelink.TrackSource.SoundCloud)
            if not tracks:
                tracks = await wavelink.Playable.search(query)
        except Exception as e:
            await interaction.followup.send(f"❌ Помилка пошуку: {e}")
            return

        if not tracks:
            await interaction.followup.send("❌ Нічого не знайдено!")
            return

        track = tracks.tracks[0] if isinstance(tracks, wavelink.Playlist) else tracks[0]
        track.requester = interaction.user.display_name
        print(f"✅ Знайдено: {track.title}")

        if player.playing or player.paused:
            player.queue.put(track)
            embed = discord.Embed(
                title="➕ Додано до черги",
                description=f"**[{track.title}]({track.uri})**\n`{fmt_duration(track.length)}` | Позиція: **#{len(player.queue)}**",
                color=0x555555,
            )
            await interaction.followup.send(embed=embed)
        else:
            player.text_channel = interaction.channel
            await player.play(track)
            await interaction.followup.send(f"▶️ Відтворюю: **{track.title}**")

    @app_commands.command(name="pause", description="⏸️ Пауза")
    async def pause(self, i: discord.Interaction):
        player: wavelink.Player = i.guild.voice_client  # type: ignore
        if player and player.playing:
            await player.pause(True)
            await i.response.send_message("⏸️ Пауза!")
        else:
            await i.response.send_message("❌ Нічого не грає.", ephemeral=True)

    @app_commands.command(name="resume", description="▶️ Продовжити відтворення")
    async def resume(self, i: discord.Interaction):
        player: wavelink.Player = i.guild.voice_client  # type: ignore
        if player and player.paused:
            await player.pause(False)
            await i.response.send_message("▶️ Продовжую!")
        else:
            await i.response.send_message("❌ Музика не на паузі.", ephemeral=True)

    @app_commands.command(name="stop", description="⏹️ Зупинити та відключитись")
    async def stop(self, i: discord.Interaction):
        player: wavelink.Player = i.guild.voice_client  # type: ignore
        if player:
            player.queue.clear()
            await player.stop()
            await player.disconnect()
            await i.response.send_message("⏹️ Зупинено та відключено!")
        else:
            await i.response.send_message("❌ Бот не в каналі.", ephemeral=True)

    @app_commands.command(name="skip", description="⏭️ Пропустити поточний трек")
    async def skip(self, i: discord.Interaction):
        player: wavelink.Player = i.guild.voice_client  # type: ignore
        if player and player.playing:
            await player.skip()
            await i.response.send_message("⏭️ Пропущено!")
        else:
            await i.response.send_message("❌ Нічого не грає.", ephemeral=True)

    @app_commands.command(name="queue", description="📋 Переглянути та керувати чергою")
    async def queue(self, i: discord.Interaction):
        player: wavelink.Player = i.guild.voice_client  # type: ignore
        if not player:
            return await i.response.send_message("❌ Бот не грає музику.", ephemeral=True)
        view = QueueView(player)
        await i.response.send_message(embed=view.build_embed(), view=view)

    @app_commands.command(name="queue_remove", description="🗑️ Видалити трек з черги за номером")
    @app_commands.describe(position="Номер треку в черзі (починаючи з 1)")
    async def queue_remove(self, i: discord.Interaction, position: int):
        player: wavelink.Player = i.guild.voice_client  # type: ignore
        if not player:
            return await i.response.send_message("❌ Бот не грає музику.", ephemeral=True)
        try:
            if position < 1 or position > len(player.queue):
                return await i.response.send_message(f"❌ Немає треку #{position}.", ephemeral=True)
            track = list(player.queue)[position - 1]
            del player.queue[position - 1]
            await i.response.send_message(f"🗑️ Видалено: **{track.title}**")
        except Exception as e:
            await i.response.send_message(f"❌ Помилка: {e}", ephemeral=True)

    @app_commands.command(name="gachi_remix", description="♂️ Рандомний гачі-ремікс!")
    async def gachi_remix(self, i: discord.Interaction):
        await i.response.defer()
        player = await self._get_player(i)
        if not player:
            return
        query = random.choice(GACHI_QUERIES)
        try:
            tracks = await wavelink.Playable.search(query, source=wavelink.TrackSource.SoundCloud)
            if not tracks:
                tracks = await wavelink.Playable.search(query)
        except Exception as e:
            await i.followup.send(f"❌ Помилка пошуку: {e}")
            return
        if not tracks:
            await i.followup.send("❌ Не вдалося знайти ремікс!")
            return
        track = tracks.tracks[0] if isinstance(tracks, wavelink.Playlist) else tracks[0]
        track.requester = "♂️ Гачі-Бот"
        if player.playing or player.paused:
            player.queue.put(track)
            await i.followup.send(f"♂️ Ремікс додано до черги: **{track.title}**")
        else:
            player.text_channel = i.channel
            await player.play(track)
            await i.followup.send(f"♂️ **FEEL THE POWER!** ♂️\nГраю: **{track.title}**")


async def setup(bot: commands.Bot):
    await bot.add_cog(Music(bot))
