"""녹화해 둔 벅스 페이지로 httpx 를 대체한다.

`tests/scoring/fake_itunes.py` 와 같은 규약이다. 목적도 같다 — 사본이 아니라
**실제 `services/bugs.py` 를 그대로** 돌려야 테스트가 무언가를 보장한다.

벅스는 HTML 을 파싱하는 대상이라 iTunes 와 다른 점이 두 가지 있다.

1. **페이지를 통째로 저장한다.** 필요한 부분만 잘라내면 픽스처가 작아지지만,
   바로 그 방식이 이번 버그를 숨긴다. 예전 코드의 `p.artist a` 는 곡 정보가
   아니라 페이지 한참 아래 뮤직비디오 목록의 라벨을 잡고 있었다. 잘라낸
   픽스처였다면 "셀렉터가 엉뚱한 데를 잡는다" 를 영원히 못 잡는다.
   전체 보존 대신 gzip 으로 줄인다 (808KB → 184KB).

2. **없는 곡은 302 다.** 벅스는 존재하지 않는 트랙을 404 가 아니라 302 로
   /noMusic 에 보낸다. 이 대역은 그 상태 코드를 그대로 재현한다 —
   `raise_for_status()` 가 여기서 걸리는 것이 삭제된 곡을 걸러내는 유일한
   방어선이기 때문이다.
"""
from __future__ import annotations

import gzip
from pathlib import Path

import httpx

FIXTURES_DIR = Path(__file__).with_name("bugs_fixtures")


class FixtureMiss(KeyError):
    """녹화되지 않은 요청. 조용히 넘기지 않고 시끄럽게 실패한다.

    `httpx.HTTPError` 를 상속하지 않는 것이 중요하다 — bugs.py 는 HTTPError 를
    잡아서 None / 빈 리스트로 흡수하므로, 그걸 상속하면 픽스처 누락이 '곡 없음'
    으로 둔갑해 테스트가 조용히 잘못된 것을 측정하게 된다.
    """


def _read(name: str) -> str:
    path = FIXTURES_DIR / f"{name}.html.gz"
    if not path.exists():
        raise FixtureMiss(
            f"녹화되지 않은 픽스처: {path.name}\n"
            f"{FIXTURES_DIR}/ 에 gzip 으로 추가하고 index.json 에 이유를 적을 것."
        )
    return gzip.open(path, "rt", encoding="utf-8").read()


class _Response:
    def __init__(self, text: str, status_code: int = 200) -> None:
        self.text = text
        self.status_code = status_code

    def raise_for_status(self) -> None:
        # httpx 는 2xx 가 아니면 전부 예외다. 3xx 도 포함된다 — 벅스의 '없는 곡'
        # 이 정확히 이 경로로 걸러진다.
        if not 200 <= self.status_code < 300:
            raise httpx.HTTPStatusError(
                f"HTTP {self.status_code}", request=None, response=None
            )


class _Client:
    """httpx.AsyncClient 대역. bugs.py 가 쓰는 표면만 구현한다."""

    def __init__(self, *args, **kwargs) -> None:
        # follow_redirects 를 켜면 없는 곡이 /noMusic 페이지(200)로 이어져
        # 가짜 Track 이 만들어진다. 켜는 순간 테스트가 실패해야 한다.
        FakeHttpx.follow_redirects = kwargs.get("follow_redirects", False)

    async def __aenter__(self) -> "_Client":
        return self

    async def __aexit__(self, *exc) -> bool:
        return False

    async def get(self, url: str, params: dict | None = None) -> _Response:
        FakeHttpx.requests.append(url)

        if "/search/track" in url:
            return _Response(_read("search_frozen"))

        track_id = url.rstrip("/").rsplit("/", 1)[-1]
        if track_id in FakeHttpx.overrides:
            return _Response(FakeHttpx.overrides[track_id])
        if track_id == NO_SUCH_TRACK:
            # 벅스의 실제 동작: 302 + 빈 본문. 404 가 아니다.
            return _Response("", status_code=302)
        return _Response(_read(f"track_{track_id}"))


#: 벅스에 존재하지 않는 트랙 ID (실측: 302 → https://music.bugs.co.kr/noMusic)
NO_SUCH_TRACK = "999999999"


class FakeHttpx:
    """`services.bugs.httpx` 자리에 끼워 넣는 모듈 대역."""

    requests: list[str] = []
    follow_redirects: bool = False

    #: 트랙 ID → 이 HTML 을 200 으로 내려준다.
    #:
    #: 녹화만으로는 태울 수 없는 경로가 있어서 둔다. 예를 들어 앨범아트
    #: 플레이스홀더 가드는 '제목·아티스트는 멀쩡한데 og:image 만 로고' 인
    #: 페이지에서만 발동하는데, 그런 곡을 벅스에서 찾아 녹화하기 어렵다.
    #: 넣는 값은 반드시 **실제로 관측된 조각**이어야 한다 — 지어내면 그
    #: 테스트는 현실이 아니라 상상을 검증하게 된다.
    overrides: dict[str, str] = {}

    AsyncClient = _Client
    HTTPError = httpx.HTTPError            # bugs.py 의 except 절이 참조한다
    HTTPStatusError = httpx.HTTPStatusError

    @classmethod
    def reset(cls) -> None:
        cls.requests = []
        cls.follow_redirects = False
        cls.overrides = {}
