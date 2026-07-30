"""iTunes 가 429 를 줄 때 **기다리지 않고 곧바로 포기하는지**.

한때 `Retry-After` 를 존중해 한 번 재시도했다. 좋아 보였지만 회귀였다.

429 면 `_get` 이 빈 리스트를 돌려주는데, 그러면 `search()` 의 조기 반환 조건이
성립하지 않아 스토어프론트를 **전부** 돈다. 즉 429 일 때 호출 횟수와 대기 시간이
최소가 아니라 **최대**가 된다. 한국어 곡이면 `search()` 한 번이 29초씩 두 번이고,
`/parse` 는 `search()` 를 두 번(`_enrich_track` + `fetch_apple`) 부르니 116초.
`PARSE_TIMEOUT_SECONDS=40` 에 걸려 504 가 됐다.

재시도가 없던 시절에는 같은 상황에서 애플 칸만 비우고 **200** 을 냈다. 그리고
실패는 캐시되지 않으므로, 504 로 죽은 요청을 사용자가 다시 누르면 멜론·벅스·FLO
를 **또** 긁는다. 업스트림을 보호하려던 코드가 스크래핑을 늘린 셈이다.

그래서 지금은 429 도 다른 오류와 똑같이 다룬다. 이 테스트는 그 결정을 고정한다.
"""
from __future__ import annotations

import asyncio

import httpx

from services import itunes


class _Response:
    def __init__(self, status_code: int, body: dict | None = None,
                 headers: dict[str, str] | None = None):
        self.status_code = status_code
        self._body = body or {}
        self.headers = headers or {}

    def raise_for_status(self):
        if self.status_code >= 400:
            raise httpx.HTTPStatusError("error", request=None, response=None)

    def json(self):
        return self._body


class _Client:
    responses: list[_Response] = []
    calls = 0

    def __init__(self, *args, **kwargs):
        pass

    async def __aenter__(self):
        return self

    async def __aexit__(self, *exc):
        return False

    async def get(self, url, params=None):
        self.__class__.calls += 1
        return self.__class__.responses.pop(0)


class _Httpx:
    AsyncClient = _Client
    HTTPError = httpx.HTTPError


def _run(coro):
    return asyncio.run(coro)


def test_429_gives_up_immediately(monkeypatch):
    """429 를 받으면 재요청하지 않는다."""
    _Client.calls = 0
    _Client.responses = [
        _Response(429, headers={"Retry-After": "29"}),
        # 두 번째 응답은 준비해 두되 **쓰이면 안 된다.**
        _Response(200, {"results": [{"trackId": 1}]}),
    ]
    monkeypatch.setattr(itunes, "httpx", _Httpx)

    assert _run(itunes._get("https://example.test", {"term": "song"})) == []
    assert _Client.calls == 1, "429 후 재요청했다 — 재시도가 되살아났다"


def test_429_does_not_sleep(monkeypatch):
    """Retry-After 를 보고 잠들지 않는다.

    대기가 되살아나면 스토어프론트 순회와 곱해져 40초 데드라인을 넘긴다.
    """
    _Client.calls = 0
    _Client.responses = [_Response(429, headers={"Retry-After": "29"})]
    monkeypatch.setattr(itunes, "httpx", _Httpx)

    slept: list[float] = []

    async def spy(seconds):
        slept.append(seconds)

    monkeypatch.setattr(asyncio, "sleep", spy)

    assert _run(itunes._get("https://example.test", {})) == []
    assert slept == [], f"429 때문에 {slept} 초를 잤다"


def test_a_korean_search_stays_cheap_when_rate_limited(monkeypatch):
    """한국어 곡이 429 를 만나도 호출은 스토어프론트 수만큼이다.

    회귀했을 때 여기가 4회로 늘어난다 (KR, KR, US, US).
    """
    _Client.calls = 0
    _Client.responses = [_Response(429, headers={"Retry-After": "29"}) for _ in range(8)]
    monkeypatch.setattr(itunes, "httpx", _Httpx)

    slept: list[float] = []

    async def spy(seconds):
        slept.append(seconds)

    monkeypatch.setattr(asyncio, "sleep", spy)

    assert _run(itunes.search("밤편지", "아이유")) == []
    assert _Client.calls == 2, f"KR·US 두 번이어야 하는데 {_Client.calls}회 호출했다"
    assert slept == []


def test_other_errors_still_return_empty(monkeypatch):
    """429 만 특별 취급하지 않는다 — 5xx 도 똑같이 빈 리스트다."""
    _Client.calls = 0
    _Client.responses = [_Response(500)]
    monkeypatch.setattr(itunes, "httpx", _Httpx)

    assert _run(itunes._get("https://example.test", {})) == []
    assert _Client.calls == 1
