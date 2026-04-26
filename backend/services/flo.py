import logging

import httpx

from core.scoring import calc_score
from models.schemas import Platform, Track

log = logging.getLogger(__name__)

FLO_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:149.0) Gecko/20100101 Firefox/149.0",
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7",
    "x-gm-os-type": "WEB",
    "x-gm-app-name": "FLO_WEB",
    "x-gm-app-version": "8.1.0",
    "x-gm-os-version": "10",
    "x-gm-device-model": "Firefox, Windows 10",
    "x-gm-access-token": "",
}

SEARCH_URL = "https://www.music-flo.com/api/search/v2/search/integration"
LOOKUP_URL = "https://www.music-flo.com/api/meta/v1/track"


async def search(title: str, artist: str, limit: int = 5) -> list[Track]:
    try:
        async with httpx.AsyncClient(headers=FLO_HEADERS, timeout=5) as client:
            res = await client.get(SEARCH_URL, params={"keyword": f"{title} {artist}"})
            res.raise_for_status()
            data = res.json()
    except httpx.HTTPError as e:
        log.warning("FLO search failed: %s", e)
        return []

    # TRACK + TITLED 섹션에서 곡 리스트 추출
    track_list = []
    for section in data.get("data", {}).get("list", []):
        if section.get("type") == "TRACK" and section.get("style") == "TITLED":
            track_list = section.get("list", [])
            break

    results: list[Track] = []
    for track in track_list[:limit]:
        track_id   = str(track.get("id", ""))
        if not track_id:
            continue
        res_title  = track.get("name", "")
        res_artist = track.get("representationArtist", {}).get("name", "")

        img_list = track.get("album", {}).get("imgList", [])
        artwork  = next((i["url"] for i in img_list if i.get("size") == 500), None)

        results.append(Track(
            platform   = Platform.FLO,
            track_id   = track_id,
            title      = res_title,
            artist     = res_artist,
            album      = track.get("album", {}).get("title"),
            album_art  = artwork,
            similarity = calc_score(title, artist, res_title, res_artist),
        ))

    return sorted(results, key=lambda t: t.similarity or 0, reverse=True)


async def lookup_by_id(track_id: str) -> Track | None:
    try:
        async with httpx.AsyncClient(headers=FLO_HEADERS, timeout=5) as client:
            res = await client.get(f"{LOOKUP_URL}/{track_id}")
            res.raise_for_status()
            data = res.json().get("data", {})
    except httpx.HTTPError as e:
        log.warning("FLO lookup failed: %s", e)
        return None

    if not data:
        return None

    img_list = data.get("album", {}).get("imgList", [])
    artwork  = next((i["url"] for i in img_list if i.get("size") == 500), None)
    artists  = ", ".join(a["name"] for a in data.get("artistList", []))

    return Track(
        platform  = Platform.FLO,
        track_id  = track_id,
        title     = data.get("name", ""),
        artist    = artists,
        album     = data.get("album", {}).get("title"),
        album_art = artwork,
    )
