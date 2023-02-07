import logging
import re
import typing
from pathlib import Path

import discord
from discord.ext import commands, tasks

import checks
from errors import AudioSourceNotFoundError, AudioUrlError, UserNotInVoiceChannel
from jsons import Jsons
from player import Player
from song import DiscordMessageLinkSong, OnlineSong, Song, YoutubeSong, YtDlpSong

PERMISSIONS = 3263552
json_path = Path(__file__).resolve().parent.joinpath("data.json")


class PlaySound(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot: commands.Bot = bot
        self.players: dict[int, Player] = dict()
        self.delete_disconnected.start()

    async def cog_load(self):
        self.data = Jsons(json_path)
        await self.data.read()

    async def cog_unload(self):
        self.delete_disconnected.cancel()
        await self.data.write()

    def get_song(self, url: str, author: discord.Member) -> Song:
        if not re.match(r"https?://[\w!?/+\-_~;.,*&@#$%()'[\]]+", url):
            raise AudioSourceNotFoundError

        if re.match(r"https://discord\.com/channels/[0-9]+/[0-9]+/[0-9]+", url):
            return DiscordMessageLinkSong(author, url, self.bot)

        if (
            re.match(
                r"https?://(?:www|music|m)\.(?:youtube\.com|youtu\.be)/(?:watch\?v=|embed)?[a-zA-Z0-9_\-]+",  # noqa
                url,
            )
            or re.match(r"https?//soundcloud.com/\w+/\w+", url)
            or re.match(r"https?://youtu.be/[a-zA-Z0-9_\-]+", url)
        ):
            return YoutubeSong(author, url)

        return OnlineSong(author, url)

    def check_url(self, url: str, author: discord.Member):
        if not (
            re.match(
                r"https?://(?:www|music|m)\.youtube\.com/(?:watch\?v=|embed/|shorts/)[a-zA-Z0-9_\-]+",  # noqa
                url,
            )
            or re.match(r"https?://soundcloud.com/[a-zA-Z0-9_\-]+/[a-zA-Z0-9_\-]+", url)
            or re.match(r"https?://youtu.be/[a-zA-Z0-9_\-]+", url)
        ):
            raise AudioUrlError
        # if url is None:
        #     song = DiscordMessageSong(ctx.message)
        # else:
        #     # song = self.get_song(url)
        return YtDlpSong(author, url)

    def get_player(self, guild_id: int):
        player = self.players.get(guild_id)
        return player if player is not None and not player.disconnected else None

    async def get_player_or_make(self, guild_id: int, author: discord.Member):
        if (plyer := self.get_player(guild_id)) is None:
            try:
                plyer = Player(await author.voice.channel.connect(), self.bot.loop)  # type: ignore
                self.players[guild_id] = plyer
            except AttributeError:
                raise UserNotInVoiceChannel
        return plyer

    @commands.hybrid_command(aliases=["p"])
    @commands.guild_only()
    async def play(self, ctx: commands.Context, url: str):
        guild = typing.cast(discord.Guild, ctx.guild)
        author = typing.cast(discord.Member, ctx.author)
        try:
            player = await self.get_player_or_make(guild.id, author)
            song = self.check_url(url, author)
            player.add(song)
        except AudioSourceNotFoundError:
            await ctx.send("ないよ")
        except UserNotInVoiceChannel:
            await ctx.send("VC入れや")

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
            await ctx.send("empty")
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
                    f"`{i + 1}.` [{x}]({x.url}) | `Requested by {x.author}`"  # type: ignore
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
    @checks.is_dj
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

    @commands.hybrid_command(aliases=[])
    @commands.guild_only()
    @checks.is_dj
    async def replay(self, ctx: commands.Context):
        guild = typing.cast(discord.Guild, ctx.guild)
        if (player := self.get_player(guild.id)) is None:
            await ctx.send("おらんで")
            return

        player.replay()
        await ctx.send("replay")

    @commands.hybrid_command(aliases=["pt", "ptop"])
    @commands.guild_only()
    @checks.is_dj
    async def playtop(self, ctx: commands.Context, url: str):
        guild = typing.cast(discord.Guild, ctx.guild)
        author = typing.cast(discord.Member, ctx.author)
        try:
            player = await self.get_player_or_make(guild.id, author)
            song = self.check_url(url, author)
            player.add_first(song)
        except AudioSourceNotFoundError:
            await ctx.send("ないよ")
        except UserNotInVoiceChannel:
            await ctx.send("VC入れや")

    @commands.hybrid_command(aliases=["ps", "pskip", "playnow", "pn"])
    @commands.guild_only()
    @checks.is_dj
    async def playskip(self, ctx: commands.Context, url: str):
        await self.playtop(ctx, url=url)
        guild = typing.cast(discord.Guild, ctx.guild)
        if (player := self.get_player(guild.id)) is None:
            await ctx.send("おらんで")
            return
        player.skip()

    @commands.hybrid_command(aliases=["cl"])
    @commands.guild_only()
    async def clear(self, ctx: commands.Context):
        guild = typing.cast(discord.Guild, ctx.guild)
        if (player := self.get_player(guild.id)) is None:
            await ctx.send("おらんで")
            return

        player.clear()
        await ctx.send("clear")

    @commands.hybrid_command(aliases=["links"])
    async def invite(self, ctx: commands.Context):
        if (client_user := self.bot.user) is None:
            await ctx.send("bot is not running")
            return
        await ctx.send(
            "https://discord.com/api/oauth2/authorize"
            f"?client_id={client_user.id}&permissions={PERMISSIONS}&scope=bot"
        )

    @commands.hybrid_command(aliases=["random", "nt"])
    @commands.guild_only()
    @checks.is_dj
    async def shuffle(self, ctx: commands.Context):
        guild = typing.cast(discord.Guild, ctx.guild)
        if (player := self.get_player(guild.id)) is None:
            await ctx.send("おらんで")
            return
        player.shuffle()
        await ctx.send("shuffling!")

    @commands.hybrid_command(aliases=["m", "mv"])
    @commands.guild_only()
    @checks.is_dj
    async def move(self, ctx: commands.Context, origin: int, target: int):
        guild = typing.cast(discord.Guild, ctx.guild)
        if (player := self.get_player(guild.id)) is None:
            await ctx.send("おらんで")
            return
        try:
            player.move(origin, target)
        except IndexError:
            await ctx.send("位置おかしいぞ")
            return

        await ctx.send("moving!")

    @commands.hybrid_command(aliases=["rm"])
    @commands.guild_only()
    @checks.is_dj
    async def remove(self, ctx: commands.Context, target: int):
        guild = typing.cast(discord.Guild, ctx.guild)
        if (player := self.get_player(guild.id)) is None:
            await ctx.send("おらんで")
            return
        try:
            player.remove(target)
        except IndexError:
            await ctx.send("位置おかしいぞ")
            return

    @commands.hybrid_command(aliases=["rmd", "rd", "drm"])
    @commands.guild_only()
    @checks.is_dj
    async def removedupes(self, ctx: commands.Context):
        guild = typing.cast(discord.Guild, ctx.guild)
        if (player := self.get_player(guild.id)) is None:
            await ctx.send("おらんで")
            return
        in_q = []
        rev_list: list[int] = []
        for i, x in enumerate(player.get_queue()):
            if x.id in in_q:
                rev_list.append(i)
            else:
                in_q.append(x.id)

        for x in reversed(rev_list):
            player.queue.remove_index(x)

        await ctx.send("done")

    @commands.hybrid_command(aliases=["st"])
    @commands.guild_only()
    @checks.is_dj
    async def skipto(self, ctx: commands.Context, target: int):
        guild = typing.cast(discord.Guild, ctx.guild)
        if (player := self.get_player(guild.id)) is None:
            await ctx.send("おらんで")
            return
        if len(player.queue) <= target:
            await ctx.send("なくなる")
            return
        for _ in range(target - 1):
            await player.queue.get()

        player.skip()

        await ctx.send("skipping!")

    @commands.hybrid_group(fallback="show")
    @commands.guild_only()
    @checks.is_mod
    async def settings(self, ctx: commands.Context):
        if ctx.invoked_subcommand is not None:
            return

        guild = typing.cast(discord.Guild, ctx.guild)
        opt = self.data.get_option(guild.id)
        embed = discord.Embed()
        embed.add_field(name="prefix", value=opt["prefix"])

        async def role_value():
            if opt["dj_id"] is None:
                return str(None)

            role = guild.get_role(opt["dj_id"])
            if role is None:
                for x in await guild.fetch_roles():
                    if x.id == opt["dj_id"]:
                        role = x
                        break
                else:
                    return str(None)
            return role.name

        def bool_value(x):
            if x:
                return "enabled"
            else:
                return "disable"

        embed.add_field(name="dj", value=await role_value())
        bools = {
            k: bool_value(v)
            for k, v in opt.items()
            if k in ["announcesongs", "preventduplicates", "displaylists"]
        }
        for k, v in bools.items():
            embed.add_field(name=k, value=v)
        max_len = opt["maxqueuelength"]
        embed.add_field(name="maxqueuelength", value=max_len if max_len > 0 else "None")
        embed.add_field(name="black list", value="")
        await ctx.send(embed=embed)

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
