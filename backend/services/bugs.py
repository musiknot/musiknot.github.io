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

        track_id  = row.get("trackid")
        title_el  = row.select_one("p.title a[title]")
        artist_el = row.select_one("p.artist a[title]")
        if not track_id or not title_el or not artist_el:
            continue

        res_title  = title_el.get("title", "").strip()
        # 아티스트명에서 한국어 표기 제거 (예: "The Weeknd(위켄드)" → "The Weeknd")
        res_artist = re.sub(r"\(.*?\)", "", artist_el.get("title", "").strip()).strip()

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
            res = await client.get(f"https://music.bugs.co.kr/track/{track_id}")
            res.raise_for_status()
    except httpx.HTTPError as e:
        log.warning("Bugs lookup failed: %s", e)
        return None

    doc = BeautifulSoup(res.text, "html.parser")
    title_el  = doc.select_one("h1.title")
    artist_el = doc.select_one("p.artist a")
    album_el  = doc.select_one("a.album")
    img_el    = doc.select_one("div.thumbnail img")

    if not title_el or not artist_el:
        return None

    return Track(
        platform  = Platform.BUGS,
        track_id  = track_id,
        title     = title_el.text.strip(),
        artist    = artist_el.text.strip(),
        album     = album_el.text.strip() if album_el else None,
        album_art = img_el.get("src") if img_el else None,
    )
