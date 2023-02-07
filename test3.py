import discord
from discord.ext import commands

if __name__ == "__main__":
    import os

    token = os.environ["DIS_TEST_TOKEN"]

    intents = discord.Intents.all()

    class MyBot(commands.Bot):
        async def on_ready(self) -> None:
            print("ready")

        async def setup_hook(self) -> None:
            await self.tree.sync()

    bot = MyBot("t!", intents=intents)

    @bot.hybrid_command(aliases=["p"])
    async def play(ctx: commands.Context):
        await ctx.send("a")

    bot.run(
        token,
        root_logger=True,
    )
