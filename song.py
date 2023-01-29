import asyncio
import mimetypes
import os
import typing
import uuid
from dataclasses import dataclass, field
from pathlib import Path

import aiofiles
import aiohttp
import discord
import magic

from errors import AudioSourceNotFoundError


class TempDir:
    def __init__(self) -> None:
        tempdir = Path(__file__).resolve().parent.joinpath("cache")
        if not tempdir.is_dir():
            tempdir.mkdir()
        self.tempdir = tempdir

    def touch(self, extension: str):
        filename = f"{uuid.uuid4()}{extension}"
        res = self.tempdir.joinpath(filename)
        res.touch()
        return res


tempdir = TempDir()


@dataclass
class Song:
    task: asyncio.Task[str] | None = field(default=None)
    filename: str | None = field(default=None)

    async def get_source(self):
        # self.filename = name = await self.task
        if self.filename is None:
            if self.task is None:
                raise AudioSourceNotFoundError
            self.filename = await self.task

        return discord.FFmpegPCMAudio(self.filename)

    def after(self):
        pass


class OnlineSong(Song):
    def __init__(self, url: str) -> None:
        async def task():
            async with aiohttp.ClientSession() as session:
                async with session.get(url) as res:
                    mime = res.headers.get("content-type")
                    data = await res.read()
                    if mime is None:
                        mime = typing.cast(str, magic.from_buffer(data))

                    extension = mimetypes.guess_extension(mime, strict=False)
                    if extension is None:
                        extension = ""
                    file = tempdir.touch(extension)
                    async with aiofiles.open(file, "wb") as f:
                        await f.write(data)

            return str(file)

        super().__init__(asyncio.create_task(task()))

    def after(self):
        if self.filename is None:
            return

        os.remove(self.filename)
