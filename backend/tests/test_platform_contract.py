"""플랫폼 식별자 계약 — 프론트엔드와 백엔드가 같은 이름을 쓰는지.

플랫폼 이름은 **네 곳에 각각 적혀 있다.** 코드 경계를 넘어 중복된 값이고,
어긋나도 아무도 알려주지 않는다. 예외도 안 나고 로그도 안 남는다 —
그냥 해당 플랫폼 카드가 화면에서 조용히 사라진다.

    ① backend/models/schemas.py   Platform enum
    ② backend/models/schemas.py   PlatformIds 필드 (JSON 응답 키)
    ③ src/constants/platforms.js  카드 메타데이터의 id
    ④ src/constants/platforms.js  deepLinks 키 (앱 딥링크 빌더)

이 테스트가 존재하는 이유는 앞으로 이 저장소가 **여러 갈래로 나뉘어**
작업되기 때문이다. 매칭 로직을 손보는 쪽이 새 플랫폼을 추가하거나 enum 값을
바꿔도, 프론트를 손보는 쪽은 그 사실을 알 방법이 없다. 계약을 코드로 못박아
두면 `pytest` 한 번에 드러난다.

프론트엔드 파일을 파이썬에서 정규식으로 읽는다. JS 파서를 쓰거나 node 를
호출하지 않는 이유는 백엔드 테스트에 런타임 의존성을 더하지 않기 위해서다.
대신 **파싱이 실패하면 통과가 아니라 실패**하도록 했다 — 계약을 확인할 수
없는 상태를 '이상 없음'으로 보고하면 이 테스트는 있으나 마나다.
"""
from __future__ import annotations

import re
from pathlib import Path

import pytest

from models.schemas import Platform, PlatformIds

# backend/tests/ → backend/ → 저장소 루트
PLATFORMS_JS = Path(__file__).resolve().parents[2] / "src" / "constants" / "platforms.js"

# 플랫폼이 8개보다 훨씬 적게 잡히면 정규식이 파일 구조를 못 따라간 것이다.
# 그 경우 조용히 통과시키지 않고 실패시킨다.
_MIN_PLAUSIBLE = 5


def _js_source() -> str:
    assert PLATFORMS_JS.is_file(), (
        f"프론트엔드 상수 파일을 찾을 수 없다: {PLATFORMS_JS}\n"
        "파일이 옮겨졌다면 이 테스트의 경로를 함께 고쳐야 한다."
    )
    return PLATFORMS_JS.read_text(encoding="utf-8")


def _card_ids(src: str) -> set[str]:
    """`{ id: "spotify", name: … }` 형태에서 id 를 뽑는다."""
    return set(re.findall(r'\bid:\s*"([A-Za-z]+)"', src))


def _deep_link_keys(src: str) -> set[str]:
    """`export const deepLinks = { spotify: { … }, … }` 의 최상위 키."""
    _, sep, tail = src.partition("export const deepLinks")
    assert sep, "platforms.js 에서 `export const deepLinks` 를 찾지 못했다"
    # 들여쓰기 4칸짜리 `이름: {` 만 최상위 키로 본다.
    return set(re.findall(r'^ {4}([A-Za-z]+):\s*\{', tail, re.MULTILINE))


@pytest.fixture(scope="module")
def js() -> str:
    return _js_source()


def test_the_parser_still_understands_the_file(js):
    """정규식이 파일 구조를 따라가고 있는지 먼저 확인한다.

    이 테스트가 없으면, platforms.js 의 서식이 바뀌어 정규식이 아무것도 못
    잡았을 때 아래 비교들이 '빈 집합 == 빈 집합' 으로 통과해 버린다.
    """
    cards, links = _card_ids(js), _deep_link_keys(js)
    assert len(cards) >= _MIN_PLAUSIBLE, (
        f"카드 id 를 {len(cards)}개밖에 못 찾았다 ({cards}). "
        "platforms.js 서식이 바뀌었다면 이 테스트의 정규식을 고칠 것."
    )
    assert len(links) >= _MIN_PLAUSIBLE, (
        f"deepLinks 키를 {len(links)}개밖에 못 찾았다 ({links}). "
        "platforms.js 서식이 바뀌었다면 이 테스트의 정규식을 고칠 것."
    )


def test_response_keys_match_the_enum():
    """PlatformIds 의 필드명이 곧 JSON 응답 키다. enum 과 어긋나면 안 된다."""
    enum_values = {p.value for p in Platform}
    response_keys = set(PlatformIds.model_fields)
    assert response_keys == enum_values, (
        "PlatformIds 필드와 Platform enum 이 어긋났다.\n"
        f"  enum 에만: {sorted(enum_values - response_keys)}\n"
        f"  응답에만: {sorted(response_keys - enum_values)}"
    )


def test_frontend_cards_match_the_enum(js):
    """프론트가 그리는 카드와 백엔드가 채우는 플랫폼이 같아야 한다.

    어긋나면 그 플랫폼은 **조용히 화면에서 사라진다.** 백엔드는 id 를 정상
    반환하는데 프론트에 대응하는 카드가 없으므로, 오류 없이 그냥 안 보인다.
    """
    enum_values = {p.value for p in Platform}
    cards = _card_ids(js)
    assert cards == enum_values, (
        "src/constants/platforms.js 의 카드 id 와 Platform enum 이 어긋났다.\n"
        f"  백엔드에만 (프론트에 카드 없음 → 화면에서 누락): {sorted(enum_values - cards)}\n"
        f"  프론트에만 (백엔드가 절대 안 채움 → 영원히 빈 카드): {sorted(cards - enum_values)}"
    )


def test_frontend_deep_links_cover_every_card(js):
    """카드마다 딥링크 빌더가 있어야 한다.

    빠지면 PlatformCard 의 `deepLinks[platform.id]` 가 undefined 가 되고,
    카드는 보이는데 눌러도 아무 일이 없다.
    """
    cards, links = _card_ids(js), _deep_link_keys(js)
    assert cards == links, (
        "카드 id 와 deepLinks 키가 어긋났다.\n"
        f"  딥링크 없는 카드 (눌러도 반응 없음): {sorted(cards - links)}\n"
        f"  카드 없는 딥링크 (죽은 코드): {sorted(links - cards)}"
    )


def test_all_four_definitions_agree(js):
    """네 곳을 한 번에 비교한다 — 실패 시 어디가 튀는지 바로 보이게."""
    sources = {
        "Platform enum (backend)":      {p.value for p in Platform},
        "PlatformIds 필드 (backend)":   set(PlatformIds.model_fields),
        "카드 id (frontend)":           _card_ids(js),
        "deepLinks 키 (frontend)":      _deep_link_keys(js),
    }
    distinct = {frozenset(v) for v in sources.values()}
    assert len(distinct) == 1, (
        "플랫폼 식별자가 네 곳에서 일치하지 않는다:\n"
        + "\n".join(f"  {name:32} {sorted(vals)}" for name, vals in sources.items())
    )
