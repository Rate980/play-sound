import abc
import asyncio
import json
import sys
from dataclasses import dataclass

url = "https://www.youtube.com/shorts/ATYqXMHf1K0"


async def task():
    cmd = [
        "yt-dlp",
        "-o",
        "%(id)s.%(ext)s",
        "-j",
        "--no-simulate",
        url,
    ]

    res = await asyncio.create_subprocess_exec(
        *cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
    )
    (stdout, stderr) = await res.communicate()
    if stderr == b"":
        print(stderr.decode("ascii"), file=sys.stderr)

    json_str = stdout.decode("ascii").splitlines()[0]

    data = json.loads(json_str)
    id = data["id"]
    title = data["title"]
    print(title)
    return f'{id}.{data["ext"]}'


@dataclass
class Meta(metaclass=abc.ABCMeta):
    def __post_init__(self):
        self.task = self.make_task()

    async def get(self):
        return await self.task

    @abc.abstractclassmethod
    def make_task(self) -> asyncio.Task[str]:
        raise NotImplementedError


@dataclass
class A(Meta):
    def make_task(self):
        return asyncio.create_task(task())


async def main():
    a = A()
    print(await a.get())


asyncio.run(main())
