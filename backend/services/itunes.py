import httpx
from difflib import SequenceMatcher


def similarity(a: str, b: str) -> float:
    return SequenceMatcher(None, a.lower().strip(), b.lower().strip()).ratio()


async def search_itunes(title: str, artist: str, limit: int = 5) -> dict | None:
    """
    iTunes Search API로 곡 정보 조회.
    반환: {
        "appleMusic_id": "1499378607",
        "title":         "Blinding Lights",
        "artist":        "The Weeknd",
        "album":         "After Hours",
        "albumArt":      "https://is1-ssl.mzstatic.com/.../600x600bb.jpg",
    }
    """
    try:
        async with httpx.AsyncClient(timeout=5) as client:
            res = await client.get(
                "https://itunes.apple.com/search",
                params={
                    "term":   f"{title} {artist}",
                    "media":  "music",
                    "entity": "song",
                    "limit":  limit
                }
            )
            res.raise_for_status()
            results = res.json().get("results", [])
    except Exception as e:
        print(f"[iTunes] 요청 실패: {e}")
        return None

    if not results:
        return None

    # 제목 + 아티스트 유사도로 가장 일치하는 곡 선택
    best       = None
    best_score = 0.0

    for track in results:
        # (Live), (Remix), (Inst.) 등 변형 버전 제외
        track_name = track.get("trackName", "")
        if any(x in track_name for x in ["(Live)", "(Remix)", "(Inst.", "(MR)", "(Cover"]):
            continue

        title_score  = similarity(title,  track_name)
        artist_score = similarity(artist, track.get("artistName", ""))
        score = title_score * 0.6 + artist_score * 0.4

        # 싱글 버전 우선 보너스
        collection = track.get("collectionName", "")
        if "Single" in collection:
            score += 0.05

        if score > best_score:
            best_score = score
            best       = track

    if not best or best_score < 0.5:
        print(f"[iTunes] 유사도 낮음: {best_score}")
        return None

    # 앨범아트 고화질로 변환 (100x100 → 600x600)
    artwork = best.get("artworkUrl100", "")
    artwork = artwork.replace("100x100bb", "600x600bb")

    # Apple Music trackId 추출
    apple_id = str(best.get("trackId", ""))

    print(f"[iTunes] 매칭: {best.get('trackName')} / {best.get('artistName')} (score={best_score:.4f})")

    return {
        "appleMusic_id": apple_id,
        "title":         best.get("trackName", ""),
        "artist":        best.get("artistName", ""),
        "album":         best.get("collectionName", ""),
        "albumArt":      artwork,
    }


async def get_apple_music_id(title: str, artist: str) -> str | None:
    """Apple Music ID만 필요할 때 사용."""
    result = await search_itunes(title, artist)
    return result["appleMusic_id"] if result else None