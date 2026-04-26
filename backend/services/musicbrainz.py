import asyncio
import logging
import re

import musicbrainzngs

from core.scoring import MUSICBRAINZ_MIN_SCORE

log = logging.getLogger(__name__)

# TODO: 실제 contact (이메일 또는 GitHub repo URL)로 교체
musicbrainzngs.set_useragent("MusiknotApp", "1.0", "https://github.com/musiknot/musiknot.github.io")


def _normalize_artist_name(name: str) -> str:
    """'Yonezu, Kenshi' → 'Kenshi Yonezu'."""
    if "," in name:
        parts = [p.strip() for p in name.split(",", 1)]
        return f"{parts[1]} {parts[0]}"
    return name


def _clean_title(title: str) -> str:
    """부제·괄호 표기 제거. 'Sayonara, Mata Itsuka! - Sayonara' → 'Sayonara, Mata Itsuka!'"""
    title = re.sub(r"\s*-\s*\S+.*$", "", title).strip()
    title = re.sub(r"\s*\(.*?\)\s*$", "", title).strip()
    return title


def _extract_candidates(rec: dict) -> list[dict]:
    """단일 recording에서 영문 제목 후보 추출."""
    artist_info = rec.get("artist-credit", [{}])[0].get("artist", {})

    en_artist = _normalize_artist_name(artist_info.get("sort-name", ""))
    for alias in artist_info.get("alias-list", []):
        if alias.get("locale") == "en" and alias.get("primary") == "primary":
            en_artist = alias.get("name", en_artist)
            break

    seen: set[str]            = set()
    candidates: list[dict]    = []

    for release in rec.get("release-list", []):
        is_en = (
            release.get("status") == "Pseudo-Release"
            or "北米" in release.get("disambiguation", "")
            or release.get("artist-credit", [{}])[0].get("name", "").isascii()
        )
        if not is_en:
            continue

        try:
            track_title = release["medium-list"][0]["track-list"][0]["title"]
        except (KeyError, IndexError):
            continue

        if not track_title.isascii() or track_title in seen:
            continue
        seen.add(track_title)
        candidates.append({"english_title": track_title, "english_artist": en_artist})

        cleaned = _clean_title(track_title)
        if cleaned != track_title and cleaned not in seen:
            seen.add(cleaned)
            candidates.append({"english_title": cleaned, "english_artist": en_artist})

    return candidates


def _get_english_candidates_sync(title: str, artist: str) -> list[dict]:
    try:
        result = musicbrainzngs.search_recordings(recording=title, artist=artist, limit=5)
    except musicbrainzngs.WebServiceError as e:
        log.warning("MusicBrainz error: %s", e)
        return []

    for rec in result.get("recording-list", []):
        if rec.get("video") == "true":
            continue
        if int(rec.get("ext:score", 0)) < MUSICBRAINZ_MIN_SCORE:
            continue

        candidates = _extract_candidates(rec)
        if candidates:
            log.info("MusicBrainz: %d candidate(s) from rec '%s'", len(candidates), rec.get("title"))
            return candidates

    log.info("MusicBrainz: no English candidates for '%s' / '%s'", title, artist)
    return []


async def get_english_candidates(title: str, artist: str) -> list[dict]:
    """동기 라이브러리를 스레드풀로 위임 (이벤트 루프 블로킹 방지)."""
    return await asyncio.to_thread(_get_english_candidates_sync, title, artist)
