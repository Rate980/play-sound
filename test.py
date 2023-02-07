import asyncio
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
            channel = self.get_channel(540816542191845386)
            if not isinstance(channel, discord.VoiceChannel):
                channel = await self.fetch_channel(540816542191845386)
            if not isinstance(channel, discord.VoiceChannel):
                return

            voice = await channel.connect()
            s = discord.FFmpegPCMAudio(
                r"C:\Users\2220208\play-sound\cache\ZVSSBUvm62o.m4a"
            )
            voice.play(
                s,
                after=lambda _: voice.play(s),
            )

        async def setup_hook(self):
            await self.load_extension(file.stem)
            # await self.tree.sync()

    bot = MyBot("t!", intents=intents)
    bot.run(token, log_level=logging.INFO)
