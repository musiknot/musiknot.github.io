import requests
import re
from bs4 import BeautifulSoup
from difflib import SequenceMatcher

BUGS_HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"}


def similarity(a: str, b: str) -> float:
    return SequenceMatcher(None, a.lower().strip(), b.lower().strip()).ratio()


def calc_score(inp_title: str, inp_artist: str,
               res_title: str, res_artist: str) -> float:
    t = similarity(inp_title,  res_title)
    a = similarity(inp_artist, res_artist)
    return round(t * 0.6 + a * 0.4, 4)


def search_bugs(title: str, artist: str, limit: int = 5) -> str | None:
    """
    Bugs 검색으로 track ID 반환.
    반환: "5812157" 또는 None
    """
    url = f"https://music.bugs.co.kr/search/track?q={title}"

    try:
        res = requests.get(url, headers=BUGS_HEADERS, timeout=5)
        res.raise_for_status()
    except requests.RequestException as e:
        print(f"[Bugs] 요청 실패: {e}")
        return None

    doc = BeautifulSoup(res.text, "html.parser")

    best_id    = None
    best_score = 0.0

    for row in doc.select("tr[trackid]"):
        track_id   = row.get("trackid")
        title_el   = row.select_one("p.title a[title]")
        artist_el  = row.select_one("p.artist a[title]")

        if not title_el or not artist_el:
            continue

        res_title  = title_el.get("title", "").strip()
        res_artist = artist_el.get("title", "").strip()

        # 아티스트명에서 한국어 표기 제거 (예: "The Weeknd(위켄드)" → "The Weeknd")
        res_artist = re.sub(r'\(.*?\)', '', res_artist).strip()

        score = calc_score(title, artist, res_title, res_artist)
        print(f"[Bugs] {res_title} / {res_artist} → score={score}")

        if score > best_score:
            best_score = score
            best_id    = track_id

        if len(doc.select("tr[trackId]")) >= limit:
            break

    if not best_id or best_score < 0.5:
        print(f"[Bugs] 매칭 실패: best_score={best_score}")
        return None

    print(f"[Bugs] 최종 매칭: trackId={best_id} (score={best_score})")
    return best_id