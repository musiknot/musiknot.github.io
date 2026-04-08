import requests
import re
from bs4 import BeautifulSoup
from difflib import SequenceMatcher
from models.schemas import SongResult

MELON_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
    "Accept-Language": "ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7",
    "Accept-Encoding": "gzip, deflate, br",
    "Connection": "keep-alive",
    "Referer": "https://www.melon.com",
    "Upgrade-Insecure-Requests": "1",
}

def similarity(a: str, b: str) -> float:
    return SequenceMatcher(None, a.lower().strip(), b.lower().strip()).ratio()


def calc_score(inp_title: str, inp_artist: str,
               res_title: str, res_artist: str) -> float:
    t = similarity(inp_title,  res_title)
    a = similarity(inp_artist, res_artist)
    # 제목 60% + 아티스트 40% 가중 평균
    return round(t * 0.6 + a * 0.4, 4)


def search_melon(title: str, artist: str, limit: int = 5) -> list[SongResult]:
    url = f'https://www.melon.com/search/song/index.htm?q={title}'

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

def get_melon_info_by_id(song_id: str) -> dict | None:
    """
    멜론 songId로 곡 정보(제목, 아티스트, 앨범명, 앨범아트 URL)를 조회한다.

    1차: 곡 상세 페이지(song/detail.htm)를 직접 호출 (정확도 100%, 봇 탐지 위험 낮음)
    2차: 검색 페이지(search/song/index.htm)를 폴백으로 사용 (파라미터 완비)
    """

    # ── 공통 세션 및 헤더 설정 ──────────────────────────────
    session = requests.Session()
    headers = {
        **MELON_HEADERS,
        "Referer": "https://www.melon.com/",
    }

    # 메인 페이지를 먼저 방문하여 세션 쿠키 확보 (봇 탐지 우회)
    try:
        session.get("https://www.melon.com", headers=headers, timeout=5)
    except requests.RequestException:
        pass  # 쿠키 확보 실패해도 본 요청은 시도

    # ── 1차 시도: 곡 상세 페이지 직접 접근 ──────────────────
    detail_url = f"https://www.melon.com/song/detail.htm?songId={song_id}"
    try:
        res = session.get(detail_url, headers=headers, timeout=10)
        res.raise_for_status()
        print(f"[Melon][Detail] HTTP {res.status_code}, 길이={len(res.text)}")
        print(f"[Melon][Detail] HTML 앞부분: {res.text[:300]}")

        doc = BeautifulSoup(res.text, "html.parser")

        # 곡 제목: <div class="song_name"> 안의 텍스트 (앞에 "곡명" 라벨 포함)
        title_el  = doc.select_one("div.song_name")
        artist_el = doc.select_one("div.artist a")
        album_el  = doc.select_one("div.meta dd a")          # 첫 번째 dd > a 가 앨범명
        img_el    = doc.select_one("div.thumb img")           # 앨범아트 이미지

        if title_el and artist_el:
            title_text = title_el.get_text(strip=True)
            # "곡명" 라벨이 포함되어 있을 수 있으므로 제거
            title_text = title_text.replace("곡명", "").strip()

            result = {
                "title":     title_text,
                "artist":    artist_el.get_text(strip=True),
                "album":     album_el.get_text(strip=True) if album_el else None,
                "image_url": img_el["src"] if img_el and img_el.get("src") else None,
            }
            print(f"[Melon][Detail] 파싱 성공: {result}")
            return result

        print("[Melon][Detail] 상세 페이지 파싱 실패, 검색 폴백으로 전환")

    except requests.RequestException as e:
        print(f"[Melon][Detail] 요청 실패: {e}, 검색 폴백으로 전환")

    # ── 2차 시도: 검색 페이지 폴백 (파라미터 완비) ───────────
    search_url = "https://www.melon.com/search/song/index.htm"
    search_params = {
        "q":            song_id,
        "section":      "",
        "searchGnbYn":  "Y",
        "kkoSpl":       "Y",
        "kkoDpType":    "",
        "mwkLogType":   "T",
    }

    try:
        res = session.get(
            search_url, params=search_params, headers=headers, timeout=10
        )
        res.raise_for_status()
        print(f"[Melon][Search] HTTP {res.status_code}, 길이={len(res.text)}")
        print(f"[Melon][Search] HTML 앞부분: {res.text[:300]}")

        doc = BeautifulSoup(res.text, "html.parser")

        # 검색 결과 테이블의 각 행을 순회하며 songId 일치 항목을 찾는다
        for row in doc.select("table tbody tr"):
            btn = row.select_one("button[data-song-no]")
            if not btn:
                continue
            if btn["data-song-no"] != str(song_id):
                continue

            # 곡 제목
            title_el = row.select_one("a.fc_gray")
            # 아티스트
            artist_el = row.select_one("div.ellipsis.rank02 a")
            # 앨범명
            album_el = row.select_one("div.ellipsis.rank03 a")
            # 앨범아트
            img_el = row.select_one("img")

            if not title_el:
                continue

            result = {
                "title":     title_el.get_text(strip=True),
                "artist":    artist_el.get_text(strip=True) if artist_el else None,
                "album":     album_el.get_text(strip=True) if album_el else None,
                "image_url": img_el["src"] if img_el and img_el.get("src") else None,
            }
            print(f"[Melon][Search] 파싱 성공: {result}")
            return result

        print("[Melon][Search] 검색 결과에서 일치하는 songId를 찾지 못함")

    except requests.RequestException as e:
        print(f"[Melon][Search] 요청 실패: {e}")

    return None
