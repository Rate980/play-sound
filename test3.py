import os

import discord
from discord.ext import commands

token = os.environ["DIS_TEST_TOKEN"]

intents = discord.Intents.all()


# def check(self):
#     async def inner(ctx: commands.Context):
#         return bool(self)

#     return commands.check(inner)


def check():
    async def inner(ctx: commands.Context):
        print(ctx.cog.id)
        return True

    return commands.check(inner)


class TestCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.id = 1

    @check()
    @commands.command()
    async def test(self, ctx):
        pass


class MyBot(commands.Bot):
    async def on_ready(self) -> None:
        print("ready")

    async def setup_hook(self) -> None:
        await self.add_cog(TestCog(self))


bot = MyBot("t!", intents=intents)


@bot.hybrid_command(aliases=["p"])
async def play(ctx: commands.Context):
    await ctx.send("a")


@bot.event
async def on_error(ctx: commands.Context, exertion: Exception):
    await ctx.send(str(exertion))


bot.run(
    token,
    root_logger=True,
)
