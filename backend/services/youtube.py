import logging
import os
import re

import httpx
from dotenv import load_dotenv

from models.schemas import Platform, Track

load_dotenv()
log = logging.getLogger(__name__)

SEARCH_URL = "https://www.googleapis.com/youtube/v3/search"
VIDEOS_URL = "https://www.googleapis.com/youtube/v3/videos"


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


async def search_mv(title: str, artist: str) -> Track | None:
    """공식 MV 영상 검색."""
    api_key = _api_key()
    if not api_key:
        log.warning("YOUTUBE_API_KEY not configured")
        return None

    try:
        async with httpx.AsyncClient(timeout=5) as client:
            res = await client.get(SEARCH_URL, params={
                "part":            "snippet",
                "q":               f"{title} {artist} official MV",
                "type":            "video",
                "videoCategoryId": "10",
                "maxResults":      5,
                "key":             api_key,
            })
            res.raise_for_status()
            items = res.json().get("items", [])
    except httpx.HTTPError as e:
        log.warning("YouTube MV search failed: %s", e)
        return None

    if not items:
        return None

    snippet  = items[0]["snippet"]
    video_id = items[0]["id"].get("videoId")
    if not video_id:
        return None
    return _to_track(video_id, snippet.get("title", ""), snippet.get("channelTitle", ""))


async def search_topic(title: str, artist: str) -> Track | None:
    """Topic 채널(자동 생성된 음원 영상) 검색. 없으면 None."""
    api_key = _api_key()
    if not api_key:
        log.warning("YOUTUBE_API_KEY not configured")
        return None

    try:
        async with httpx.AsyncClient(timeout=5) as client:
            res = await client.get(SEARCH_URL, params={
                "part":            "snippet",
                "q":               f"{title} {artist}",
                "type":            "video",
                "videoCategoryId": "10",
                "maxResults":      10,
                "key":             api_key,
            })
            res.raise_for_status()
            items = res.json().get("items", [])
    except httpx.HTTPError as e:
        log.warning("YouTube Topic search failed: %s", e)
        return None

    for item in items:
        channel = item["snippet"].get("channelTitle", "")
        if "- Topic" not in channel:
            continue
        video_id = item["id"].get("videoId")
        if video_id:
            return _to_track(video_id, item["snippet"].get("title", ""), channel)

    return None


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
