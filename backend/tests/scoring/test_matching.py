"""곡 매칭 회귀 테스트 — 검증된 정답 41곡.

이 테스트가 지키는 것은 다음 사실이다.

  한때 한국어·일본어 곡이 **하나도** 매칭되지 않았다 (한국곡 0/10, 일본곡 0/7).
  원인은 검색이 아니라 채점이었다. iTunes 에 `country` 를 안 보내면 US
  스토어프론트로 가고, US 는 한국어 제목을 영어로 번역해 돌려준다. 그걸
  한국어 입력과 문자열 비교하니 유사도가 0 이 됐다.

      calc_score('물론', '허각', 'With you', 'Huh Gak') = 0.000   ← 정답인데 0점

  임계값을 낮추는 건 해법이 아니다. 원어 제목을 그대로 쓴 노래방 커버가 점수를
  더 받기 때문에 오히려 나빠진다. 그래서 번역을 검증하는 대신, 입력의 문자체계에
  맞는 스토어프론트에 질의해 **애초에 번역이 생기지 않게** 했다.

정답(expected_apple_id)은 추측이 아니다. 전부 `lookup?id=…&country=KR|JP` 로
원어 표기를 확인해 넣었고, 그 근거가 각 행의 `verified` 필드에 들어 있다.

주의: 이 벤치마크는 포화 상태다. 스코어러를 통째로 빼고 '스토어프론트 라우팅 +
아티스트 우선 질의 + 1위 채택'만 해도 40/41 이 나온다. 즉 이 데이터가 검증하는
것은 주로 **검색 경로**이고, scoring.py 의 임계값들은 여기서 반증되지 않는다.
임계값을 바꾸려면 새 데이터가 필요하다.
"""
from __future__ import annotations

import asyncio
import json
from collections import Counter
from pathlib import Path

import pytest

from services import itunes
from tests.scoring.fake_itunes import FakeHttpx

BENCH_PATH = Path(__file__).with_name("bench_data.json")
SONGS = json.loads(BENCH_PATH.read_text(encoding="utf-8"))


@pytest.fixture(autouse=True)
def _offline(monkeypatch):
    """실제 itunes.py 를 녹화된 응답 위에서 돌린다. 네트워크 없음."""
    FakeHttpx.load()
    FakeHttpx.reset()
    monkeypatch.setattr(itunes, "httpx", FakeHttpx)


def _run(song: dict) -> str | None:
    tracks = asyncio.run(itunes.search(song["native_title"], song["native_artist"]))
    return tracks[0].track_id if tracks else None


@pytest.mark.parametrize("song", SONGS, ids=[s["id"] for s in SONGS])
def test_song_resolves_to_expected_apple_id(song):
    got = _run(song)
    expected = song["expected_apple_id"]
    alts = song.get("alt_apple_ids") or []

    # alt 는 '같은 녹음의 다른 앨범 프레싱'이다. 리믹스·라이브·커버는 포함되지 않는다.
    assert got in {expected, *alts}, (
        f"{song['native_title']} / {song['native_artist']}\n"
        f"  기대: {expected} (또는 {alts})\n"
        f"  실제: {got}\n"
        f"  근거: {song.get('verified', '')}"
    )


def test_no_false_positives_overall():
    """오답은 무응답보다 나쁘다 — 사용자가 눌러서 엉뚱한 곡으로 가기 때문이다.

    그래서 이 둘을 분리해서 센다. 채점 기준을 바꿀 때 무응답이 늘어나는 건
    감수할 수 있지만 오답이 늘어나는 건 안 된다.
    """
    wrong, missed = [], []
    for song in SONGS:
        got = _run(song)
        ok = {song["expected_apple_id"], *(song.get("alt_apple_ids") or [])}
        if got is None:
            missed.append(song["id"])
        elif got not in ok:
            wrong.append((song["id"], got))

    assert not wrong, f"오답 {len(wrong)}건: {wrong}"
    assert not missed, f"무응답 {len(missed)}건: {missed}"


def test_every_category_is_covered():
    """카테고리가 통째로 사라지면 벤치마크가 조용히 약해진다."""
    counts = Counter(s["category"] for s in SONGS)
    for category in ("kr_translated", "kr_native_only", "jp_translated",
                     "mixed_ascii", "en_control", "tricky"):
        assert counts[category] >= 5, f"{category} 가 {counts[category]}곡뿐"


def test_runs_entirely_offline():
    """녹화되지 않은 요청이 있으면 FixtureMiss 로 시끄럽게 실패해야 한다.

    조용히 네트워크로 나가면 테스트가 느려지고, 비결정적이 되고, iTunes 의
    분당 20회 제한에 걸린다.
    """
    _run(SONGS[0])
    assert FakeHttpx.requests, "요청이 한 건도 기록되지 않았다 — 모킹이 안 걸렸다"
    assert all(r.startswith("https://itunes.apple.com/") for r in FakeHttpx.requests)
