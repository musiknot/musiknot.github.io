from difflib import SequenceMatcher

# 매칭 임계값 — 한 곳에서만 관리
SEARCH_MATCH_THRESHOLD = 0.5      # 외부 플랫폼 검색 결과 채택 경계
EXACT_MATCH_THRESHOLD  = 0.85     # /match에서 단일 결과로 확정하는 경계
MUSICBRAINZ_MIN_SCORE  = 70       # MusicBrainz ext:score 컷오프


def similarity(a: str, b: str) -> float:
    return SequenceMatcher(None, a.lower().strip(), b.lower().strip()).ratio()


def calc_score(inp_title: str, inp_artist: str,
               res_title: str, res_artist: str) -> float:
    """제목 60% + 아티스트 40% 가중 평균."""
    t = similarity(inp_title,  res_title)
    a = similarity(inp_artist, res_artist)
    return round(t * 0.6 + a * 0.4, 4)
