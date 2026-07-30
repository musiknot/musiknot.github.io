import logging

import httpx

from core.scoring import (
    RANK_TIEBREAK,
    SEARCH_MATCH_THRESHOLD,
    WEAK_MATCH_THRESHOLD,
    calc_score,
    route_storefronts,
)
from models.schemas import Platform, Track

log = logging.getLogger(__name__)

SEARCH_URL = "https://itunes.apple.com/search"
LOOKUP_URL = "https://itunes.apple.com/lookup"

# 상위 몇 개까지 훑을지. 정답이 1위가 아닌 경우가 실제로 있다
# (예: '너를 만나'/폴킴은 같은 아티스트의 다른 곡 뒤 2위에 온다).
SCAN_LIMIT = 5

# iTunes는 분당 약 20회에서 429와 Retry-After(실측 19~29초)를 돌려준다.
# **기다렸다 재시도하지 않는다.** 한때 그렇게 했다가 더 나빠졌다 — 429일 때
# _get 이 빈 리스트를 돌려주면 search() 의 조기 반환 조건이 성립하지 않아
# 스토어프론트를 전부 돌고, 그래서 대기가 곱해진다. 한국어 곡이면
# search() 한 번이 29초씩 두 번, /parse 는 search 를 두 번 부르니 116초.
# 40초 데드라인에 걸려 504 가 됐다. 그 전에는 같은 상황에서
# appleMusic 만 비우고 200 을 냈다. 즉 재시도가 회귀였다.
#
# 애플 칸 하나를 비우는 것이 곡 전체를 못 찾는 것보다 낫다. 게다가 429 자체는
# /parse 캐시(routers/parse.py)가 줄여준다.


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


async def _get(url: str, params: dict) -> list[dict]:
    """빈 값/None 파라미터는 빼고 GET. 실패하면 빈 리스트.

    429 도 다른 오류와 똑같이 다룬다 — 기다리지 않고 곧바로 포기한다.
    이유는 위 주석 참고.
    """
    clean = {k: v for k, v in params.items() if v is not None and v != ""}
    try:
        async with httpx.AsyncClient(timeout=5) as client:
            res = await client.get(url, params=clean)
            res.raise_for_status()
            return res.json().get("results", [])
    except httpx.HTTPError as e:
        log.warning("iTunes request failed (%s): %s", url, e)
        return []


def _best_candidate(title: str, artist: str, results: list[dict], limit: int):
    """(후보, 순위보정점수, 순수점수). 채택 판단은 순위보정점수로 한다.

    순위 가산점은 '동일성'을 대체하지 않는다. 0점(다른 곡/다른 연주자)은
    가산점을 아예 받지 못하므로 카라오케 커버가 순위로 진짜 곡을 이길 수 없다.
    가산점은 메타데이터가 완전히 같은 프레싱들(같은 녹음, 다른 앨범) 사이에서만
    의미를 갖고, 그 경우엔 iTunes 자체 관련도 순서가 가장 좋은 판단 기준이다.
    """
    best, best_ranked, best_score = None, 0.0, 0.0

    for rank, track in enumerate(results[:limit]):
        if not track.get("trackId"):
            continue

        score = calc_score(
            title, artist,
            track.get("trackName") or "",
            track.get("artistName") or "",
            track.get("collectionName") or "",
        )
        if score <= 0.0:
            continue

        ranked = score + RANK_TIEBREAK * (limit - rank)
        if ranked > best_ranked:
            best, best_ranked, best_score = track, ranked, score

    return best, best_ranked, best_score


async def search(title: str, artist: str, limit: int = SCAN_LIMIT) -> list[Track]:
    """단일 best 매치를 list로 감싸 반환 (호출부 인터페이스 통일).

    핵심은 `country`다. 이 파라미터는 스토어프론트뿐 아니라 **메타데이터 언어**를
    고른다. country를 안 보내면 US 스토어프론트가 잡히고, 한국어/일본어 곡은
    영어로 번역된 제목이 돌아온다 — 그러면 '물론' vs 'With you'를 비교하게 되어
    유사도가 구조적으로 0이 되고 정답이 버려진다. 그래서 입력 문자체계에 맞는
    스토어프론트에 먼저 질의해, 애초에 번역이 생기지 않게 한다.

    검색어는 '아티스트 제목' 순서다. 순서가 실제로 결과를 바꾼다
    ('아이유 밤편지'는 정답을, '밤편지 아이유'는 엉뚱한 곡을 1위로 준다).
    """
    title  = (title or "").strip()
    artist = (artist or "").strip()
    if not title:
        return []

    term = f"{artist} {title}".strip()

    best, best_ranked, best_score, best_country = None, 0.0, 0.0, None

    for country in route_storefronts(title, artist):
        results = await _get(SEARCH_URL, {
            "term":    term,
            "media":   "music",
            "entity":  "song",
            "limit":   limit,
            "country": country,
        })

        cand, ranked, score = _best_candidate(title, artist, results, limit)
        if ranked > best_ranked:
            best, best_ranked, best_score, best_country = cand, ranked, score, country

        if cand is not None and ranked >= SEARCH_MATCH_THRESHOLD:
            log.info("iTunes match on %s (score=%.3f): %s / %s",
                     country, score, cand.get("trackName"), cand.get("artistName"))
            return [_to_track(cand, similarity=score)]

    # 모든 스토어프론트를 다 본 뒤의 최후 채택
    if best is not None and best_ranked >= WEAK_MATCH_THRESHOLD:
        log.info("iTunes weak match on %s (score=%.3f): %s",
                 best_country, best_score, best.get("trackName"))
        return [_to_track(best, similarity=best_score)]

    # 틀린 곡을 주는 것보다 아무것도 안 주는 게 낫다
    log.info("iTunes: no acceptable match for '%s' / '%s' (best=%.3f)",
             title, artist, best_score)
    return []


async def lookup_by_id(track_id: str, country: str | None = None) -> Track | None:
    """country를 주면 그 스토어프론트의 표기로 받는다.

    country=None이면 iTunes 기본값(US)이라 한국어/일본어 곡은 영문 표기가 온다.
    영문 표기가 필요한 자리에서는 country="US"를 명시적으로 주는 편이 낫다.
    """
    results = await _get(LOOKUP_URL, {
        "id":      track_id,
        "media":   "music",
        "country": country,
    })
    if not results:
        return None
    return _to_track(results[0])
