import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import TypedDict

import aiofiles


class Options(TypedDict):
    prefix: str | None
    dj_id: int | None
    blacklist: list[int]
    announcesongs: bool
    preventduplicates: bool
    maxqueuelength: int
    displaylists: bool


@dataclass
class Jsons:
    data: dict[str, Options] = field(default_factory=dict, init=False)
    file: Path

    async def read(self):
        if not self.file.is_file():
            self.data = {}
        async with aiofiles.open(self.file) as f:
            self.data = json.loads(await f.read())

    async def write(self):
        context = json.dumps(self.data)
        async with aiofiles.open("data.json", "w") as f:
            await f.write(context)

    def get_option(self, guild_id: int) -> Options:
        data = self.data.get(str(guild_id))
        if data is not None:
            return data
        data = Options(
            prefix=None,
            dj_id=None,
            blacklist=[],
            announcesongs=False,
            preventduplicates=False,
            maxqueuelength=0,
            displaylists=False,
        )
        self.data[str(guild_id)] = data
        return data
