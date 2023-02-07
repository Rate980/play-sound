import asyncio
from cmath import rect
from dataclasses import dataclass, field

import discord

from errors import VoiceClientDisconnectedError
from queues import Queue
from song import Song


@dataclass
class Player:
    queue: Queue[Song] = field(default_factory=Queue, init=False)
    voice_client: discord.VoiceClient
    loop: asyncio.AbstractEventLoop
    disconnected: bool = field(default=False, init=False)
    loop_queue: bool = field(default=False, init=False)
    loop_song: bool = field(default=False, init=False)

    def __post_init__(self):
        asyncio.run_coroutine_threadsafe(self.play(), self.loop)

    def check(self):
        if self.disconnected:
            raise VoiceClientDisconnectedError

    async def loop_play(self, song: Song):
        def after(_):
            if not self.loop_song:
                asyncio.run_coroutine_threadsafe(self.play(), self.loop)
                if self.loop_queue:
                    self.queue.put(song)
                    return
                song.after()
                return
            asyncio.run_coroutine_threadsafe(self.loop_play(song), self.loop)

        self.voice_client.play(await song.get_source(), after=after)

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
            if self.loop_queue:

                return
            asyncio.run_coroutine_threadsafe(self.play(), self.loop)
            song.after()

        self.voice_client.play(
            source,
            after=after,
        )

    def add(self, song: Song):
        self.check()
        self.queue.put(song)

    def skip(self):
        self.voice_client.stop()

    def add_first(self, song: Song):
        self.queue.put_first(song)

    def pause(self):
        self.voice_client.pause()

    def resume(self):
        self.voice_client.resume()

    async def disconnect(self) -> None:
        self.check()
        await self.voice_client.disconnect()
        self.disconnected = True
