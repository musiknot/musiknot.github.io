import logging
import os
import re

import httpx
from dotenv import load_dotenv

from core.scoring import route_storefronts
from models.schemas import Platform, Track

load_dotenv()
log = logging.getLogger(__name__)

SEARCH_URL = "https://www.googleapis.com/youtube/v3/search"
VIDEOS_URL = "https://www.googleapis.com/youtube/v3/videos"

# search.list 는 호출당 100 유닛이고 기본 할당량이 10,000/일이다.
# 예전에는 MV용과 Topic용으로 두 번 검색해서 하루 50 파싱이 상한이었다.
# 한 번 검색해 결과 목록에서 둘 다 골라내면 상한이 100 파싱으로 두 배가 된다.
SEARCH_QUOTA_COST = 100
MAX_RESULTS       = 10

# 스토어프론트 → (regionCode, relevanceLanguage)
# 공식 MV 는 원어 제목으로 올라오므로, 지역/언어를 주면 관련도가 올라간다.
_REGION_BY_STOREFRONT = {
    "KR": ("KR", "ko"),
    "JP": ("JP", "ja"),
    "US": (None, None),
}

# 제목에 이게 있으면 공식 뮤직비디오일 가능성이 높다.
# 예전에는 질의어에 'official MV' 를 붙여서 같은 효과를 냈는데, 그러면
# Topic 채널 결과가 밀려나서 검색을 두 번 해야 했다. 질의는 중립적으로 두고
# 편향은 여기서 준다.
_MV_MARKERS = re.compile(
    r"\b(?:m/?v|official\s+(?:music\s+)?video|music\s+video)\b|뮤직비디오|ミュージックビデオ",
    re.IGNORECASE,
)


def _api_key() -> str | None:
    """호출 시점에 env 조회 — import 타이밍 의존 회피."""
    return os.getenv("YOUTUBE_API_KEY")


def _to_track(video_id: str, title: str, channel: str) -> Track:
    return Track(
        platform = Platform.YOUTUBE,
        track_id = video_id,
        title    = title,
        artist   = channel,
    )


def _is_topic(channel: str) -> bool:
    """YouTube 가 음원 라이선스용으로 자동 생성하는 채널."""
    return "- Topic" in (channel or "")


def pick_mv_and_topic(items: list[dict]) -> tuple[Track | None, Track | None]:
    """검색 결과 하나에서 (MV, Topic) 후보를 고른다.

    순수 함수다 — 네트워크도 API 키도 필요 없어서 그대로 테스트할 수 있다.

    MV 선택 순서:
      1) Topic 채널이 아니면서 제목에 MV 표지가 있는 첫 항목
      2) 그것도 없으면 Topic 채널이 아닌 첫 항목
    Topic 선택: 채널명에 '- Topic' 이 있는 첫 항목.
    """
    mv_marked: Track | None = None
    mv_any:    Track | None = None
    topic:     Track | None = None

    for item in items or []:
        video_id = (item.get("id") or {}).get("videoId")
        if not video_id:
            continue                      # 채널/재생목록 결과
        snippet = item.get("snippet") or {}
        vtitle  = snippet.get("title", "")
        channel = snippet.get("channelTitle", "")
        track   = _to_track(video_id, vtitle, channel)

        if _is_topic(channel):
            if topic is None:
                topic = track
            continue

        if mv_any is None:
            mv_any = track
        if mv_marked is None and _MV_MARKERS.search(vtitle):
            mv_marked = track

    return (mv_marked or mv_any), topic


async def search_mv_and_topic(title: str, artist: str) -> tuple[Track | None, Track | None]:
    """search.list 를 **한 번만** 호출해 (MV, Topic) 을 함께 돌려준다."""
    api_key = _api_key()
    if not api_key:
        log.warning("YOUTUBE_API_KEY not configured")
        return None, None

    region, lang = _REGION_BY_STOREFRONT.get(
        route_storefronts(title, artist)[0], (None, None))

    params = {
        "part":            "snippet",
        "q":               f"{artist} {title}".strip(),
        "type":            "video",
        "videoCategoryId": "10",
        "maxResults":      MAX_RESULTS,
        "key":             api_key,
    }
    if region:
        params["regionCode"]        = region
        params["relevanceLanguage"] = lang

    try:
        async with httpx.AsyncClient(timeout=5) as client:
            res = await client.get(SEARCH_URL, params=params)
            res.raise_for_status()
            items = res.json().get("items", [])
    except httpx.HTTPError as e:
        log.warning("YouTube search failed: %s", e)
        return None, None

    mv, topic = pick_mv_and_topic(items)
    log.info("YouTube search (region=%s, %d units): mv=%s topic=%s",
             region or "-", SEARCH_QUOTA_COST,
             mv.track_id if mv else None, topic.track_id if topic else None)
    return mv, topic


async def lookup_by_id(video_id: str) -> Track | None:
    """video ID로 곡 메타 추출. 제목에서 'Artist - Song' 패턴 파싱."""
    api_key = _api_key()
    if not api_key:
        log.warning("YOUTUBE_API_KEY not configured")
        return None

    try:
        async with httpx.AsyncClient(timeout=5) as client:
            res = await client.get(VIDEOS_URL, params={
                "part": "snippet",
                "id":   video_id,
                "key":  api_key,
            })
            res.raise_for_status()
            items = res.json().get("items", [])
    except httpx.HTTPError as e:
        log.warning("YouTube videos lookup failed: %s", e)
        return None

    if not items:
        return None

    snippet = items[0]["snippet"]
    raw_title = snippet.get("title", "")
    channel   = snippet.get("channelTitle", "")

    # "Artist - Song (Official Video)" 패턴 파싱
    if " - " in raw_title:
        artist, song = raw_title.split(" - ", 1)
        song = re.sub(r"\s*[\(\[].*?[\)\]]", "", song).strip()
    else:
        artist = channel
        song   = raw_title

    return Track(
        platform = Platform.YOUTUBE,
        track_id = video_id,
        title    = song,
        artist   = artist,
    )
