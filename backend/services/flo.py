import httpx
from difflib import SequenceMatcher

FLO_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:149.0) Gecko/20100101 Firefox/149.0",
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7",
    "x-gm-os-type": "WEB",
    "x-gm-app-name": "FLO_WEB",
    "x-gm-app-version": "8.1.0",
    "x-gm-os-version": "10",
    "x-gm-device-model": "Firefox, Windows 10",
    "x-gm-access-token": "",
}


def similarity(a: str, b: str) -> float:
    return SequenceMatcher(None, a.lower().strip(), b.lower().strip()).ratio()


def calc_score(inp_title: str, inp_artist: str,
               res_title: str, res_artist: str) -> float:
    t = similarity(inp_title,  res_title)
    a = similarity(inp_artist, res_artist)
    return round(t * 0.6 + a * 0.4, 4)


async def search_flo(title: str, artist: str, limit: int = 5) -> str | None:
    """
    FLO 내부 API로 track ID 반환.
    반환: "438092629" 또는 None
    """
    try:
        async with httpx.AsyncClient(timeout=5, headers=FLO_HEADERS) as client:
            res = await client.get(
                "https://www.music-flo.com/api/search/v2/search/integration",
                params={"keyword": f"{title} {artist}"}
            )
            res.raise_for_status()
            data = res.json()
    except Exception as e:
        print(f"[FLO] 요청 실패: {e}")
        return None

    # TRACK + TITLED 리스트 추출
    track_list = []
    for section in data.get("data", {}).get("list", []):
        if section.get("type") == "TRACK" and section.get("style") == "TITLED":
            track_list = section.get("list", [])
            break

    if not track_list:
        print("[FLO] 검색 결과 없음")
        return None

    best_id    = None
    best_score = 0.0

    for track in track_list[:limit]:
        track_id   = str(track.get("id", ""))
        res_title  = track.get("name", "")
        res_artist = track.get("representationArtist", {}).get("name", "")

        score = calc_score(title, artist, res_title, res_artist)
        print(f"[FLO] {res_title} / {res_artist} → score={score}")

        if score > best_score:
            best_score = score
            best_id    = track_id

    if not best_id or best_score < 0.5:
        print(f"[FLO] 매칭 실패: best_score={best_score}")
        return None

    print(f"[FLO] 최종 매칭: trackId={best_id} (score={best_score})")
    return best_id
