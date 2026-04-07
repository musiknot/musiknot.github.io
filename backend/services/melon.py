import requests
import re
from bs4 import BeautifulSoup
from difflib import SequenceMatcher
from models.schemas import SongResult

MELON_HEADERS = {"User-Agent": "Chrome"}


def similarity(a: str, b: str) -> float:
    return SequenceMatcher(None, a.lower().strip(), b.lower().strip()).ratio()


def calc_score(inp_title: str, inp_artist: str,
               res_title: str, res_artist: str) -> float:
    t = similarity(inp_title,  res_title)
    a = similarity(inp_artist, res_artist)
    # 제목 60% + 아티스트 40% 가중 평균
    return round(t * 0.6 + a * 0.4, 4)


def search_melon(title: str, artist: str, limit: int = 5) -> list[SongResult]:
    url = f'https://www.melon.com/search/song/index.htm?q="{title}"'

    try:
        res = requests.get(url, headers=MELON_HEADERS, timeout=5)
        res.raise_for_status()
    except requests.RequestException:
        return []

    doc = BeautifulSoup(res.text, "html.parser")
    results = []

    for row in doc.select("tr"):
        btn = row.select_one("button[data-song-no]")
        if not btn:
            continue

        song_id   = btn.get("data-song-no")
        title_el  = row.select_one("a.fc_gray[title]")
        artist_el = row.select_one("a.fc_mgray")
        album_el  = row.find("a", href=re.compile(r"goAlbumDetail"))

        if not title_el or not artist_el:
            continue

        res_title  = title_el.text.strip()
        res_artist = artist_el.text.strip()
        res_album  = album_el.text.strip() if album_el else None

        print(f"[Melon] title.text='{res_title}' / title속성='{title_el.get('title')}'")

        score = calc_score(title, artist, res_title, res_artist)

        results.append(SongResult(
            songId     = song_id,
            title      = res_title,
            artist     = res_artist,
            album      = res_album,
            similarity = score
        ))

        if len(results) >= limit:
            break

    return sorted(results, key=lambda x: x.similarity, reverse=True)


def merge_results(a: list[SongResult],
                  b: list[SongResult]) -> list[SongResult]:
    seen, merged = set(), []
    for r in sorted(a + b, key=lambda x: x.similarity, reverse=True):
        if r.songId not in seen:
            seen.add(r.songId)
            merged.append(r)
    return merged