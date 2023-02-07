import logging
import re
import typing
from pathlib import Path

import discord
from discord.ext import commands, tasks

from errors import AudioSourceNotFoundError
from player import Player
from song import (
    DiscordMessageLinkSong,
    DiscordMessageSong,
    OnlineSong,
    Song,
    YoutubeSong,
)


# @dataclass
class PlaySound(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot: commands.Bot = bot
        self.players: dict[int, Player] = dict()

    def get_song(self, link: str) -> Song:
        if not re.match(r"https?://[\w!?/+\-_~;.,*&@#$%()'[\]]+", link):
            raise AudioSourceNotFoundError

        if re.match(r"https://discord\.com/channels/[0-9]+/[0-9]+/[0-9]+", link):
            return DiscordMessageLinkSong(link, self.bot)

        if (
            re.match(
                r"https?://(?:www|music|m)\.(?:youtube\.com|youtu\.be)/(?:watch\?v=|embed)?[a-zA-Z0-9_\-]+",
                link,
            )
            or re.match(r"https?//soundcloud.com/\w+/\w+", link)
            or re.match(r"https?://youtu.be/[a-zA-Z0-9_\-]+", link)
        ):
            return YoutubeSong(link)

        return OnlineSong(link)

    @commands.hybrid_command()
    @commands.guild_only()
    async def play(self, ctx: commands.Context, url: str | None = None):
        guild = typing.cast(discord.Guild, ctx.guild)
        if (player := self.players.get(guild.id)) is None or player.disconnected:
            author = typing.cast(discord.Member, ctx.author)
            if (voice := author.voice) is None or voice.channel is None:
                await ctx.send("vc入れや")
                return

            player = Player(await voice.channel.connect(), self.bot.loop)
        try:
            if url is None:
                song = DiscordMessageSong(ctx.message)
            else:
                song = self.get_song(url)
            player.add(song)
            self.players[guild.id] = player
        except AudioSourceNotFoundError:
            await ctx.send("ないよ")

    @commands.hybrid_command()
    @commands.guild_only()
    async def join(self, ctx: commands.Context) -> None:
        guild = typing.cast(discord.Guild, ctx.guild)

        if (
            player := self.players.get(guild.id)
        ) is not None and not player.disconnected:
            await ctx.send("もうおるで")
            return

        author = typing.cast(discord.Member, ctx.author)
        if (voice := author.voice) is None or (channel := voice.channel) is None:
            await ctx.send("vc入れや")
            return

        self.players[guild.id] = Player(await channel.connect(), self.bot.loop)

    @commands.hybrid_command()
    @commands.guild_only()
    async def disconnect(self, ctx: commands.Context):
        guild = typing.cast(discord.Guild, ctx.guild)
        if (player := self.players.get(guild.id)) is None or player.disconnected:
            await ctx.send("おらんで")
            return

        await player.disconnect()

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
