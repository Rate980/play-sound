import asyncio
import mimetypes
import os
import uuid
from asyncio import subprocess
from collections.abc import Coroutine
from pathlib import Path
from typing import Any, Tuple, cast

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


class Song:
    def __init__(
        self,
        *,
        task: Coroutine[Any, Any, str] | None = None,
        filename: str | None = None,
    ):
        self.task = asyncio.create_task(task) if task is not None else None
        self.filename = filename
        if self.task is None and self.filename is None:
            raise AudioSourceNotFoundError

    async def get_source(self):
        # self.filename = name = await self.task
        if self.filename is None:
            if self.task is None:
                raise AudioSourceNotFoundError
            self.filename = await self.task

        return discord.FFmpegPCMAudio(self.filename)

    def after(self):
        if self.filename is None:
            return

        os.remove(self.filename)


class OnlineSong(Song):
    def __init__(self, url: str) -> None:
        async def task():
            async with aiohttp.ClientSession() as session:
                async with session.get(url) as res:
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

        super().__init__(task=task())


class DiscordMessageSong(Song):
    def __init__(self, mes: discord.Message):
        async def task():
            if not mes.attachments:
                raise AudioSourceNotFoundError

            att = mes.attachments[0]
            _, dot, ext = att.filename.partition(".")
            extension = dot + ext or mimetypes.guess_extension(
                att.content_type if att.content_type is not None else ""
            )
            if extension is None:
                raise AudioExtensionError

            await att.save(name := tempdir.touch(extension))
            return str(name)

        super().__init__(task=task())


class DiscordMessageLinkSong(Song):
    def __init__(self, url: str, client: discord.Client):
        async def task():
            channel_id, message_id = (int(x) for x in url.split("/")[-2::])
            if channel := client.get_channel(channel_id) is None:
                channel = await client.fetch_channel(channel_id)

            if not isinstance(channel, discord.abc.Messageable):
                raise AudioSourceNotFoundError

            message = await channel.fetch_message(message_id)
            super_ = DiscordMessageSong(message)
            if super_.task is None:
                raise AudioSourceNotFoundError
            return await super_.task

        self.task = asyncio.create_task(task())


class YoutubeSong(Song):
    def __init__(self, url: str):
        async def task():
            name = tempdir.touch("")
            cmd = self.make_cmd(name)
            # print(cmd)
            cmd_dl = [*cmd, url]
            # print(cmd_dl)
            cmd_get_name = [*cmd, "--get-filename", url]
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

        super().__init__(task=task())

    @staticmethod
    def make_cmd(filename: Path):
        return ["youtube-dl", "-f", "bestaudio", "-o", f"{filename}.%(ext)s"]


if __name__ == "__main__":

    async def main():
        a = YoutubeSong("https://soundcloud.com/djgdnkk/tintin")
        s = await a.get_source()
        print(s)

    asyncio.run(main())
