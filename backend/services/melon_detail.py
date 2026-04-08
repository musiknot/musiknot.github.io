import requests
from bs4 import BeautifulSoup

MELON_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Referer": "https://www.melon.com",
    "Accept-Language": "ko-KR,ko;q=0.9",
}

def get_melon_song_info(song_id: str) -> dict | None:
    try:
        res = requests.get(
            f"https://www.melon.com/song/detail.htm?songId={song_id}",
            headers=MELON_HEADERS,
            timeout=5
        )
        res.raise_for_status()
    except Exception as e:
        print(f"[Melon Detail] 요청 실패: {e}")
        return None

    doc = BeautifulSoup(res.text, "html.parser")
    title  = doc.select_one("div.song_name strong")
    artist = doc.select_one("div.artist_name span.ellipsis")
    album  = doc.select_one("div.song_info dl dd.ellipsis")
    art    = doc.select_one("div.thumb img")

    print(f"[Melon Detail] title: {title}")
    print(f"[Melon Detail] artist: {artist}")

    if not title or not artist:
        return None

    return {
        "title":    title.text.strip(),
        "artist":   artist.text.strip(),
        "album":    album.text.strip() if album else None,
        "albumArt": art.get("src") if art else None,
    }

if __name__ == "__main__":
    result = get_melon_song_info("601555642")
    print(result)