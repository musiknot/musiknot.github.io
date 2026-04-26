import logging

import httpx

from core.scoring import SEARCH_MATCH_THRESHOLD, calc_score
from models.schemas import Platform, Track

log = logging.getLogger(__name__)

SEARCH_URL = "https://itunes.apple.com/search"
LOOKUP_URL = "https://itunes.apple.com/lookup"

# 변형 버전(라이브/리믹스/MR) 제외용 토큰
_VARIANT_TOKENS = ("(Live)", "(Remix)", "(Inst.", "(MR)", "(Cover")


def _to_track(track: dict, similarity: float | None = None) -> Track:
    artwork = track.get("artworkUrl100", "").replace("100x100bb", "600x600bb") or None
    return Track(
        platform   = Platform.APPLE_MUSIC,
        track_id   = str(track.get("trackId", "")),
        title      = track.get("trackName", ""),
        artist     = track.get("artistName", ""),
        album      = track.get("collectionName"),
        album_art  = artwork,
        similarity = similarity,
    )


async def search(title: str, artist: str, limit: int = 5) -> list[Track]:
    """단일 best 매치를 list로 감싸 반환 (호출부 인터페이스 통일)."""
    try:
        async with httpx.AsyncClient(timeout=5) as client:
            res = await client.get(SEARCH_URL, params={
                "term":   f"{title} {artist}",
                "media":  "music",
                "entity": "song",
                "limit":  limit,
            })
            res.raise_for_status()
            results = res.json().get("results", [])
    except httpx.HTTPError as e:
        log.warning("iTunes search failed: %s", e)
        return []

    best: dict | None = None
    best_score        = 0.0

    for track in results:
        track_name = track.get("trackName", "")
        if any(x in track_name for x in _VARIANT_TOKENS):
            continue

        score = calc_score(title, artist, track_name, track.get("artistName", ""))
        # 싱글 우선 보너스
        if "Single" in track.get("collectionName", ""):
            score += 0.05

        if score > best_score:
            best_score = score
            best       = track

    if not best or best_score < SEARCH_MATCH_THRESHOLD:
        log.info("iTunes match below threshold (best=%.3f)", best_score)
        return []

    return [_to_track(best, similarity=best_score)]


async def lookup_by_id(track_id: str) -> Track | None:
    try:
        async with httpx.AsyncClient(timeout=5) as client:
            res = await client.get(LOOKUP_URL, params={"id": track_id, "media": "music"})
            res.raise_for_status()
            results = res.json().get("results", [])
    except httpx.HTTPError as e:
        log.warning("iTunes lookup failed: %s", e)
        return None

    if not results:
        return None
    return _to_track(results[0])
