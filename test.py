import logging

from discord.ext import commands


class Test(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot


async def setup(bot: commands.Bot):
    await bot.add_cog(Test(bot))


if __name__ == "__main__":
    import os
    from pathlib import Path

    import discord

    file = Path(__file__).resolve()
    prefix = file.parent

    token = os.environ["DIS_TEST_TOKEN"]

    intents = discord.Intents.all()

    class MyBot(commands.Bot):
        async def on_ready(self):
            channel = self.get_channel(596760218755399685)
            if not isinstance(channel, discord.abc.Messageable):
                return

            await channel.send(
                embed=discord.Embed(
                    description="[youtube](https://www.youtube.com/watch?v=NzIBCjAfNgU&list=TLPQMDcwMjIwMjOgMWb94cxOCA&index=2)"  # noqa
                )
            )

        async def setup_hook(self):
            await self.load_extension(file.stem)
            # await self.tree.sync()

    bot = MyBot("t!", intents=intents)
    bot.run(token, log_level=logging.INFO)
