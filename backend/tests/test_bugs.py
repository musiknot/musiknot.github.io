"""벅스 파싱 회귀.

`lookup_by_id` 는 통째로 고장나 있었다. 페이지는 HTTP 200 인데 셀렉터 네 개 중
세 개가 옛 DOM 을 가리켜 None 을 반환했고, 라우터가 그걸 404 로 바꿨다
(routers/parse.py). 즉 **벅스 링크를 붙여넣으면 곡을 못 찾는다** 였다.

가장 고약했던 건 살아 있어 보이던 하나다. `p.artist a` 는 곡 정보 영역이 아니라
페이지 한참 아래 "이 곡의 영상" 뮤직비디오 목록의 아티스트 라벨을 잡고 있었다.
뮤비 아티스트가 곡 아티스트와 같아서 값이 맞아떨어졌을 뿐이고, 뮤비가 없는
페이지에서는 0개였다 — 픽스처 9곡 중 3곡이 그렇다.

여기 테스트는 그 회귀와, 같은 뿌리에서 나온 두 가지 조용한 실패를 고정한다.
"""
from __future__ import annotations

import asyncio
import re

import pytest

from services import bugs
from tests.fake_bugs import NO_SUCH_TRACK, FakeHttpx

# 픽스처에 녹화된 트랙. index.json 에 각각을 왜 골랐는지 적혀 있다.
IU          = "30598121"     # 정상 경로
FROZEN_OST  = "30492229"     # 아티스트가 <a> 없는 'Various Artists' 평문
GOLDEN      = "125523552"    # 협연 5명
YOUNHA      = "6155092"      # 아티스트명에 슬래시


@pytest.fixture(autouse=True)
def _fake_network(monkeypatch):
    FakeHttpx.reset()
    monkeypatch.setattr(bugs, "httpx", FakeHttpx)


def lookup(track_id: str):
    return asyncio.run(bugs.lookup_by_id(track_id))


def search(title: str, artist: str, limit: int = 50):
    return asyncio.run(bugs.search(title, artist, limit=limit))


# ── lookup_by_id — 기본 동작 ────────────────────────────────────

def test_lookup_returns_a_track():
    t = lookup(IU)
    assert t is not None, "정상적인 곡에서 None 이면 라우터가 404 를 낸다"
    assert t.title  == "밤편지"
    assert t.artist == "아이유(IU)"
    assert t.album  == "밤편지"
    assert t.album_art and t.album_art.startswith("https://")


@pytest.mark.parametrize("track_id", [IU, FROZEN_OST, GOLDEN, YOUNHA])
def test_every_recorded_track_resolves(track_id):
    """녹화된 곡은 하나도 빠짐없이 Track 이 나와야 한다.

    예전 코드는 이 중 FROZEN_OST 와 GOLDEN 에서 None 이었다.
    """
    t = lookup(track_id)
    assert t is not None
    assert t.title and t.artist


# ── 회귀 1: 아티스트에 링크가 없는 곡 ───────────────────────────

def test_artist_without_a_link_is_still_read():
    """'Various Artists' 는 아티스트 페이지가 없어서 <a> 없이 평문으로 온다.

    링크를 요구하면 OST·컴필레이션 곡이 통째로 404 가 된다. 곡을 버릴지 말지는
    파서가 아니라 스코어러가 정할 일이다.
    """
    t = lookup(FROZEN_OST)
    assert t is not None, "아티스트 링크가 없다고 곡을 버리면 안 된다"
    assert t.artist == "Various Artists"
    assert t.title  == "겨울왕국 Let It Go"


def test_search_keeps_rows_whose_artist_has_no_link():
    """같은 결함이 search() 에도 있었다 — 그런 행을 조용히 건너뛰었다."""
    rows = search("겨울왕국 Let It Go", "Various Artists")
    plain = [r for r in rows if r.artist in {"Various Artists", "Unknown", "Cover Artist"}]
    assert plain, "링크 없는 아티스트 행이 전부 버려지고 있다"


# ── 회귀 2: 협연곡의 대표 아티스트 ──────────────────────────────

def test_collaboration_uses_the_primary_artist():
    """협연곡에서 sc:artist_nm 은 대표가 아니라 앨범 크레딧을 준다.

    'Golden' 의 대표는 HUNTR/X 인데 sc:artist_nm 은 'KPop Demon Hunters Cast'
    다. 그걸 쓰면 같은 곡을 두고 search() 와 lookup_by_id() 가 서로 다른
    아티스트를 말하게 되고, 그 이름으로 다른 플랫폼을 검색하면 못 찾는다.
    """
    t = lookup(GOLDEN)
    assert t is not None
    assert t.artist == "HUNTR/X"
    assert t.artist != "KPop Demon Hunters Cast"


def test_the_all_artists_button_is_not_an_artist():
    """협연곡 셀에는 '아티스트 전체보기' 버튼이 <a title=...> 로 들어 있다.

    a[title] 로 아티스트를 잡으면 이 버튼 라벨이 아티스트 이름이 된다.
    """
    for row in search("겨울왕국 Let It Go", "Various Artists"):
        assert "전체보기" not in row.artist
    t = lookup(GOLDEN)
    assert "전체보기" not in t.artist


# ── 회귀 3: 없는 곡을 그럴듯한 곡으로 만들지 않기 ────────────────

def test_missing_track_returns_none():
    assert lookup(NO_SUCH_TRACK) is None


def test_missing_track_does_not_become_a_fake_track():
    """벅스는 없는 곡을 404 가 아니라 302 로 /noMusic 에 보낸다.

    그 페이지는 200 에 og:title='나를 위한 플리, 벅스' 와 벅스 로고 이미지를
    달고 온다. 그래서 두 가지를 하면 안 된다 —
      - 리다이렉트를 따라가면 안 되고,
      - og:title 을 제목/아티스트 폴백으로 쓰면 안 된다.
    둘 중 하나라도 하면 삭제된 곡이 '나를 위한 플리' 라는 Track 이 된다.
    """
    t = lookup(NO_SUCH_TRACK)
    assert t is None
    assert FakeHttpx.follow_redirects is False, (
        "리다이렉트를 따라가면 /noMusic 이 200 으로 들어와 가짜 Track 이 된다"
    )


def test_even_if_the_redirect_were_followed_no_track_is_built():
    """302 가드는 첫 번째 방어선일 뿐이다. 두 번째 방어선도 확인한다.

    누군가 follow_redirects 를 켜면 /noMusic 본문이 200 으로 들어온다. 그때도
    Track 이 만들어지면 안 된다. 이 페이지에는 sc:* 메타도, header.pgTitle h1 도,
    곡정보 표도 없어서 제목과 아티스트가 **둘 다** None 이 된다.

    있는 건 og:title='나를 위한 플리, 벅스' 뿐이다. 그래서 제목만 og:title 로
    폴백시켜도 아티스트가 따로 막아 준다 — 이 페이지에 한해서는 그렇다.
    그렇다고 og:title 을 폴백에 넣어도 된다는 뜻은 아니다. 벅스가 이 페이지의
    문구를 '제목 / 아티스트' 꼴로 바꾸는 날 바로 가짜 곡이 만들어진다.
    필수 필드 둘이 서로를 막아 준다는 사실 자체를 고정해 둔다.
    """
    from tests.fake_bugs import _read

    FakeHttpx.overrides["1"] = _read(f"track_{NO_SUCH_TRACK}")   # 200 으로 내려준다
    assert lookup("1") is None, "곡이 없는 페이지에서 Track 이 만들어지면 안 된다"


def test_album_art_placeholder_is_rejected():
    """앨범 아트 URL 은 image.bugsm.co.kr/album/images/ 아래여야 한다.

    벅스는 커버가 없을 때 로고(file.bugsm.co.kr/bdesign/sns/1200x630_bugs.png)를
    og:image 로 내려준다. 가드가 없으면 그 로고가 앨범 아트인 척 카드에 박힌다.

    이 경로는 '제목·아티스트는 멀쩡한데 og:image 만 로고' 일 때만 발동해서
    녹화된 곡으로는 태울 수 없다. 그래서 정상 곡의 og:image 를 /noMusic 에서
    **실제로 관측된** 플레이스홀더로 바꿔 끼운다.
    """
    from tests.fake_bugs import _read

    real  = _read(f"track_{IU}")
    art   = "https://image.bugsm.co.kr/album/images/500/200890/20089092.jpg"
    logo  = "https://file.bugsm.co.kr/bdesign/sns/1200x630_bugs.png"
    assert art in real, "픽스처가 바뀌었다. 바꿔 끼울 대상이 없으면 테스트가 헛돈다"

    FakeHttpx.overrides["1"] = real.replace(art, logo)
    t = lookup("1")
    assert t is not None and t.title == "밤편지"     # 곡 자체는 멀쩡해야 한다
    assert t.album_art is None, "벅스 로고를 앨범 아트로 받아들이면 안 된다"

    # 정상 곡은 그대로 통과한다
    for tid in (IU, FROZEN_OST, GOLDEN, YOUNHA):
        assert "image.bugsm.co.kr/album/images/" in lookup(tid).album_art


# ── 두 진입점이 같은 곡을 같게 말하는가 ─────────────────────────

def test_both_entry_points_read_the_same_cell_shape():
    """search() 와 lookup_by_id() 는 아티스트 셀을 같은 규칙으로 읽는다.

    한쪽만 고치면 사용자가 검색으로 찾은 곡과 링크로 연 곡이 서로 다른
    아티스트를 갖는다. 실제로 그 상태였다 — search 는 첫 <a> 를, lookup 은
    뮤비 섹션의 라벨을 읽고 있었다.
    """
    rows = {r.track_id: r for r in search("겨울왕국 Let It Go", "Various Artists")}
    row = rows.get(FROZEN_OST)
    assert row is not None, "검색 결과에 이 곡이 있어야 비교가 성립한다"
    assert row.artist == lookup(FROZEN_OST).artist


def test_the_two_entry_points_still_disagree_about_the_korean_gloss():
    """**두 경로는 아직 완전히 일치하지 않는다.** 이 테스트는 그 사실을 고정한다.

    search() 는 아티스트명의 괄호 병기를 떼고('The Weeknd(위켄드)' → 'The Weeknd'),
    lookup_by_id() 는 그대로 둔다. 그래서 같은 곡이 들어온 경로에 따라 다른
    문자열을 갖는다.

    이건 파싱이 아니라 매칭 정책 문제라서 일부러 손대지 않았다 — 어느 쪽으로
    통일하든 calc_score 결과가 달라지고, 채점 로직은 별도로 검증 중이다.
    통일하기로 결정하는 날 이 테스트가 빨개지면서 결정을 상기시킬 것이다.
    """
    t = lookup(IU)
    assert t.artist == "아이유(IU)"          # lookup 은 병기를 남긴다
    assert re.sub(r"\(.*?\)", "", t.artist).strip() == "아이유"   # search 규칙이면 이 값


def test_a_connect_badge_is_not_part_of_the_artist_name():
    """상세 페이지의 아티스트 링크에는 title 속성이 없어 텍스트로 읽는다.

    그런데 앵커 안에 <span class="badgeConnect">CONNECT 아티스트</span> 배지가
    들어 있는 경우가 실재한다 (125523552 의 세 번째 아티스트). 배지를 안 떼면
    이름에 흡수되어 'AUDREY NUNA CONNECT 아티스트' 가 된다 — 조용히 틀린 값이다.
    """
    from bs4 import BeautifulSoup

    from services.bugs import _artist_name, _info_cell
    from tests.fake_bugs import _read

    doc = BeautifulSoup(_read(f"track_{GOLDEN}"), "html.parser")
    cell = _info_cell(doc, "아티스트")
    badged = [a for a in cell.select('a[href*="/artist/"]') if a.select("span")]
    assert badged, "이 픽스처에 배지 달린 아티스트가 없다면 테스트가 헛돈다"

    # 배지가 달린 앵커만 남긴 셀을 만들어 그 경로를 직접 태운다
    for a in cell.select('a[href*="/artist/"]'):
        if not a.select("span"):
            a.decompose()
    name = _artist_name(cell)
    assert name == "AUDREY NUNA"
    assert "CONNECT" not in name


# ── 픽스처가 진짜인지 ───────────────────────────────────────────

def test_the_old_selectors_really_are_dead():
    """이 픽스처가 실제로 고장난 페이지를 담고 있는지 확인한다.

    이게 없으면, 어쩌다 옛 DOM 이 담긴 픽스처를 넣어도 테스트가 통과해
    아무것도 검증하지 못한다.
    """
    from bs4 import BeautifulSoup

    from tests.fake_bugs import _read

    doc = BeautifulSoup(_read(f"track_{IU}"), "html.parser")
    assert doc.select_one("h1.title") is None
    assert doc.select_one("a.album") is None
    assert doc.select_one("div.thumbnail img") is None

    # p.artist 는 존재하지만 곡 정보 영역이 아니라 뮤비 목록 안이다.
    for el in doc.select("p.artist"):
        assert el.find_parent("section", class_="summaryInfo") is None, (
            "p.artist 가 곡 기본정보 영역에 있다면 이 픽스처는 옛 페이지가 아니다"
        )
    # 뮤비가 없는 페이지에는 아예 0개다 — 그래서 우연히 맞던 것도 절반은 실패했다.
    assert BeautifulSoup(_read(f"track_{FROZEN_OST}"), "html.parser").select("p.artist") == []
