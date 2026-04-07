import httpx
import re


async def resolve_url(url: str) -> str:
    """
    단축 URL을 최종 URL로 변환.
    예: kko.to/xxx      → https://www.melon.com/song/detail.htm?songId=xxx
        flomuz.io/s/xxx → https://www.music-flo.com/detail/track/xxx/trackList.html
    """
    try:
        async with httpx.AsyncClient(follow_redirects=True, timeout=5) as client:
            res = await client.get(url)
            final_url = str(res.url)

            # FLO share URL 처리 (share.music-flo.com → 실제 track ID 추출)
            if "share.music-flo.com" in final_url:
                match = re.search(r'/detail/track/(\d+)', res.text)
                if match:
                    track_id = match.group(1)
                    return f"https://www.music-flo.com/detail/track/{track_id}/trackList.html"
                raise ValueError("FLO track ID를 찾을 수 없습니다.")

            return final_url

    except Exception as e:
        raise ValueError(f"URL 리다이렉트 실패: {e}")


def extract_platform_id(url: str) -> dict | None:
    """
    URL에서 플랫폼 종류와 ID 추출.
    반환: { "platform": "spotify", "id": "0VjIjW4GlUZAMYd2vXMi3b" }
    """
    patterns = [
        # Spotify
        ("spotify",      r"open\.spotify\.com/track/([A-Za-z0-9]+)"),
        # Apple Music - /album/.../albumId?i=trackId
        ("appleMusic",   r"music\.apple\.com/[a-z]+/album/[^/]+/\d+\?i=(\d+)"),
        # Apple Music - /song/제목/trackId
        ("appleMusic",   r"music\.apple\.com/[a-z]+/song/[^/]+/(\d+)"),
        # YouTube Music
        ("youtubeMusic", r"music\.youtube\.com/watch\?v=([A-Za-z0-9_-]+)"),
        # YouTube
        ("youtube",      r"(?:youtube\.com/watch\?v=|youtu\.be/)([A-Za-z0-9_-]+)"),
        # Melon
        ("melon",        r"melon\.com/.*[?&]songId=(\d+)"),
        # Bugs
        ("bugs",         r"(?:music|m)\.bugs\.co\.kr/track/(\d+)"),
        # FLO
        ("flo",          r"music-flo\.com/detail/track/(\d+)"),
        # Amazon
        ("amazon",       r"music\.amazon\.com/tracks/([A-Za-z0-9]+)"),
    ]

    for platform, pattern in patterns:
        m = re.search(pattern, url)
        if m:
            return {"platform": platform, "id": m.group(1)}

    return None