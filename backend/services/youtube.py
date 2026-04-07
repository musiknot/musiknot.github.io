import asyncio
import httpx
import os
from dotenv import load_dotenv

load_dotenv()

YOUTUBE_API_KEY = os.getenv("YOUTUBE_API_KEY")


async def search_youtube_mv(title: str, artist: str) -> str | None:
    """
    YouTube Data API로 MV video ID 검색.
    반환: "4NRXx6U8ABQ" 또는 None
    """
    if not YOUTUBE_API_KEY:
        print("[YouTube] API 키 없음")
        return None

    try:
        async with httpx.AsyncClient(timeout=5) as client:
            res = await client.get(
                "https://www.googleapis.com/youtube/v3/search",
                params={
                    "part":            "snippet",
                    "q":               f"{title} {artist} official MV",
                    "type":            "video",
                    "videoCategoryId": "10",
                    "maxResults":      5,
                    "key":             YOUTUBE_API_KEY,
                }
            )
            res.raise_for_status()
            items = res.json().get("items", [])
    except Exception as e:
        print(f"[YouTube] 요청 실패: {e}")
        return None

    if not items:
        print("[YouTube] 검색 결과 없음")
        return None

    video_id = items[0]["id"]["videoId"]
    print(f"[YouTube] MV 매칭: {items[0]['snippet']['title']} → {video_id}")
    return video_id


async def search_youtube_music(title: str, artist: str) -> str | None:
    """
    YouTube Data API로 Topic 채널 음원 video ID 검색.
    반환: "J7p4bzqLvCw" 또는 None
    """
    if not YOUTUBE_API_KEY:
        print("[YouTube Music] API 키 없음")
        return None

    try:
        async with httpx.AsyncClient(timeout=5) as client:
            res = await client.get(
                "https://www.googleapis.com/youtube/v3/search",
                params={
                    "part":            "snippet",
                    "q":               f"{title} {artist}",
                    "type":            "video",
                    "videoCategoryId": "10",
                    "maxResults":      10,
                    "key":             YOUTUBE_API_KEY,
                }
            )
            res.raise_for_status()
            items = res.json().get("items", [])
    except Exception as e:
        print(f"[YouTube Music] 요청 실패: {e}")
        return None

    if not items:
        print("[YouTube Music] 검색 결과 없음")
        return None

    # Topic 채널 영상 우선
    for item in items:
        channel  = item["snippet"]["channelTitle"]
        video_id = item["id"]["videoId"]
        print(f"[YouTube Music] {item['snippet']['title']} / {channel} → {video_id}")

        if "- Topic" in channel:
            print(f"[YouTube Music] Topic 채널 매칭: {channel} → {video_id}")
            return video_id

    # Topic 채널 없으면 None 반환
    print("[YouTube Music] Topic 채널 없음")
    return None
