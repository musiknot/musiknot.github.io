from fastapi import FastAPI
from pydantic import BaseModel
from bs4 import BeautifulSoup
from difflib import SequenceMatcher
import requests
import re
import musicbrainzngs

app = FastAPI()

MELON_HEADERS = {"User-Agent": "Chrome"}
musicbrainzngs.set_useragent("MyMelonApp", "1.0", "contact@example.com")


# ── 모델 정의 ─────────────────────────────────────────

class SongRequest(BaseModel):
    title:    str
    artist:   str
    album:    str | None = None
    track_no: int | None = None


class SongResult(BaseModel):
    songId:     str
    title:      str
    artist:     str
    album:      str | None
    similarity: float


class SearchResponse(BaseModel):
    status:  str          # "exact" | "multiple" | "not_found"
    results: list[SongResult]


# ── 유사도 계산 ───────────────────────────────────────

def similarity(a: str, b: str) -> float:
    return SequenceMatcher(None, a.lower().strip(), b.lower().strip()).ratio()


def calc_score(inp_title: str, inp_artist: str,
               res_title: str, res_artist: str) -> float:
    t = similarity(inp_title,  res_title)
    a = similarity(inp_artist, res_artist)
    # 제목 60% + 아티스트 40% 가중 평균
    return round(t * 0.6 + a * 0.4, 4)


# ── 멜론 검색 ─────────────────────────────────────────

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

        # ← 여기 추가
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


# ── MusicBrainz 영어 제목 후보 수집 ──────────────────

def normalize_artist_name(name: str) -> str:
    if "," in name:
        parts = [p.strip() for p in name.split(",", 1)]
        return f"{parts[1]} {parts[0]}"
    return name


def get_english_candidates(title: str, artist: str) -> list[dict]:
    try:
        result = musicbrainzngs.search_recordings(
            recording=title,
            artist=artist,
            limit=5
        )
    except musicbrainzngs.WebServiceError as e:
        print(f"[MusicBrainz] WebServiceError: {e}")
        return []

    for rec in result.get("recording-list", []):
        print(f"[MusicBrainz] video={rec.get('video')}, score={rec.get('ext:score')}, title={rec.get('title')}")

        if rec.get("video") == "true":
            print("[MusicBrainz] → 뮤직비디오라 제외")
            continue
        if int(rec.get("ext:score", 0)) < 70:
            print("[MusicBrainz] → score 70 미만이라 제외")
            continue

        artist_info = rec.get("artist-credit", [{}])[0].get("artist", {})

        # 영어 아티스트명: sort-name 뒤집기 우선 적용
        en_artist = normalize_artist_name(artist_info.get("sort-name", ""))
        print(f"[MusicBrainz] sort-name 기반 아티스트: {en_artist}")

        # locale=en alias가 있으면 덮어씌움
        for alias in artist_info.get("alias-list", []):
            print(f"[MusicBrainz] alias 확인: locale={alias.get('locale')}, primary={alias.get('primary')}, name={alias.get('name')}")
            if alias.get("locale") == "en" and alias.get("primary") == "primary":
                en_artist = alias.get("name", en_artist)
                print(f"[MusicBrainz] → locale=en alias 발견: {en_artist}")
                break

        # 영어 제목 후보 수집
        seen_titles = set()
        candidates  = []

        for release in rec.get("release-list", []):
            status = release.get("status", "")
            disam  = release.get("disambiguation", "")
            is_en  = (
                status == "Pseudo-Release" or
                "北米" in disam or
                release.get("artist-credit", [{}])[0]
                       .get("name", "").isascii()
            )
            if is_en:
                try:
                    track_title = (
                        release["medium-list"][0]["track-list"][0]["title"]
                    )
                    if track_title.isascii() and track_title not in seen_titles:
                        seen_titles.add(track_title)
                        candidates.append({
                            "english_title":  track_title,
                            "english_artist": en_artist
                        })
                        print(f"[MusicBrainz] → 후보 추가: {track_title} / {en_artist}")
                except (KeyError, IndexError):
                    pass

        if candidates:
            return candidates

        print("[MusicBrainz] → 영어 제목 없음")
        return []

    print("[MusicBrainz] → 결과 없음")
    return []

# ── 검색 결과 병합 및 중복 제거 ───────────────────────

def merge_results(a: list[SongResult],
                  b: list[SongResult]) -> list[SongResult]:
    seen, merged = set(), []
    for r in sorted(a + b, key=lambda x: x.similarity, reverse=True):
        if r.songId not in seen:
            seen.add(r.songId)
            merged.append(r)
    return merged


# ── 엔드포인트 ────────────────────────────────────────

@app.post("/match", response_model=SearchResponse)
async def match_song(req: SongRequest):

    # STEP 1: 원제 그대로 멜론 검색 (K-POP / POP은 대부분 여기서 해결)
    results = search_melon(req.title, req.artist)
    best    = results[0] if results else None

    if best and best.similarity >= 0.85:
        return SearchResponse(status="exact", results=[best])

    # STEP 2: MusicBrainz 영어 제목 후보 각각 검색 후 최고 유사도 선택
    candidates = get_english_candidates(req.title, req.artist)

    for candidate in candidates:
        en_title  = candidate["english_title"]
        en_artist = candidate["english_artist"]
        print(f"[MusicBrainz] 후보 검색 중: {en_title} / {en_artist}")

        results2 = search_melon(en_title, en_artist)
        best2    = results2[0] if results2 else None

        if best2:
            print(f"[MusicBrainz] 후보 결과: {best2.title} / similarity={best2.similarity}")

        # 후보 중 하나라도 threshold 넘으면 바로 반환
        if best2 and best2.similarity >= 0.85:
            return SearchResponse(status="exact", results=[best2])

        # threshold 못 넘어도 결과 병합해서 유지
        results = merge_results(results, results2)

    # STEP 3: 최대 5개 후보 반환 → 프론트엔드에서 유저가 선택
    if results:
        return SearchResponse(status="multiple", results=results[:5])

    # 결과 없음
    return SearchResponse(status="not_found", results=[])