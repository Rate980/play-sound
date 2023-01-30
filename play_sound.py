import logging
import typing
from dataclasses import dataclass, field
from mimetypes import init
from pathlib import Path

import discord
from discord.ext import commands, tasks

from player import Player
from song import OnlineSong, YoutubeSong


# @dataclass
class PlaySound(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot: commands.Bot = bot
        self.players: dict[int, Player] = dict()

    @commands.hybrid_command()
    @commands.guild_only()
    async def play(self, ctx: commands.Context, url: str):
        guild = typing.cast(discord.Guild, ctx.guild)
        if (player := self.players.get(guild.id)) is None or player.disconnected:
            author = typing.cast(discord.Member, ctx.author)
            if (voice := author.voice) is None or voice.channel is None:
                await ctx.send("vc入れや")
                return

            player = Player(await voice.channel.connect(), self.bot.loop)

        await player.add(YoutubeSong(url))
        self.players[guild.id] = player

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
    token = "OTc0NjE1NDQ1MjI5NDA0MjEw.GAXKVx.PnDLESyvs6vfFmXUecol4W6s8yHGwUTljbTX6w"

    intents = discord.Intents.all()

    class Mybot(commands.Bot):
        async def on_ready(self) -> None:
            print("ready")

        async def setup_hook(self) -> None:
            await self.load_extension(file.stem)
            await self.tree.sync()

    bot = Mybot("t!", intents=intents)
    bot.run(token, root_logger=True, log_level=logging.INFO)
