"""외부 호출을 하기 전에 `/parse`를 보호하는 인메모리 도구의 회귀 테스트."""
from __future__ import annotations

import asyncio

import pytest

from core.resilience import AsyncTTLCache, SlidingWindowRateLimiter


def test_cache_reuses_a_successful_value_and_returns_a_copy():
    async def run():
        calls = 0
        cache = AsyncTTLCache(ttl_seconds=60, max_entries=10)

        async def fetch():
            nonlocal calls
            calls += 1
            return {"platforms": {"melon": "1"}}

        first = await cache.get_or_create("song", fetch)
        first["platforms"]["melon"] = "mutated"
        second = await cache.get_or_create("song", fetch)
        return calls, second

    calls, second = asyncio.run(run())
    assert calls == 1
    assert second == {"platforms": {"melon": "1"}}


def test_concurrent_requests_share_one_inflight_fetch():
    async def run():
        calls = 0
        started = asyncio.Event()
        release = asyncio.Event()
        cache = AsyncTTLCache(ttl_seconds=60, max_entries=10)

        async def fetch():
            nonlocal calls
            calls += 1
            started.set()
            await release.wait()
            return "done"

        first = asyncio.create_task(cache.get_or_create("same-song", fetch))
        await started.wait()
        second = asyncio.create_task(cache.get_or_create("same-song", fetch))
        await asyncio.sleep(0)
        release.set()
        return calls, await first, await second

    calls, first, second = asyncio.run(run())
    assert (calls, first, second) == (1, "done", "done")


def test_failed_fetch_is_not_cached():
    async def run():
        calls = 0
        cache = AsyncTTLCache(ttl_seconds=60, max_entries=10)

        async def fails():
            nonlocal calls
            calls += 1
            raise RuntimeError("upstream failed")

        with pytest.raises(RuntimeError):
            await cache.get_or_create("song", fails)
        with pytest.raises(RuntimeError):
            await cache.get_or_create("song", fails)
        return calls

    assert asyncio.run(run()) == 2


def test_rate_limiter_returns_retry_after_and_recovers_after_window():
    now = [100.0]
    limiter = SlidingWindowRateLimiter(limit=2, window_seconds=10, clock=lambda: now[0])

    async def run():
        first = await limiter.allow("client")
        second = await limiter.allow("client")
        blocked = await limiter.allow("client")
        now[0] += 10
        recovered = await limiter.allow("client")
        return first, second, blocked, recovered

    first, second, blocked, recovered = asyncio.run(run())
    assert first == (True, 0)
    assert second == (True, 0)
    assert blocked == (False, 11)
    assert recovered == (True, 0)
