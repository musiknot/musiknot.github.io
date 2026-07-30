"""`/parse` 요청을 외부 서비스와 남용으로부터 보호하는 작은 인메모리 도구.

단일 uvicorn 프로세스에서 동작하는 현재 배포 형태에 맞춘다. 프로세스 재시작 때
캐시와 제한 상태가 사라지는 것은 의도적이다. 워커를 여러 개로 늘리거나 서버를
여러 대로 나누는 때에는 Redis 같은 공유 저장소로 옮겨야 한다.
"""
from __future__ import annotations

import asyncio
import copy
import time
from collections import OrderedDict, deque
from collections.abc import Awaitable, Callable
from typing import TypeVar


T = TypeVar("T")


class AsyncTTLCache:
    """TTL/LRU 캐시와 같은 키의 진행 중 요청 합치기(single-flight).

    `/parse`는 한 번에 여러 외부 서비스를 호출한다. 같은 링크가 동시에 들어오면
    결과를 기다리는 요청들이 한 작업을 공유해야 업스트림 호출이 중복되지 않는다.
    성공한 값만 저장하고, 예외·타임아웃은 절대 캐시하지 않는다.
    """

    def __init__(self, *, ttl_seconds: float, max_entries: int,
                 clock: Callable[[], float] = time.monotonic):
        self._ttl_seconds = ttl_seconds
        self._max_entries = max_entries
        self._clock = clock
        self._values: OrderedDict[str, tuple[float, T]] = OrderedDict()
        self._inflight: dict[str, asyncio.Task[T]] = {}
        self._lock = asyncio.Lock()

    async def get_or_create(self, key: str, factory: Callable[[], Awaitable[T]]) -> T:
        """캐시값 또는 단 하나의 새 작업 결과를 돌려준다."""
        async with self._lock:
            now = self._clock()
            self._discard_expired(now)
            cached = self._values.get(key)
            if cached is not None:
                self._values.move_to_end(key)
                return copy.deepcopy(cached[1])

            task = self._inflight.get(key)
            if task is None:
                task = asyncio.create_task(self._fill(key, factory))
                self._inflight[key] = task

        # 호출자가 연결을 끊거나 자신의 대기를 취소해도, 다른 동시 요청과
        # 공유 중인 실제 작업까지 취소하지 않는다.
        return copy.deepcopy(await asyncio.shield(task))

    async def _fill(self, key: str, factory: Callable[[], Awaitable[T]]) -> T:
        try:
            value = await factory()
        except BaseException:
            raise
        else:
            async with self._lock:
                now = self._clock()
                self._discard_expired(now)
                self._values[key] = (now + self._ttl_seconds, copy.deepcopy(value))
                self._values.move_to_end(key)
                while len(self._values) > self._max_entries:
                    self._values.popitem(last=False)
            return value
        finally:
            async with self._lock:
                self._inflight.pop(key, None)

    def _discard_expired(self, now: float) -> None:
        expired = [key for key, (deadline, _) in self._values.items() if deadline <= now]
        for key in expired:
            del self._values[key]


class SlidingWindowRateLimiter:
    """키별 슬라이딩 윈도우 요청 제한.

    외부 프록시나 Redis를 요구하지 않아 현재 단일 프로세스 API에서도 즉시 쓸 수
    있다. 이는 업스트림 보호용 1차 방어이며, 분산 배포 시에는 공유 저장소 기반
    제한으로 교체해야 한다.
    """

    def __init__(self, *, limit: int, window_seconds: float,
                 clock: Callable[[], float] = time.monotonic):
        self._limit = limit
        self._window_seconds = window_seconds
        self._clock = clock
        self._hits: dict[str, deque[float]] = {}
        self._lock = asyncio.Lock()

    async def allow(self, key: str) -> tuple[bool, int]:
        """허용 여부와 거절 시 Retry-After 초를 돌려준다."""
        now = self._clock()
        async with self._lock:
            hits = self._hits.setdefault(key, deque())
            boundary = now - self._window_seconds
            while hits and hits[0] <= boundary:
                hits.popleft()

            if len(hits) >= self._limit:
                retry_after = max(1, int(hits[0] + self._window_seconds - now) + 1)
                return False, retry_after

            hits.append(now)
            return True, 0
