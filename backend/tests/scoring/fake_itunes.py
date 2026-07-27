"""녹화해 둔 iTunes 응답으로 httpx 를 대체한다.

테스트가 실제 `services/itunes.py` 를 그대로 채점할 수 있게 하는 장치다.
사본을 만들어 채점하면 사본이 시간이 지나며 실제 코드와 어긋나고, 그러면
테스트가 통과해도 아무것도 보장하지 못한다.

네트워크를 쓰지 않으므로
  - 결정적이다. 같은 입력이면 언제 돌려도 같은 결과다.
  - 빠르다.
  - iTunes 의 분당 약 20회 제한에 걸리지 않는다.
  - 코드를 고치기 전/후를 **같은 데이터**로 비교할 수 있다.
"""
from __future__ import annotations

import json
import urllib.parse
from pathlib import Path

import httpx

FIXTURES_PATH = Path(__file__).with_name("itunes_fixtures.json")


class FixtureMiss(KeyError):
    """녹화되지 않은 요청. 조용히 넘기지 않고 시끄럽게 실패한다.

    httpx.HTTPError 를 상속하지 않는 것이 중요하다 — itunes.py 는 HTTPError 를
    잡아서 빈 리스트로 흡수하므로, 그걸 상속하면 픽스처 누락이 '검색 결과 없음'
    으로 둔갑해 테스트가 조용히 잘못된 것을 측정하게 된다.
    """


def _canonical(url: str, params: dict | None) -> str:
    """파라미터를 키 순으로 정렬한 URL. 녹화 시점과 같은 규칙이어야 한다.

    services/itunes.py 는 파라미터를 dict 리터럴 순서로 넘기는데, 그 순서가
    바뀌어도 같은 캐시 항목을 찾아야 하므로 여기서 정규화한다.
    """
    clean = {k: v for k, v in (params or {}).items() if v is not None and v != ""}
    qs = urllib.parse.urlencode(sorted(clean.items()), quote_via=urllib.parse.quote)
    return f"{url}?{qs}" if qs else url


class _Response:
    def __init__(self, body: dict) -> None:
        self._body = body

    def raise_for_status(self) -> None:
        return None

    def json(self) -> dict:
        return self._body


class _Client:
    """httpx.AsyncClient 대역. itunes.py 가 쓰는 표면만 구현한다."""

    def __init__(self, *args, **kwargs) -> None:
        self.calls: list[str] = []

    async def __aenter__(self) -> "_Client":
        return self

    async def __aexit__(self, *exc) -> bool:
        return False

    async def get(self, url: str, params: dict | None = None) -> _Response:
        full = _canonical(url, params)
        FakeHttpx.requests.append(full)
        try:
            return _Response(FakeHttpx.fixtures[full])
        except KeyError:
            raise FixtureMiss(
                f"녹화되지 않은 요청: {full}\n"
                f"픽스처를 갱신하려면 {FIXTURES_PATH.name} 에 이 URL 의 응답을 추가할 것."
            ) from None


class FakeHttpx:
    """`services.itunes.httpx` 자리에 끼워 넣는 모듈 대역."""

    fixtures: dict[str, dict] = {}
    requests: list[str] = []

    AsyncClient = _Client
    HTTPError = httpx.HTTPError      # itunes.py 의 except 절이 참조한다

    @classmethod
    def load(cls) -> None:
        if not cls.fixtures:
            cls.fixtures = json.loads(FIXTURES_PATH.read_text(encoding="utf-8"))

    @classmethod
    def reset(cls) -> None:
        cls.requests = []
