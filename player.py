import asyncio
from dataclasses import dataclass, field

import discord

from errors import VoiceClientDisconnectedError
from song import Song


@dataclass
class Player:
    queue: asyncio.Queue[Song] = field(default_factory=asyncio.Queue, init=False)
    voice_client: discord.VoiceClient
    loop: asyncio.AbstractEventLoop
    disconnected: bool = field(default=False, init=False)

    def __post_init__(self):
        asyncio.run_coroutine_threadsafe(self.play(), self.loop)

    def check(self):
        if self.disconnected:
            raise VoiceClientDisconnectedError

    async def play(self):
        self.check()
        # song = await asyncio.wait_for(self.queue.get(), 1)
        try:
            song = await asyncio.wait_for(self.queue.get(), 1)
            # song = await self.queue.get()
        except asyncio.TimeoutError:
            await self.disconnect()
            return
        source = await song.get_source()

        def after(_):
            asyncio.run_coroutine_threadsafe(self.play(), self.loop)
            song.after()

        self.voice_client.play(
            source,
            after=after,
        )

    async def add(self, song: Song):
        self.check()
        await self.queue.put(song)

    async def disconnect(self) -> None:
        self.check()
        await self.voice_client.disconnect()
        self.disconnected = True
