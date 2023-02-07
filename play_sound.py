import logging
import re
import typing
from pathlib import Path

import discord
from discord.ext import commands, tasks

from errors import AudioSourceNotFoundError
from player import Player
from song import DiscordMessageLinkSong, OnlineSong, Song, YoutubeSong, YtDlpSong


# @dataclass
class PlaySound(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot: commands.Bot = bot
        self.players: dict[int, Player] = dict()
        self.delete_disconnected.start()

    async def cog_unload(self):
        self.delete_disconnected.cancel()

    def get_song(self, link: str) -> Song:
        if not re.match(r"https?://[\w!?/+\-_~;.,*&@#$%()'[\]]+", link):
            raise AudioSourceNotFoundError

        if re.match(r"https://discord\.com/channels/[0-9]+/[0-9]+/[0-9]+", link):
            return DiscordMessageLinkSong(link, self.bot)

        if (
            re.match(
                r"https?://(?:www|music|m)\.(?:youtube\.com|youtu\.be)/(?:watch\?v=|embed)?[a-zA-Z0-9_\-]+",  # noqa
                link,
            )
            or re.match(r"https?//soundcloud.com/\w+/\w+", link)
            or re.match(r"https?://youtu.be/[a-zA-Z0-9_\-]+", link)
        ):
            return YoutubeSong(link)

        return OnlineSong(link)

    def get_player(self, guild_id: int):
        player = self.players.get(guild_id)
        return player if player is not None and not player.disconnected else None

    @commands.hybrid_command(aliases=["p"])
    @commands.guild_only()
    async def play(self, ctx: commands.Context, url: str):
        guild = typing.cast(discord.Guild, ctx.guild)
        if (player := self.get_player(guild.id)) is None:
            author = typing.cast(discord.Member, ctx.author)
            if (voice := author.voice) is None or voice.channel is None:
                await ctx.send("vc入れや")
                return

            player = Player(await voice.channel.connect(), self.bot.loop)
            self.players[guild.id] = player
            if not (
                re.match(
                    r"https?://(?:www|music|m)\.youtube\.com/(?:watch\?v=|embed/|shorts/)[a-zA-Z0-9_\-]+",  # noqa
                    url,
                )
                or re.match(
                    r"https?://soundcloud.com/[a-zA-Z0-9_\-]+/[a-zA-Z0-9_\-]+", url
                )
                or re.match(r"https?://youtu.be/[a-zA-Z0-9_\-]+", url)
            ):
                await ctx.send("soundcloud or youtube plz")
                return
        try:
            # if url is None:
            #     song = DiscordMessageSong(ctx.message)
            # else:
            #     # song = self.get_song(url)
            song = YtDlpSong(url)
            player.add(song)
        except AudioSourceNotFoundError:
            await ctx.send("ないよ")

    @commands.hybrid_command(aliases=["summon", "fuckon"])
    @commands.guild_only()
    async def join(self, ctx: commands.Context) -> None:
        guild = typing.cast(discord.Guild, ctx.guild)

        if self.get_player(guild.id) is not None:
            await ctx.send("もうおるで")
            return

        author = typing.cast(discord.Member, ctx.author)
        if (voice := author.voice) is None or (channel := voice.channel) is None:
            await ctx.send("vc入れや")
            return

        self.players[guild.id] = Player(await channel.connect(), self.bot.loop)
        await ctx.send("やあ")

    @commands.hybrid_command(aliases=["dis", "dc", "leave", "fuckoff"])
    @commands.guild_only()
    async def disconnect(self, ctx: commands.Context):
        guild = typing.cast(discord.Guild, ctx.guild)
        if (player := self.get_player(guild.id)) is None:
            await ctx.send("おらんで")
            return

        await player.disconnect()
        await ctx.send("bye")

    @commands.hybrid_command(aliases=["s", "skip", "next"])
    @commands.guild_only()
    async def voteskip(self, ctx: commands.Context):
        guild = typing.cast(discord.Guild, ctx.guild)
        if (player := self.get_player(guild.id)) is None:
            await ctx.send("おらんで")
            return

        player.skip()

    @commands.hybrid_command(aliases=["q"])
    @commands.guild_only()
    async def queue(self, ctx):
        guild = typing.cast(discord.Guild, ctx.guild)
        if (player := self.get_player(guild.id)) is None:
            await ctx.send("おらんで")
            return

        if (now_play := player.now_play) is None:
            return
        queue = player.get_queue()
        embed = discord.Embed(
            title=f"Queue of {guild.name}",
        )
        embed.add_field(
            name="",
            value="__Play now:__\n" + f"[{now_play.title}]({now_play.url})"  # type: ignore
            if hasattr(now_play, "url")
            else now_play.title,
        )
        embed.add_field(
            name="",
            value="__Next up:__\n"
            + "\n".join(
                [
                    f"`{i + 1}.` [{x.title}]({x.url})"  # type: ignore
                    for i, x in enumerate(queue)
                    if hasattr(x, "url")
                ]
            ),
            inline=False,
        )
        await ctx.send(embed=embed)

    @commands.hybrid_command(aliases=["np"])
    @commands.guild_only()
    async def nowplaying(self, ctx: commands.Context):
        guild = typing.cast(discord.Guild, ctx.guild)
        if (player := self.get_player(guild.id)) is None:
            await ctx.send("おらんで")
            return

        if (now_play := player.now_play) is None:
            await ctx.send("再生してないよ")
            return

        await ctx.send(
            embed=discord.Embed(
                title="Now Playing",
                description=f"[{now_play.title}]({now_play.url})"  # type: ignore
                if hasattr(now_play, "url")
                else now_play.title,
            )
        )

    @commands.hybrid_command()
    @commands.guild_only()
    async def pause(self, ctx: commands.Context):
        guild = typing.cast(discord.Guild, ctx.guild)
        if (player := self.get_player(guild.id)) is None:
            await ctx.send("おらんで")
            return
        if player.is_paused():
            await ctx.send("もうしてる")
        player.pause()
        await ctx.send("pausing!")

    @commands.hybrid_command(aliases=["re"])
    @commands.guild_only()
    async def resume(self, ctx: commands.Context):
        guild = typing.cast(discord.Guild, ctx.guild)
        if (player := self.get_player(guild.id)) is None:
            await ctx.send("おらんで")
            return

        if not player.is_paused():
            await ctx.send("もうしてる")
        player.resume()
        await ctx.send("resume!")

    @commands.hybrid_command(aliases=["repeat"])
    @commands.guild_only()
    async def loop(self, ctx: commands.Context):
        guild = typing.cast(discord.Guild, ctx.guild)
        if (player := self.get_player(guild.id)) is None:
            await ctx.send("おらんで")
            return
        player.loop_song = not player.loop_song
        msg = "🔂"
        if player.loop_song:
            msg += "Enabled!"
        else:
            msg += "Disabled!"
        await ctx.send(msg)

    @commands.hybrid_command(aliases=["loopqueue", "lq", "queueloop"])
    @commands.guild_only()
    async def qloop(self, ctx: commands.Context):
        guild = typing.cast(discord.Guild, ctx.guild)
        if (player := self.get_player(guild.id)) is None:
            await ctx.send("おらんで")
            return

        player.loop_queue = not player.loop_queue
        msg = "🔂"
        if player.loop_queue:
            msg += "Enabled!"
        else:
            msg += "Disabled!"
        await ctx.send(msg)

    @tasks.loop(hours=1)
    async def delete_disconnected(self):
        self.players = {k: v for k, v in self.players.items() if not v.disconnected}


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(PlaySound(bot))


if __name__ == "__main__":
    import os

    file = Path(__file__).resolve()
    prefix = file.parent

    token = os.environ["DIS_TEST_TOKEN"]

    intents = discord.Intents.all()

    class MyBot(commands.Bot):
        async def on_ready(self) -> None:
            print("ready")

        async def setup_hook(self) -> None:
            await self.load_extension(file.stem)
            await self.tree.sync()

    bot = MyBot("t!", intents=intents)
    bot.run(token, root_logger=True, log_level=logging.INFO)
