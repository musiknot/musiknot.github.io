import asyncio
import logging

from fastapi import APIRouter, HTTPException

from core.scoring import SEARCH_MATCH_THRESHOLD
from models.schemas import (
    ParseRequest,
    ParseResponse,
    Platform,
    PlatformIds,
    Track,
)
from services import bugs, flo, itunes, melon, musicbrainz, url_resolver, youtube
from utils.platform_url import extract_platform_id

log    = logging.getLogger(__name__)
router = APIRouter()


# 플랫폼 → 게이트웨이 lookup_by_id 라우팅
_LOOKUP_BY_PLATFORM = {
    Platform.APPLE_MUSIC:   itunes.lookup_by_id,
    Platform.MELON:         melon.lookup_by_id,
    Platform.BUGS:          bugs.lookup_by_id,
    Platform.FLO:           flo.lookup_by_id,
    Platform.YOUTUBE:       youtube.lookup_by_id,
    Platform.YOUTUBE_MUSIC: youtube.lookup_by_id,
}


async def _resolve_english_query(title: str, artist: str) -> tuple[str, str]:
    """
    외국 플랫폼 검색용 영문 질의어 결정.
    - 이미 ASCII면 그대로 사용
    - MusicBrainz가 영문 후보를 주면 첫 번째 사용
    - 둘 다 안 되면 원본 그대로 fallback (영어 후보 없을 때 검색이 아예 안 도는 것보단 낫다)
    """
    if title.isascii() and artist.isascii():
        return title, artist

    candidates = await musicbrainz.get_english_candidates(title, artist)
    if candidates:
        return candidates[0]["english_title"], candidates[0]["english_artist"]

    log.info("No English candidates from MusicBrainz; using original title/artist")
    return title, artist


async def _enrich_track(track: Track) -> Track:
    """원본 플랫폼이 album/album_art를 못 채웠으면 iTunes로 보강."""
    if track.album and track.album_art:
        return track

    itunes_results = await itunes.search(track.title, track.artist)
    if not itunes_results:
        return track

    fill = itunes_results[0]
    return track.model_copy(update={
        "album":     track.album     or fill.album,
        "album_art": track.album_art or fill.album_art,
    })


async def _find_cross_platform_ids(
    title: str, artist: str, known_platform: Platform, known_id: str,
) -> PlatformIds:
    en_title, en_artist = await _resolve_english_query(title, artist)

    ids: dict[str, str | None] = {p.value: None for p in Platform}
    ids[known_platform.value]  = known_id

    async def fetch_apple():
        if ids[Platform.APPLE_MUSIC.value]:
            return
        results = await itunes.search(en_title, en_artist)
        if results:
            ids[Platform.APPLE_MUSIC.value] = results[0].track_id

    async def fetch_melon():
        if ids[Platform.MELON.value]:
            return
        results = await melon.search(en_title, en_artist)
        if results and (results[0].similarity or 0) >= SEARCH_MATCH_THRESHOLD:
            ids[Platform.MELON.value] = results[0].track_id

    async def fetch_bugs():
        if ids[Platform.BUGS.value]:
            return
        results = await bugs.search(en_title, en_artist)
        if results and (results[0].similarity or 0) >= SEARCH_MATCH_THRESHOLD:
            ids[Platform.BUGS.value] = results[0].track_id

    async def fetch_flo():
        if ids[Platform.FLO.value]:
            return
        results = await flo.search(en_title, en_artist)
        if results and (results[0].similarity or 0) >= SEARCH_MATCH_THRESHOLD:
            ids[Platform.FLO.value] = results[0].track_id

    async def fetch_youtube():
        # MV 우선
        if not ids[Platform.YOUTUBE.value]:
            mv = await youtube.search_mv(en_title, en_artist)
            if mv:
                ids[Platform.YOUTUBE.value] = mv.track_id

        # Topic 채널 음원
        if not ids[Platform.YOUTUBE_MUSIC.value]:
            topic = await youtube.search_topic(en_title, en_artist)
            if topic:
                ids[Platform.YOUTUBE_MUSIC.value] = topic.track_id
            elif ids[Platform.YOUTUBE.value]:
                # Topic 없으면 MV로 fallback
                ids[Platform.YOUTUBE_MUSIC.value] = ids[Platform.YOUTUBE.value]

    await asyncio.gather(
        fetch_apple(), fetch_melon(), fetch_bugs(), fetch_flo(), fetch_youtube(),
    )

    return PlatformIds(**ids)


@router.post("/parse", response_model=ParseResponse)
async def parse_url(req: ParseRequest):
    url = req.url

    # STEP 1: 단축 URL 해제
    if "kko.to" in url or "flomuz.io" in url:
        try:
            url = await url_resolver.resolve_url(url)
            log.info("Short URL resolved → %s", url)
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))

    # STEP 2: 플랫폼 감지
    parsed = extract_platform_id(url)
    if not parsed:
        raise HTTPException(status_code=400, detail="지원하지 않는 플랫폼입니다.")
    platform, track_id = parsed
    log.info("Detected platform=%s, id=%s", platform.value, track_id)

    # STEP 3: 해당 플랫폼에서 곡 정보 조회
    lookup = _LOOKUP_BY_PLATFORM.get(platform)
    if lookup is None:
        raise HTTPException(status_code=501, detail=f"플랫폼 lookup 미구현: {platform.value}")

    track = await lookup(track_id)
    if not track:
        raise HTTPException(status_code=404, detail="곡 정보를 찾을 수 없습니다.")

    # STEP 4: album/album_art 누락 시 iTunes로 보강
    track = await _enrich_track(track)

    # STEP 5: 나머지 플랫폼 ID 병렬 조회
    platform_ids = await _find_cross_platform_ids(
        track.title, track.artist, platform, track_id,
    )

    return ParseResponse(
        title     = track.title,
        artist    = track.artist,
        album     = track.album,
        albumArt  = track.album_art,
        isrc      = None,
        platforms = platform_ids,
    )
