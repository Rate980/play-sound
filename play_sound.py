import logging
import typing
from dataclasses import dataclass, field
from pathlib import Path

import discord
from discord.ext import commands

from player import Player
from song import OnlineSong


@dataclass
class PlaySound(commands.Cog):
    bot: commands.Bot
    players: dict[int, Player] = field(default_factory=dict, init=False)

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

        await player.add(OnlineSong(url))
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


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(PlaySound(bot))


if __name__ == "__main__":
    import os

    file = Path(__file__).resolve()
    prefix = file.parent

    token = os.environ["DIS_TEST_TOKEN"]

    intents = discord.Intents.all()

    class Mybot(commands.Bot):
        async def on_ready(self) -> None:
            print("ready")

        async def setup_hook(self) -> None:
            await self.load_extension(file.stem)
            await self.tree.sync()

    bot = Mybot("t!", intents=intents)
    bot.run(token, root_logger=True, log_level=logging.INFO)
