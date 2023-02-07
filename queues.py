import asyncio
from collections import abc, deque
from random import shuffle
from typing import Generic, TypeVar

T = TypeVar("T")


class Queue(Generic[T]):
    def __init__(self):
        self._getters: deque[asyncio.Future] = deque()
        self._init()

    def _init(self):
        self._queue: deque[T] = deque()

    def get_nowait(self):
        return self._queue.popleft()

    def put(self, item):
        self._queue.append(item)
        self._wakeup_next()

    def put_first(self, item):
        self._queue.appendleft(item)
        self._wakeup_next()

    def insert(self, index, item):
        self._queue.insert(index, item)
        self._wakeup_next()

    def move(self, old_index: int, target_index: int):
        tmp = self._queue[old_index]
        del self._queue[old_index]
        self._queue.insert(target_index, tmp)

    def remove_index(self, i: int):
        del self._queue[i]

    def _wakeup_next(self):
        while self._getters:
            waiter = self._getters.popleft()
            if not waiter.done():
                waiter.set_result(None)
                break

    def shuffle(self):
        shuffle(self._queue)

    def clear(self):
        self._queue.clear()

    def __len__(self):
        return len(self._queue)

    def __iter__(self):
        iter(self._queue)

    def empty(self):
        return not self._queue

    async def get(self):
        while self.empty():
            getter = asyncio.get_running_loop().create_future()
            self._getters.append(getter)
            await getter
        return self.get_nowait()
