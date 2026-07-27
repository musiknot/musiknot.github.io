"""곡 동일성 판정 — 번역 대신 '같은 문자체계 안에서' 비교한다.

문자열 유사도로 번역을 검증할 수는 없다. '물론' vs 'With you'는 0.0이지만
그건 "다른 곡"이 아니라 "정보 없음"이다. 그래서 번역을 검증하지 않고,
애초에 번역이 생기지 않게 한다 — iTunes `country` 파라미터가 스토어프론트뿐
아니라 메타데이터 언어까지 고른다는 사실을 이용해, 입력 문자체계와 같은
언어를 쓰는 스토어프론트에 질의한다(route_storefronts). 그러면 양쪽 문자열이
같은 문자체계가 되고 평범한 유사도가 다시 유효한 동일성 검사가 된다.

calc_score는 세 층으로 구성된다.
  1) 동일성  — NFKC + casefold + 공백/문장부호 제거. '버스커 버스커'와
     '버스커버스커', '옛사랑'과 '옛 사랑'을 같은 키로 만든다.
  2) 녹음본 구분 — 같은 곡·같은 가수라도 다른 녹음일 수 있다. 괄호/대괄호/
     ' - ' 꼬리표를 집합으로 뽑아 한쪽에만 있는 것에 벌점을 준다. 아는
     변형 표지(live/inst/remix/카라오케/오르골/여자키…)는 더 크게,
     모르는 꼬리표도 '정량화되지 않은 위험'으로 조금은 벌점을 준다.
  3) 결합    — 제목·아티스트의 곱(가중 지수). 선형 0.6/0.4 가중합은
     "아티스트가 다르니 커버다"라고 말할 수 없다 — 아티스트 0.4점의 손해를
     제목 0.6점으로 언제든 살 수 있기 때문이고, 카라오케 커버가 진짜 곡을
     이긴 경로가 정확히 그것이었다. 곱은 매수당하지 않는다.

주의: 아티스트 표기가 서로 다른 문자체계면(예: '지드래곤' vs 'G-DRAGON')
artist_score는 0이 되고 곡 전체가 0점 처리되어 '기권'한다. 틀린 링크(-1)보다
빈 슬롯(0)이 낫다는 판단이며, 로마자 변환 비교를 붙이기 전까지 유지한다.
"""
from __future__ import annotations

import re
import unicodedata
from difflib import SequenceMatcher

# ── 임계값 — 한 곳에서만 관리 ──────────────────────────
SEARCH_MATCH_THRESHOLD = 0.62     # 외부 플랫폼 검색 결과 채택 경계
WEAK_MATCH_THRESHOLD   = 0.55     # 모든 스토어프론트를 다 본 뒤의 최후 채택 경계
EXACT_MATCH_THRESHOLD  = 0.90     # /match에서 단일 결과로 확정하는 경계

# ── 점수 튜닝값 ────────────────────────────────────────
ARTIST_GATE   = 0.34    # 미만이면 다른 연주자 → 커버로 보고 0점
TITLE_GATE    = 0.34    # 미만이면 다른 곡 → 0점
RANK_TIEBREAK = 0.012   # 순위당 가산점. 메타데이터가 동일한 프레싱만 가른다
P_VARIANT     = 0.42    # 한쪽에만 있는 '아는' 변형 표지 1개당 벌점
P_UNKNOWN     = 0.22    # 한쪽에만 있는 '모르는' 꼬리표 1개당 벌점
P_ALBUM       = 0.25    # 앨범명에만 나타나는 변형 표지 1개당 벌점


# ── 문자체계 판별 ──────────────────────────────────────
_HANGUL = re.compile(r"[가-힣ᄀ-ᇿ㄰-㆏]")
_KANA   = re.compile(r"[぀-ヿｦ-ﾟ]")
_HAN    = re.compile(r"[㐀-䶿一-鿿豈-﫿]")


# ── 정규화 ─────────────────────────────────────────────
_PAREN       = re.compile(r"[\(\[\{（【][^\)\]\}）】]*[\)\]\}）】]?")
_QUAL        = re.compile(r"[\(\[\{（【]([^\)\]\}）】]*)[\)\]\}）】]?")
_FEAT        = re.compile(r"\s*(?:feat\.?|ft\.?|featuring|with)\s+.*$", re.IGNORECASE)
_FEAT_HEAD   = re.compile(r"^\s*(?:feat\.?|ft\.?|featuring|with|&|duet)\b", re.IGNORECASE)
_DASH_SUFFIX = re.compile(r"\s+[\-–—]\s+.*$")
_KEEP        = re.compile(r"[^0-9a-z぀-ヿ㐀-鿿가-힣]")
_WORDS       = re.compile(r"[0-9a-z぀-ヿ㐀-鿿가-힣]+")
_ARTIST_SPLIT = re.compile(
    r"[,&/×x·・;+]|\band\b|\bwith\b|\bfeat\.?\b|\bft\.?\b", re.IGNORECASE)


def _nfkc(s: str) -> str:
    return unicodedata.normalize("NFKC", s or "")


def norm(s: str) -> str:
    """동일성 키: NFKC + casefold + 글자/숫자/CJK 이외 전부 제거.
    공백·문장부호·전각 변형을 한 번에 없앤다."""
    return _KEEP.sub("", _nfkc(s).casefold())


def title_base(s: str) -> str:
    """괄호·feat 표기·' - ' 꼬리표를 뗀 제목 줄기."""
    t = _nfkc(s)
    t = _PAREN.sub(" ", t)
    t = _DASH_SUFFIX.sub("", t)
    t = _FEAT.sub("", t)
    return norm(t) or norm(s)


def route_storefronts(title: str, artist: str) -> list[str]:
    """시도할 스토어프론트 순서. 네이티브 우선, US는 항상 마지막 폴백.

    라우팅은 '핵심 제목'(꼬리표·feat 제거)과 '대표 아티스트'(첫 협연 구분자
    앞)만 본다. 다른 문자체계의 게스트 크레딧이 스토어프론트를 납치하면 안
    되기 때문이다 — 국내 플랫폼은 실제로 'Shape of You (Feat. 아무개)'처럼
    표기하고, 그걸 KR로 보내면 영어 곡을 잃는다.
    """
    t = _nfkc(title or "")
    t = _PAREN.sub(" ", t)
    t = _DASH_SUFFIX.sub("", t)
    t = _FEAT.sub("", t)
    a = _ARTIST_SPLIT.split(_nfkc(artist or ""))[0]
    blob = f"{t} {a}"
    if _HANGUL.search(blob):
        return ["KR", "US"]
    if _KANA.search(blob) or _HAN.search(blob):
        return ["JP", "US"]
    return ["US"]


# ── 변형 표지 어휘 — "같은 곡의 다른 녹음"을 뜻하는 말들 ──
# ASCII는 단어 경계로 매칭한다('Alive'가 'live'로 읽히면 안 된다).
# CJK는 단어 경계가 없으므로 부분 문자열로 매칭한다.
_VARIANT_ASCII: dict[str, tuple[str, ...]] = {
    "live":     ("live", "concert", "tour", "unplugged", "session", "rehearsal"),
    "inst":     ("instrumental", "inst", "mr", "off vocal", "offvocal",
                 "karaoke", "backing", "accompaniment", "playback"),
    "remix":    ("remix", "mix", "bootleg", "rework", "edit", "nightcore",
                 "sped up", "spedup", "slowed", "bpm", "extended", "dub"),
    "version":  ("version", "ver", "rerecorded", "re recorded", "reimagined"),
    "cover":    ("cover", "tribute", "made famous", "made popular",
                 "originally performed", "in the style of", "as made", "performed by"),
    "acoustic": ("acoustic", "unplugged"),
    "piano":    ("piano", "orgel", "music box", "musicbox", "8 bit", "8bit",
                 "chiptune", "lullaby", "violin", "guitar", "strings", "kalimba"),
    "acap":     ("a cappella", "acappella"),
    "demo":     ("demo",),
}
_VARIANT_CJK: dict[str, tuple[str, ...]] = {
    "live":     ("라이브", "ライブ", "독창회", "실황"),
    "inst":     ("반주", "카라오케", "노래방", "여자키", "남자키", "엘프", "연주곡"),
    "remix":    ("리믹스", "リミックス", "버전"),
    "cover":    ("커버", "カバー", "원곡"),
    "acoustic": ("어쿠스틱", "アコースティック"),
    "piano":    ("피아노", "ピアノ", "オルゴール", "오르골"),
}
_ASCII_RE = {
    name: re.compile(r"\b(?:%s)\b" % "|".join(re.escape(n) for n in needles))
    for name, needles in _VARIANT_ASCII.items()
}

# 녹음본 자체를 바꾸지 않는 단어들
_BENIGN_WORDS = {
    "remaster", "remastered", "remastering", "deluxe", "edition", "explicit",
    "clean", "bonus", "track", "single", "ep", "album", "original", "anniversary",
    "mono", "stereo", "digital", "expanded", "special", "standard", "reissue",
    "soundtrack", "ost", "television", "tv", "drama", "movie", "film", "from",
    "pt", "part", "vol", "no", "the", "리마스터", "リマスター",
    "오리지널", "사운드트랙", "보너스",
}


def _variant_tags(text: str, artists: tuple[str, ...] = ()) -> frozenset[str]:
    """이 자유 텍스트가 담고 있는 변형 표지 범주.

    먼저 연주자 이름을 지운다. 아티스트 본인의 이름은 변형 표지가 될 수 없고,
    한국어/일본어에는 단어 경계가 없어서 이걸 안 하면 '버스커버스커'가 '커버'로,
    Live라는 밴드명이 live로 읽힌다.
    """
    t = _nfkc(text or "").casefold()
    for raw in artists:
        a = _nfkc(raw or "").casefold().strip()
        if len(a) < 2:
            continue
        t = t.replace(a, " ")
        a_ns = a.replace(" ", "")
        if a_ns and a_ns != a:
            t = t.replace(a_ns, " ")
    hits = set()
    for name, rx in _ASCII_RE.items():
        if rx.search(t):
            hits.add(name)
    for name, needles in _VARIANT_CJK.items():
        if any(n in t for n in needles):
            hits.add(name)
    return frozenset(hits)


def _benign(qual: str) -> bool:
    """녹음본 정체성에 아무 정보도 주지 않는 꼬리표인가."""
    q = _nfkc(qual).casefold().strip()
    if not q:
        return True
    if _FEAT_HEAD.match(q):
        return True
    toks = _WORDS.findall(q)
    if not toks:
        return True
    return all(t in _BENIGN_WORDS or t.isdigit() for t in toks)


def qualifiers(title: str) -> dict[str, str]:
    """의미 있는 꼬리표: {정규화 키: 원문}.

    원문을 함께 들고 다니는 게 중요하다. 키는 공백이 제거된 형태라
    'Live Version' → 'liveversion'이 되어 ASCII 단어 경계 매칭이 실패한다.
    벌점 판정은 반드시 원문으로 해야 P_VARIANT 등급을 제대로 받는다.
    """
    t = _nfkc(title or "")
    raw = list(_QUAL.findall(t))
    tail = _DASH_SUFFIX.search(_QUAL.sub(" ", t))
    if tail:
        raw.append(tail.group(0).lstrip(" -–—"))
    out: dict[str, str] = {}
    for q in raw:
        if _benign(q):
            continue
        k = norm(q)
        if k:
            out.setdefault(k, q)
    return out


def _qualifier_penalty(inp_title: str, cand_title: str,
                       artists: tuple[str, ...] = ()) -> float:
    qi, qc = qualifiers(inp_title), qualifiers(cand_title)
    pen = 0.0
    for k in (qc.keys() - qi.keys()) | (qi.keys() - qc.keys()):
        raw = qc.get(k) or qi.get(k) or k
        pen += P_VARIANT if _variant_tags(raw, artists) else P_UNKNOWN
    # 괄호 밖이라도 한쪽에만 있는 변형 범주는 벌점
    vi = _variant_tags(inp_title, artists)
    vc = _variant_tags(cand_title, artists)
    pen += 0.15 * len(vi ^ vc)
    return pen


# ── 유사도 프리미티브 ──────────────────────────────────
def fuzzy(a: str, b: str) -> float:
    """정규화된 문자열 두 개를 비교. 1.0은 오직 완전 일치일 때만.
    포함 관계는 완전 일치보다 엄격히 낮고, 긴 쪽의 잉여 분량만큼 깎인다."""
    if not a or not b:
        return 0.0
    if a == b:
        return 1.0
    if a in b or b in a:
        short, long = (a, b) if len(a) < len(b) else (b, a)
        if len(short) >= 2:
            return 0.60 + 0.40 * (len(short) / len(long))
    return SequenceMatcher(None, a, b).ratio()


def artist_score(inp: str, cand: str) -> float:
    a, b = norm(inp), norm(cand)
    if not a or not b:
        return 0.0
    if a == b:
        return 1.0
    base = fuzzy(a, b)
    # 한쪽이 협연 표기일 수 있다: 'DAOKO' vs 'DAOKO×米津玄師'
    at = {norm(x) for x in _ARTIST_SPLIT.split(_nfkc(inp).casefold())}
    bt = {norm(x) for x in _ARTIST_SPLIT.split(_nfkc(cand).casefold())}
    at.discard("")
    bt.discard("")
    if at and bt:
        inter = at & bt
        if inter and max(len(x) for x in inter) >= 2:
            base = max(base, 0.90)
        else:
            base = max(base, 0.85 * len(at & bt) / len(at | bt))
    return base


def title_score(inp: str, cand: str) -> float:
    literal = fuzzy(norm(inp), norm(cand))
    stem    = fuzzy(title_base(inp), title_base(cand))
    return max(literal, stem * 0.995)   # 완전 일치 쪽을 아주 살짝 우대


# ── 최종 점수 ──────────────────────────────────────────
def calc_score(inp_title: str, inp_artist: str,
               res_title: str, res_artist: str, res_album: str = "") -> float:
    """입력 곡과 후보 곡의 동일성 점수. [0.0, 1.0]으로 클램프된다.

    res_album은 선택 인자다 — 라이브/노래방 프레싱은 트랙명은 멀쩡하고
    앨범명에서만 자백하는 경우가 많다('AKMU [항해] TOUR LIVE').

    !! 서로 다른 문자체계의 문자열을 넣지 말 것. '물론' vs 'With you'는
       "다른 곡"이 아니라 "정보 없음"이고, 이 함수는 그 둘을 구분하지 못한다.
       iTunes 결과는 반드시 route_storefronts()가 고른 스토어프론트에서
       받아온 뒤에 비교해야 한다.
    """
    a = artist_score(inp_artist, res_artist)
    if a < ARTIST_GATE:
        return 0.0                       # 다른 연주자 → 커버
    t = title_score(inp_title, res_title)
    if t < TITLE_GATE:
        return 0.0                       # 다른 곡

    # 곱셈 결합: 약한 쪽을 강한 쪽으로 매수할 수 없다
    s = (t ** 0.62) * (a ** 0.38)

    # 같은 곡이지만 다른 '녹음'인가 (표지 탐색에서 아티스트명은 제외)
    who = (inp_artist, res_artist)
    s -= _qualifier_penalty(inp_title, res_title, who)

    # 결정적 단서가 앨범명에만 있는 경우
    album_only = (_variant_tags(res_album, who)
                  - _variant_tags(inp_title, who) - _variant_tags(res_title, who))
    if album_only:
        s -= P_ALBUM * min(len(album_only), 2)

    return round(max(0.0, min(1.0, s)), 4)
