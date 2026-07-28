import copy
import logging
import re

import httpx
from bs4 import BeautifulSoup

from core.scoring import calc_score
from models.schemas import Platform, Track

log = logging.getLogger(__name__)

BUGS_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}

# 앨범 아트로 인정할 URL 패턴. 벅스는 곡이 없을 때 SNS 기본 이미지
# (file.bugsm.co.kr/bdesign/sns/1200x630_bugs.png) 를 og:image 로 내려준다.
# 그걸 그대로 받으면 카드에 벅스 로고가 앨범 아트인 척 박힌다.
_ALBUM_ART_PATH = "image.bugsm.co.kr/album/images/"

_WS = re.compile(r"\s+")


def _clean(text: str | None) -> str | None:
    """표 셀에는 들여쓰기 탭과 개행이 섞여 있다. 양끝뿐 아니라 내부 공백도 눌러야 한다."""
    if not text:
        return None
    return _WS.sub(" ", text).strip() or None


def _meta(doc: BeautifulSoup, prop: str) -> str | None:
    """`<meta property="...">` 의 content."""
    el = doc.find("meta", attrs={"property": prop})
    return _clean(el.get("content")) if el else None


def _info_cell(doc: BeautifulSoup, label: str):
    """곡 기본정보 표에서 `<th>{label}</th>` 인 행의 `<td>`.

    행 위치로 찾으면 안 된다 — '앨범' 은 '참여 정보' 행이 있으면 3번째,
    없으면 2번째다.
    """
    for row in doc.select("section.summaryInfo table.info tr"):
        th = row.select_one("th")
        if th and _clean(th.text) == label:
            return row.select_one("td")
    return None


def _artist_name(cell) -> str | None:
    """아티스트 셀에서 대표 아티스트 한 명을 뽑는다.

    셀은 세 가지 모양이다 (검색 결과 400행 + 트랙 상세 10곡 실측):

        링크 하나      373/400   <a href=".../artist/123" title="아이유(IU)">
        링크 여럿       13/400   협연. 첫 번째가 대표다
        링크 없는 평문  27/400   'Unknown' 22 · 'Various Artists' 3 · 'Cover Artist' 2

    링크는 반드시 `/artist/` 를 가리킨다는 데 앵커링한다. `a[title]` 로 잡으면
    협연곡의 '아티스트 전체보기' 버튼(`a.more`)이 아티스트 이름으로 섞인다.

    **링크가 없다고 곡을 버리면 안 된다.** 그건 파서가 아니라 스코어러가 할
    판단이다 — calc_score 는 'Unknown' 에 0.000 을 준다. 예전 코드는 여기서
    행을 버려서 OST·컴필레이션 곡이 벅스에서 통째로 사라졌다.
    """
    if cell is None:
        return None

    link = cell.select_one('a[href*="/artist/"]')
    if link is None:
        return _clean(cell.get_text(" "))

    # 검색 결과의 링크에는 title 속성이 있지만 트랙 상세 페이지의 링크에는 없다.
    # 텍스트로 떨어질 때는 배지를 떼야 한다 — 앵커 안에 'CONNECT 아티스트'
    # 같은 <span> 배지가 들어 있으면 그게 이름에 흡수된다
    # (실제로 'AUDREY NUNA' 가 'AUDREY NUNA CONNECT 아티스트' 가 된다).
    # 원본 문서를 건드리지 않으려고 복사본에서 떼어낸다.
    if link.get("title"):
        return _clean(link.get("title"))

    node = copy.copy(link)
    for badge in node.select("span"):
        badge.decompose()
    return _clean(node.get_text(" "))


async def search(title: str, artist: str, limit: int = 5) -> list[Track]:
    try:
        async with httpx.AsyncClient(headers=BUGS_HEADERS, timeout=5) as client:
            res = await client.get(
                "https://music.bugs.co.kr/search/track",
                params={"q": title},
            )
            res.raise_for_status()
    except httpx.HTTPError as e:
        log.warning("Bugs search failed: %s", e)
        return []

    doc = BeautifulSoup(res.text, "html.parser")
    results: list[Track] = []

    for row in doc.select("tr[trackid]"):
        if len(results) >= limit:
            break

        track_id   = row.get("trackid")
        title_el   = row.select_one("p.title a[title]")
        res_artist = _artist_name(row.select_one("p.artist"))
        if not track_id or not title_el or not res_artist:
            continue

        res_title = _clean(title_el.get("title"))
        if not res_title:
            continue

        # 아티스트명에서 한국어 표기 제거 (예: "The Weeknd(위켄드)" → "The Weeknd").
        # 통째로 괄호인 이름이 빈 문자열이 되지 않게 원본으로 되돌린다.
        res_artist = _clean(re.sub(r"\(.*?\)", "", res_artist)) or res_artist

        results.append(Track(
            platform   = Platform.BUGS,
            track_id   = track_id,
            title      = res_title,
            artist     = res_artist,
            similarity = calc_score(title, artist, res_title, res_artist),
        ))

    return sorted(results, key=lambda t: t.similarity or 0, reverse=True)


async def lookup_by_id(track_id: str) -> Track | None:
    try:
        async with httpx.AsyncClient(headers=BUGS_HEADERS, timeout=5) as client:
            # **리다이렉트를 따라가지 않는다.** 없는 곡은 302 로 /noMusic 에
            # 보내는데 그 페이지는 200 에 og:title='나를 위한 플리, 벅스' 와
            # 벅스 로고 이미지를 달고 온다. 따라갔다가는 삭제된 곡이 그럴듯한
            # 가짜 Track 이 된다. 안 따라가면 302 에서 raise_for_status 가
            # 걸려 None 으로 끝난다.
            res = await client.get(f"https://music.bugs.co.kr/track/{track_id}")
            res.raise_for_status()
    except httpx.HTTPError as e:
        log.warning("Bugs lookup failed: %s", e)
        return None

    doc = BeautifulSoup(res.text, "html.parser")

    # 벅스는 공유 카드용으로 sc:* 메타를 <head> 에 박아둔다. 본문 DOM 보다
    # 안정적이고, 무엇보다 곡이 없는 페이지에는 아예 없어서 실패가 조용하지 않다.
    # og:title 을 " / " 로 쪼개는 폴백은 쓰지 않는다 — /noMusic 페이지에도
    # og:title 이 채워져 있어서 쓰레기 값을 만들어낸다.
    title = _meta(doc, "sc:track_title")
    if not title:
        h1 = doc.select_one("header.pgTitle h1")
        title = _clean(h1.text) if h1 else None

    # 아티스트만 메타보다 표를 먼저 본다. 협연곡에서 sc:artist_nm 은 대표가
    # 아니라 앨범 크레딧을 준다 — 'Golden' 의 대표는 'HUNTR/X' 인데
    # sc:artist_nm 은 'KPop Demon Hunters Cast' 다. 그러면 같은 곡을 두고
    # search() 와 lookup_by_id() 가 서로 다른 아티스트를 말하게 된다.
    artist = _artist_name(_info_cell(doc, "아티스트"))
    if not artist:
        # 표를 못 읽었다. sc:artist_nm 으로 버티되 조용히 넘기지 않는다 —
        # 이 폴백은 협연곡에서 대표가 아닌 앨범 크레딧을 주므로, 여기가 값이
        # 조용히 틀릴 수 있는 유일한 지점이다. 이번 버그가 오래 안 잡힌 이유도
        # 로그가 없어서였다.
        artist = _meta(doc, "sc:artist_nm")
        if artist:
            log.warning(
                "Bugs %s: 곡정보 표를 못 읽어 sc:artist_nm 으로 폴백했다 (artist=%s)",
                track_id, artist,
            )

    if not title or not artist:
        return None

    album_cell = _info_cell(doc, "앨범")
    album = _meta(doc, "sc:album_title") or (
        _clean(album_cell.get_text(" ")) if album_cell else None
    )

    # og:image 는 500px 이고 캐시버스터 쿼리가 없다. 본문의 앨범 아트는
    # 200px 에 ?version=... 이 붙는다.
    album_art = _meta(doc, "og:image")
    if album_art and _ALBUM_ART_PATH not in album_art:
        album_art = None

    return Track(
        platform  = Platform.BUGS,
        track_id  = track_id,
        title     = title,
        artist    = artist,
        album     = album,
        album_art = album_art,
    )
