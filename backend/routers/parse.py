import sys
import os
import asyncio
from fastapi import APIRouter, HTTPException
from models.schemas import ParseRequest, ParseResponse, PlatformIds
from utils.url_resolver import resolve_url, extract_platform_id
from services.itunes import search_itunes
from services.melon import search_melon
from services.bugs import search_bugs
from services.flo import search_flo
from services.youtube import search_youtube_mv, search_youtube_music
from services.musicbrainz import get_english_candidates

router = APIRouter()


async def get_song_info_from_platform(platform: str, song_id: str) -> dict | None:
    """
    플랫폼 + ID로 곡 정보 조회.
    반환: { "title", "artist", "album", "albumArt" }
    """

    if platform == "appleMusic":
        import httpx
        try:
            async with httpx.AsyncClient(timeout=5) as client:
                res = await client.get(
                    "https://itunes.apple.com/lookup",
                    params={"id": song_id, "media": "music"}
                )
                data = res.json().get("results", [])
                if data:
                    track = data[0]
                    artwork = track.get("artworkUrl100", "").replace("100x100bb", "600x600bb")
                    return {
                        "title":    track.get("trackName", ""),
                        "artist":   track.get("artistName", ""),
                        "album":    track.get("collectionName", ""),
                        "albumArt": artwork,
                    }
        except Exception as e:
            print(f"[Parse] iTunes lookup 실패: {e}")
        return None

    if platform == "melon":
        import requests
        from bs4 import BeautifulSoup
        try:
            res = requests.get(
                f"https://www.melon.com/song/detail.htm?songId={song_id}",
                headers={"User-Agent": "Chrome"},
                timeout=5
            )
            print(f"[Melon] status: {res.status_code}")
            doc = BeautifulSoup(res.text, "html.parser")
            title  = doc.select_one("div.song_name strong")
            artist = doc.select_one("div.artist_name span.ellipsis")
            album  = doc.select_one("div.song_info dl dd.ellipsis")
            art    = doc.select_one("div.thumb img")
            print(f"[Melon] title: {title}, artist: {artist}")
            if title and artist:
                return {
                    "title":    title.text.strip(),
                    "artist":   artist.text.strip(),
                    "album":    album.text.strip() if album else None,
                    "albumArt": art.get("src") if art else None,
                }
        except Exception as e:
            print(f"[Parse] Melon 크롤링 실패: {e}")
        return None

    if platform == "bugs":
        import requests
        from bs4 import BeautifulSoup
        try:
            res = requests.get(
                f"https://music.bugs.co.kr/track/{song_id}",
                headers={"User-Agent": "Mozilla/5.0"},
                timeout=5
            )
            doc = BeautifulSoup(res.text, "html.parser")
            title  = doc.select_one("h1.title")
            artist = doc.select_one("p.artist a")
            album  = doc.select_one("a.album")
            art    = doc.select_one("div.thumbnail img")
            if title and artist:
                return {
                    "title":    title.text.strip(),
                    "artist":   artist.text.strip(),
                    "album":    album.text.strip() if album else None,
                    "albumArt": art.get("src") if art else None,
                }
        except Exception as e:
            print(f"[Parse] Bugs 크롤링 실패: {e}")
        return None

    if platform == "flo":
        import httpx
        try:
            async with httpx.AsyncClient(timeout=5) as client:
                res = await client.get(
                    f"https://www.music-flo.com/api/meta/v1/track/{song_id}",
                    headers={
                        "User-Agent": "Mozilla/5.0",
                        "x-gm-os-type": "WEB",
                        "x-gm-app-name": "FLO_WEB",
                        "x-gm-app-version": "8.1.0",
                        "x-gm-access-token": "",
                    }
                )
                data = res.json().get("data", {})
                if data:
                    img_list = data.get("album", {}).get("imgList", [])
                    artwork  = next((i["url"] for i in img_list if i["size"] == 500), None)
                    # 아티스트 여러 명이면 쉼표로 연결
                    artists  = ", ".join([a["name"] for a in data.get("artistList", [])])
                    return {
                        "title":    data.get("name", ""),
                        "artist":   artists,
                        "album":    data.get("album", {}).get("title", ""),
                        "albumArt": artwork,
                    }
        except Exception as e:
            print(f"[Parse] FLO API 실패: {e}")
        return None
    
    if platform in ("youtube", "youtubeMusic"):
        import httpx
        try:
            async with httpx.AsyncClient(timeout=5) as client:
                res = await client.get(
                    "https://www.googleapis.com/youtube/v3/videos",
                    params={
                        "part": "snippet",
                        "id":   song_id,
                        "key":  os.getenv("YOUTUBE_API_KEY"),
                    }
                )
                items = res.json().get("items", [])
                if items:
                    snippet    = items[0]["snippet"]
                    title      = snippet.get("title", "")
                    channel    = snippet.get("channelTitle", "")
                    # "The Weeknd - Blinding Lights (Official Video)" 형식에서 파싱
                    if " - " in title:
                        artist, song = title.split(" - ", 1)
                        # "(Official Video)" 등 제거
                        import re
                        song = re.sub(r'\s*[\(\[].*?[\)\]]', '', song).strip()
                    else:
                        artist = channel
                        song   = title
                    return {
                        "title":    song,
                        "artist":   artist,
                        "album":    None,
                        "albumArt": None,
                    }
        except Exception as e:
            print(f"[Parse] YouTube 곡 정보 실패: {e}")
    return None

    return None


async def get_all_platform_ids(title: str, artist: str,
                               known_platform: str, known_id: str) -> PlatformIds:
    ids = {
        "spotify":      None,
        "appleMusic":   None,
        "youtube":      None,
        "youtubeMusic": None,
        "melon":        None,
        "bugs":         None,
        "flo":          None,
        "amazon":       None,
    }
    ids[known_platform] = known_id

# 이미 ASCII(영어)면 MusicBrainz 스킵
    if title.isascii() and artist.isascii():
        en_title  = title
        en_artist = artist
        print(f"[Parse] 영어 곡 → MusicBrainz 스킵")
    else:
        candidates = get_english_candidates(title, artist)
        if candidates:
            en_title  = candidates[0]["english_title"]
            en_artist = candidates[0]["english_artist"]
            print(f"[Parse] 영어 제목 변환: {title} → {en_title}")

    async def fetch_apple():
        if ids["appleMusic"]:
            return
        result = await search_itunes(en_title, en_artist)
        if result:
            ids["appleMusic"] = result["appleMusic_id"]
            print(f"[Parse] Apple Music ID: {ids['appleMusic']}")

    async def fetch_melon():
        if ids["melon"]:
            return
        results = await asyncio.to_thread(search_melon, en_title, en_artist)
        if results and results[0].similarity >= 0.5:
            ids["melon"] = results[0].songId
            print(f"[Parse] Melon ID: {ids['melon']}")

    async def fetch_bugs():
        if ids["bugs"]:
            return
        bug_id = await asyncio.to_thread(search_bugs, en_title, en_artist)
        if bug_id:
            ids["bugs"] = bug_id
            print(f"[Parse] Bugs ID: {ids['bugs']}")

    async def fetch_flo():
        if ids["flo"]:
            return
        flo_id = await search_flo(en_title, en_artist)
        if flo_id:
            ids["flo"] = flo_id
            print(f"[Parse] FLO ID: {ids['flo']}")

    async def fetch_youtube():
        # STEP 1: MV 검색
        mv_id = await search_youtube_mv(en_title, en_artist)
        if mv_id:
            ids["youtube"] = mv_id
            print(f"[Parse] YouTube MV ID: {mv_id}")

        # STEP 2: Topic 채널 음원 검색
        music_id = await search_youtube_music(en_title, en_artist)
        if music_id:
            ids["youtubeMusic"] = music_id
            print(f"[Parse] YouTube Music ID: {music_id}")
        elif mv_id:
            # Topic 채널 없으면 MV ID로 fallback
            ids["youtubeMusic"] = mv_id
            print(f"[Parse] YouTube Music ID: MV fallback → {mv_id}")

    await asyncio.gather(
        fetch_apple(),
        fetch_melon(),
        fetch_bugs(),
        fetch_flo(),
        fetch_youtube(),
    )

    return PlatformIds(**ids)


@router.post("/parse", response_model=ParseResponse)
async def parse_url(req: ParseRequest):

    url = req.url

    # STEP 1: 단축 URL 처리
    if "kko.to" in url or "flomuz.io" in url:
        try:
            url = await resolve_url(url)
            print(f"[Parse] 단축 URL 해제: {url}")
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))

    # STEP 2: 플랫폼 감지 + ID 추출
    parsed = extract_platform_id(url)
    if not parsed:
        raise HTTPException(status_code=400, detail="지원하지 않는 플랫폼입니다.")

    platform = parsed["platform"]
    song_id  = parsed["id"]
    print(f"[Parse] platform={platform}, id={song_id}")

    # STEP 3: 해당 플랫폼에서 곡 정보 조회
    song_info = await get_song_info_from_platform(platform, song_id)
    if not song_info:
        raise HTTPException(status_code=404, detail="곡 정보를 찾을 수 없습니다.")

    title    = song_info["title"]
    artist   = song_info["artist"]
    album    = song_info["album"]
    albumArt = song_info["albumArt"]

    print(f"[Parse] 곡 정보: {title} / {artist}")

    # STEP 4: 나머지 플랫폼 ID 조회
    platform_ids = await get_all_platform_ids(title, artist, platform, song_id)

    # Apple Music 결과에서 albumArt, album 업그레이드
    if not albumArt or not album:
        result = await search_itunes(title, artist)
        if result:
            if not albumArt:
                albumArt = result["albumArt"]
            if not album:
                album = result["album"]

    return ParseResponse(
        title     = title,
        artist    = artist,
        album     = album,
        albumArt  = albumArt,
        isrc      = None,
        platforms = platform_ids,
    )
