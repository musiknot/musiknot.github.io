import asyncio
import logging
import os

from fastapi import APIRouter, HTTPException, Request

from core.resilience import AsyncTTLCache, SlidingWindowRateLimiter
from core.scoring import SEARCH_MATCH_THRESHOLD
from models.schemas import (
    ParseRequest,
    ParseResponse,
    Platform,
    PlatformIds,
    Track,
)
from services import bugs, flo, itunes, melon, url_resolver, youtube
from utils.platform_url import build_share_id, extract_platform_id, parse_share_id

log    = logging.getLogger(__name__)
router = APIRouter()


# 전부 환경 변수로 바꿀 수 있게 두되, 기본값은 한 대의 개인 서비스에서 업스트림
# 차단을 피하는 보수적인 수준이다. 인메모리 상태이므로 프로세스 재시작 때 초기화된다.
#
# 데드라인 40초는 각 서비스의 timeout(멜론 10초, 나머지 5초)이 순차 단계
# (단축 URL 해제 → lookup → 메타 보강 → 크로스플랫폼 병렬 조회)에 쌓이는 것을
# 덮는 값이다. 외부 호출은 어느 것도 재시도하지 않으므로 이 예산이 곱해지지 않는다
# (services/itunes.py 의 429 주석 참고).
PARSE_TIMEOUT_SECONDS = float(os.getenv("PARSE_TIMEOUT_SECONDS", "40"))
PARSE_CACHE_TTL_SECONDS = float(os.getenv("PARSE_CACHE_TTL_SECONDS", "600"))
PARSE_CACHE_MAX_ENTRIES = int(os.getenv("PARSE_CACHE_MAX_ENTRIES", "500"))
PARSE_RATE_LIMIT = int(os.getenv("PARSE_RATE_LIMIT", "20"))
PARSE_RATE_WINDOW_SECONDS = float(os.getenv("PARSE_RATE_WINDOW_SECONDS", "60"))

_parse_cache = AsyncTTLCache(
    ttl_seconds=PARSE_CACHE_TTL_SECONDS,
    max_entries=PARSE_CACHE_MAX_ENTRIES,
)
_parse_limiter = SlidingWindowRateLimiter(
    limit=PARSE_RATE_LIMIT,
    window_seconds=PARSE_RATE_WINDOW_SECONDS,
)


# 플랫폼 → 게이트웨이 lookup_by_id 라우팅
_LOOKUP_BY_PLATFORM = {
    Platform.APPLE_MUSIC:   itunes.lookup_by_id,
    Platform.MELON:         melon.lookup_by_id,
    Platform.BUGS:          bugs.lookup_by_id,
    Platform.FLO:           flo.lookup_by_id,
    Platform.YOUTUBE:       youtube.lookup_by_id,
    Platform.YOUTUBE_MUSIC: youtube.lookup_by_id,
}


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
    """모든 플랫폼에 **원문 그대로** 질의한다.

    예전에는 여기서 MusicBrainz로 영문 질의어를 만들어 돌려썼는데, 그게 두 가지를
    한꺼번에 망가뜨리고 있었다.
      1) 멜론/벅스/FLO는 원제만 색인한다. 번역어를 넣으면 '밤편지'(정답,
         sim 1.0) 대신 'Through the Night'로 검색해 sim 0.54짜리 엉뚱한 곡이
         임계값을 통과했다.
      2) iTunes 쪽은 번역이 필요 없다. itunes.search()가 문자체계에 맞는
         스토어프론트를 골라 원문 표기 그대로 받아온다.
    번역어는 이제 어디에도 필요하지 않다.
    """
    ids: dict[str, str | None] = {p.value: None for p in Platform}
    ids[known_platform.value]  = known_id

    async def fetch_apple():
        if ids[Platform.APPLE_MUSIC.value]:
            return
        results = await itunes.search(title, artist)
        if results:
            ids[Platform.APPLE_MUSIC.value] = results[0].track_id

    async def fetch_melon():
        if ids[Platform.MELON.value]:
            return
        results = await melon.search(title, artist)
        if results and (results[0].similarity or 0) >= SEARCH_MATCH_THRESHOLD:
            ids[Platform.MELON.value] = results[0].track_id

    async def fetch_bugs():
        if ids[Platform.BUGS.value]:
            return
        results = await bugs.search(title, artist)
        if results and (results[0].similarity or 0) >= SEARCH_MATCH_THRESHOLD:
            ids[Platform.BUGS.value] = results[0].track_id

    async def fetch_flo():
        if ids[Platform.FLO.value]:
            return
        results = await flo.search(title, artist)
        if results and (results[0].similarity or 0) >= SEARCH_MATCH_THRESHOLD:
            ids[Platform.FLO.value] = results[0].track_id

    async def fetch_youtube():
        if ids[Platform.YOUTUBE.value] and ids[Platform.YOUTUBE_MUSIC.value]:
            return

        # 검색 한 번으로 MV 와 Topic 을 함께 받는다. 예전에는 두 번 호출했는데,
        # search.list 가 100 유닛이라 그것만으로 하루 상한이 절반이 됐다.
        mv, topic = await youtube.search_mv_and_topic(title, artist)

        if mv and not ids[Platform.YOUTUBE.value]:
            ids[Platform.YOUTUBE.value] = mv.track_id

        if not ids[Platform.YOUTUBE_MUSIC.value]:
            if topic:
                ids[Platform.YOUTUBE_MUSIC.value] = topic.track_id
            elif ids[Platform.YOUTUBE.value]:
                # Topic 없으면 MV로 fallback
                ids[Platform.YOUTUBE_MUSIC.value] = ids[Platform.YOUTUBE.value]

    await asyncio.gather(
        fetch_apple(), fetch_melon(), fetch_bugs(), fetch_flo(), fetch_youtube(),
    )

    return PlatformIds(**ids)


async def _parse_uncached(req: ParseRequest) -> ParseResponse:
    """외부 서비스 조회를 실제로 수행하는 `/parse` 본문.

    캐시·제한·시간 제한과 분리해 두면, 실패한 조회가 캐시되는 일이 없고 이
    함수의 플랫폼 처리 흐름도 그대로 읽힌다.
    """
    # 공유 ID 로 들어온 경우 — URL 해제·정규식 단계를 건너뛴다.
    # ID 자체가 이미 (platform, track_id) 이기 때문이다.
    if req.id:
        parsed = parse_share_id(req.id)
        if not parsed:
            raise HTTPException(status_code=400, detail="잘못된 공유 ID 입니다.")
        platform, track_id = parsed
        log.info("Share id → platform=%s, id=%s", platform.value, track_id)
    else:
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

    # STEP 5: 나머지 플랫폼 ID 병렬 조회 (원문 질의)
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
        shareId   = build_share_id(platform, track_id),
    )


def _cache_key(req: ParseRequest) -> str:
    """URL과 공유 ID 입력 공간을 명확히 분리한 캐시 키."""
    return f"id:{req.id}" if req.id else f"url:{req.url}"


def _client_key(request: Request) -> str:
    """Caddy(로컬 역방향 프록시)를 거친 실제 요청자의 안정적인 키.

    `X-Forwarded-For`는 바로 연결한 쪽이 loopback일 때만 신뢰한다. 외부에서
    API 포트에 직접 붙는 요청은 이 헤더를 위조해 제한을 우회할 수 없고, 로컬
    개발 서버에서는 자연스럽게 `request.client.host`를 사용한다.
    """
    host = request.client.host if request.client else "unknown"
    if host in {"127.0.0.1", "::1"}:
        forwarded = request.headers.get("x-forwarded-for", "").split(",", 1)[0].strip()
        if forwarded:
            return forwarded
    return host


@router.post("/parse", response_model=ParseResponse)
async def parse_url(req: ParseRequest, request: Request):
    allowed, retry_after = await _parse_limiter.allow(_client_key(request))
    if not allowed:
        raise HTTPException(
            status_code=429,
            detail="요청이 너무 많습니다. 잠시 후 다시 시도해 주세요.",
            headers={"Retry-After": str(retry_after)},
        )

    async def fetch() -> ParseResponse:
        try:
            return await asyncio.wait_for(_parse_uncached(req), timeout=PARSE_TIMEOUT_SECONDS)
        except TimeoutError as e:
            log.warning("Parse request timed out after %.1fs", PARSE_TIMEOUT_SECONDS)
            raise HTTPException(
                status_code=504,
                detail="음원 서비스 응답이 지연되고 있습니다. 잠시 후 다시 시도해 주세요.",
            ) from e

    return await _parse_cache.get_or_create(_cache_key(req), fetch)
