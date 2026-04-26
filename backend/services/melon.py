import logging
import re

import httpx
from bs4 import BeautifulSoup

from core.scoring import calc_score
from models.schemas import Platform, Track

log = logging.getLogger(__name__)

MELON_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
    "Accept-Language": "ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7",
    "Accept-Encoding": "gzip, deflate, br",
    "Connection": "keep-alive",
    "Referer": "https://www.melon.com",
    "Upgrade-Insecure-Requests": "1",
}

SEARCH_URL = "https://www.melon.com/search/song/index.htm"
DETAIL_URL = "https://www.melon.com/song/detail.htm"


async def search(title: str, artist: str, limit: int = 5) -> list[Track]:
    try:
        async with httpx.AsyncClient(headers=MELON_HEADERS, timeout=5) as client:
            res = await client.get(SEARCH_URL, params={"q": title})
            res.raise_for_status()
    except httpx.HTTPError as e:
        log.warning("Melon search failed: %s", e)
        return []

    doc = BeautifulSoup(res.text, "html.parser")
    results: list[Track] = []

    for row in doc.select("tr"):
        if len(results) >= limit:
            break

        btn = row.select_one("button[data-song-no]")
        if not btn:
            continue

        title_el  = row.select_one("a.fc_gray[title]")
        artist_el = row.select_one("a.fc_mgray")
        album_el  = row.find("a", href=re.compile(r"goAlbumDetail"))

        if not title_el or not artist_el:
            continue

        res_title  = title_el.text.strip()
        res_artist = artist_el.text.strip()

        results.append(Track(
            platform   = Platform.MELON,
            track_id   = btn.get("data-song-no"),
            title      = res_title,
            artist     = res_artist,
            album      = album_el.text.strip() if album_el else None,
            similarity = calc_score(title, artist, res_title, res_artist),
        ))

    return sorted(results, key=lambda t: t.similarity or 0, reverse=True)


async def lookup_by_id(track_id: str) -> Track | None:
    """곡 상세 페이지로 1차 시도, 실패 시 검색 페이지 폴백."""
    async with httpx.AsyncClient(headers=MELON_HEADERS, timeout=10) as client:
        # 메인 페이지를 먼저 방문해서 세션 쿠키 확보 (봇 탐지 우회)
        try:
            await client.get("https://www.melon.com")
        except httpx.HTTPError:
            pass

        # 1차: 상세 페이지
        track = await _lookup_via_detail(client, track_id)
        if track:
            return track

        # 2차: 검색 페이지에서 동일 songId 행 찾기
        return await _lookup_via_search(client, track_id)


async def _lookup_via_detail(client: httpx.AsyncClient, track_id: str) -> Track | None:
    try:
        res = await client.get(DETAIL_URL, params={"songId": track_id})
        res.raise_for_status()
    except httpx.HTTPError as e:
        log.warning("Melon detail request failed: %s", e)
        return None

    doc = BeautifulSoup(res.text, "html.parser")

    title_el  = doc.select_one("div.song_name")
    artist_el = doc.select_one("div.artist a")
    album_el  = doc.select_one("div.meta dd a")
    img_el    = doc.select_one("div.thumb img")

    if not title_el or not artist_el:
        log.info("Melon detail parse miss for id=%s, falling back to search", track_id)
        return None

    title_text = title_el.get_text(strip=True).replace("곡명", "").strip()

    return Track(
        platform  = Platform.MELON,
        track_id  = track_id,
        title     = title_text,
        artist    = artist_el.get_text(strip=True),
        album     = album_el.get_text(strip=True) if album_el else None,
        album_art = img_el["src"] if img_el and img_el.get("src") else None,
    )


async def _lookup_via_search(client: httpx.AsyncClient, track_id: str) -> Track | None:
    try:
        res = await client.get(SEARCH_URL, params={
            "q":           track_id,
            "section":     "",
            "searchGnbYn": "Y",
            "kkoSpl":      "Y",
            "kkoDpType":   "",
            "mwkLogType":  "T",
        })
        res.raise_for_status()
    except httpx.HTTPError as e:
        log.warning("Melon search-fallback failed: %s", e)
        return None

    doc = BeautifulSoup(res.text, "html.parser")

    for row in doc.select("table tbody tr"):
        btn = row.select_one("button[data-song-no]")
        if not btn or btn.get("data-song-no") != str(track_id):
            continue

        title_el  = row.select_one("a.fc_gray")
        artist_el = row.select_one("div.ellipsis.rank02 a")
        album_el  = row.select_one("div.ellipsis.rank03 a")
        img_el    = row.select_one("img")

        if not title_el:
            continue

        return Track(
            platform  = Platform.MELON,
            track_id  = track_id,
            title     = title_el.get_text(strip=True),
            artist    = artist_el.get_text(strip=True) if artist_el else "",
            album     = album_el.get_text(strip=True) if album_el else None,
            album_art = img_el["src"] if img_el and img_el.get("src") else None,
        )

    log.info("Melon search-fallback found no match for id=%s", track_id)
    return None


def merge_results(a: list[Track], b: list[Track]) -> list[Track]:
    """track_id 중복 제거 후 similarity 내림차순 정렬."""
    seen: set[str]      = set()
    merged: list[Track] = []
    for t in sorted(a + b, key=lambda x: x.similarity or 0, reverse=True):
        if t.track_id not in seen:
            seen.add(t.track_id)
            merged.append(t)
    return merged
