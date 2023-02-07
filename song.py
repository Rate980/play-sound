import asyncio
import mimetypes
import os
import uuid
from abc import ABCMeta, abstractmethod
from asyncio import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import cast, final

import aiofiles
import aiohttp
import discord
import magic

from errors import AudioExtensionError, AudioSourceNotFoundError


class TempDir:
    def __init__(self) -> None:
        tempdir = Path(__file__).resolve().parent.joinpath("cache")
        if not tempdir.is_dir():
            tempdir.mkdir()
        self.tempdir = tempdir

    def touch(self, extension: str):
        filename = f"{uuid.uuid4()}{extension}"
        res = self.tempdir.joinpath(filename)
        # res.touch()
        return res


tempdir = TempDir()


class Song(metaclass=ABCMeta):
    def __init__(self):
        self.__post_init__()

    @final
    def __post_init__(self):
        self.task = self.create_task()
        self.filename: str | None = None

    async def get_source(self):
        # self.filename = name = await self.task
        if self.filename is None:
            self.filename = await self.task

        return discord.FFmpegPCMAudio(self.filename)

    def after(self):
        if self.filename is None:
            return

        os.remove(self.filename)

    @abstractmethod
    def create_task(self) -> asyncio.Task[str]:
        raise NotImplementedError


@dataclass
class OnlineSong(Song):
    url: str

    def create_task(self):
        async def task():
            async with aiohttp.ClientSession() as session:
                async with session.get(self.url) as res:
                    mime = res.headers.get("content-type")
                    data = await res.read()
                    if mime is None:
                        mime = cast(str, magic.from_buffer(data))

                    extension = mimetypes.guess_extension(mime, strict=False)
                    if extension is None:
                        extension = ""
                    file = tempdir.touch(extension)
                    async with aiofiles.open(file, "wb") as f:
                        await f.write(data)

            return str(file)

        return asyncio.create_task(task())


@dataclass
class DiscordMessageSong(Song):
    mes: discord.Message

    def create_task(self):
        async def task():
            if not self.mes.attachments:
                raise AudioSourceNotFoundError

            att = self.mes.attachments[0]
            _, dot, ext = att.filename.partition(".")
            extension = dot + ext or mimetypes.guess_extension(
                att.content_type if att.content_type is not None else ""
            )
            if extension is None:
                raise AudioExtensionError

            await att.save(name := tempdir.touch(extension))
            return str(name)

        return asyncio.create_task(task())


@dataclass
class DiscordMessageLinkSong(DiscordMessageSong):
    url: str
    client: discord.Client
    mes: discord.Message | None = field(default=None, init=False)

    def create_task(self):
        async def task():
            channel_id, message_id = (int(x) for x in self.url.split("/")[-2::])
            if (channel := self.client.get_channel(channel_id)) is None:
                channel = await self.client.fetch_channel(channel_id)

            if not isinstance(channel, discord.abc.Messageable):
                raise AudioSourceNotFoundError

            self.mes = await channel.fetch_message(message_id)
            return await super().create_task()

        return asyncio.create_task(task())


@dataclass
class YoutubeSong(Song):
    url: str

    def create_task(self):
        async def task():
            name = tempdir.touch("")
            cmd = self.make_cmd(name)
            # print(cmd)
            cmd_dl = [*cmd, self.url]
            # print(cmd_dl)
            cmd_get_name = [*cmd, "--get-filename", self.url]
            dl = asyncio.create_task(
                asyncio.create_subprocess_exec(
                    *cmd_dl, stdout=subprocess.PIPE, stderr=subprocess.PIPE
                )
            )
            get_name = asyncio.create_task(
                asyncio.create_subprocess_exec(
                    *cmd_get_name, stdout=subprocess.PIPE, stderr=subprocess.PIPE
                )
            )
            # dl, name = await asyncio.gather(dl, get_name)
            await dl
            name = await get_name
            file_name, _ = await name.communicate()
            # def con(x: Tuple[bytes, bytes]):
            #     a, b = x
            #     return a.decode("utf8"), b.decode("utf_8")

            # res = [
            #     con(await x.communicate()) for x in await asyncio.gather(dl, get_name)
            # ]
            # print(res)

            # return res[1][0]
            # res = await get_name
            # (
            #     stdout,
            #     stderr,
            # ) = await res.communicate()
            # print(stdout, stderr)
            return file_name.decode("ascii")

        return asyncio.create_task(task())

    @staticmethod
    def make_cmd(filename: Path):
        return ["youtube-dl", "-f", "bestaudio", "-o", f"{filename}.%(ext)s"]


if __name__ == "__main__":

    async def main():
        a = YoutubeSong("https://soundcloud.com/djgdnkk/tintin")
        s = await a.get_source()
        print(s)

    asyncio.run(main())
