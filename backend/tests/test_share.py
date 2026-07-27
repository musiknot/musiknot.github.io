"""공유 링크 — ID 파싱과 HTML 이스케이프.

둘 다 순수 함수라 네트워크도 API 키도 필요 없다.

지키려는 것:
  1. ID 는 URL 경로에서 와서 그대로 외부 서비스 조회에 쓰인다. 느슨하면
     경로 탈출·널바이트·미등록 플랫폼이 그대로 통과한다.
  2. 곡 제목은 멜론·벅스에서 **스크래핑해 온 값**이다. 그걸 그대로 HTML 속성에
     넣으면 따옴표 하나로 `<meta content="...">` 를 탈출한다.
"""
from __future__ import annotations

import pytest

from models.schemas import Platform
from routers.share import _page
from utils.platform_url import build_share_id, parse_share_id

VALID = [
    ("melon:30314784",        Platform.MELON,         "30314784"),
    ("bugs:30598121",         Platform.BUGS,          "30598121"),
    ("flo:438092629",         Platform.FLO,           "438092629"),
    ("appleMusic:1219218446", Platform.APPLE_MUSIC,   "1219218446"),
    ("youtube:BzYnNdJhZQw",   Platform.YOUTUBE,       "BzYnNdJhZQw"),
    ("youtubeMusic:a-b_c9",   Platform.YOUTUBE_MUSIC, "a-b_c9"),
    ("spotify:0VjIjW4GlUZA",  Platform.SPOTIFY,       "0VjIjW4GlUZA"),
]

REJECTED = [
    ("melon:../../etc/passwd", "경로 탈출"),
    ("melon:30314784\x00",     "널 바이트"),
    ("melon:3031/4784",        "슬래시"),
    ("melon:3031 4784",        "공백"),
    ("nosuchplatform:123",     "플랫폼 화이트리스트 밖"),
    ("MELON:30314784",         "플랫폼 이름 대소문자 불일치"),
    ("melon:",                 "track_id 없음"),
    (":30314784",              "플랫폼 없음"),
    ("melon",                  "구분자 없음"),
    ("melon:" + "9" * 65,      "길이 초과"),
    ("melon:30314784:extra",   "콜론이 더 있음"),
    ("",                       "빈 문자열"),
]


@pytest.mark.parametrize("share_id,platform,track_id", VALID,
                         ids=[c[0] for c in VALID])
def test_valid_ids_parse(share_id, platform, track_id):
    assert parse_share_id(share_id) == (platform, track_id)


@pytest.mark.parametrize("share_id,why", REJECTED, ids=[c[1] for c in REJECTED])
def test_malformed_ids_are_rejected(share_id, why):
    assert parse_share_id(share_id) is None, f"통과하면 안 됨: {why}"


@pytest.mark.parametrize("share_id,platform,track_id", VALID,
                         ids=[c[0] for c in VALID])
def test_build_and_parse_round_trip(share_id, platform, track_id):
    assert build_share_id(platform, track_id) == share_id


# ── HTML 이스케이프 ────────────────────────────────────

INJECTIONS = [
    'Song" /><script>alert(1)</script><meta x="',
    "Song' /><img src=x onerror=alert(1)>",
    "<b>굵게</b>",
    'A "quoted" title',
    "O'Brien & Sons",
]


# 무엇을 검사해야 하는가.
#
# 페이지에는 사람을 넘기기 위한 정상 <script> 가 항상 하나 들어 있으므로
# "<script> 문자열이 없어야 한다" 는 틀린 검사다. 또 `onerror=` 같은 문자열은
# 특수문자가 없어서 이스케이프 후에도 평범한 텍스트로 남는데, 그건 위험하지
# 않다 — 앞의 `<img` 가 `&lt;img` 가 되어 태그가 성립하지 않기 때문이다.
#
# 진짜 불변식은 하나다: **속성 값 안에 날것의 < > " 가 없어야 한다.**
# 그게 있으면 속성이나 태그를 탈출한 것이고, 없으면 무슨 문자열이 들어 있든
# 텍스트일 뿐이다.
_RAW_IN_ATTR = ('<', '>', '"')


def _attr_value(html_out: str, prop: str) -> str:
    """`<meta property="og:title" content="...">` 의 content 값을 그대로 꺼낸다."""
    line = next(l for l in html_out.splitlines() if prop in l)
    return line.split('content="', 1)[1].rsplit('"', 1)[0]


def _tag_count(html_out: str) -> int:
    """생성된 태그 수. 주입으로 태그가 늘어나면 안 된다."""
    return html_out.count("<")


@pytest.mark.parametrize("evil", INJECTIONS)
def test_title_cannot_escape_the_meta_attribute(evil):
    html_out = _page(title=evil, description="d", image=None,
                     canonical="/s/melon:1", redirect_to="https://musiknot.github.io/")
    value = _attr_value(html_out, "og:title")
    for ch in _RAW_IN_ATTR:
        assert ch not in value, f"속성 탈출: {value!r} 안에 {ch!r}"
    # 주입 문자열이 태그를 하나도 새로 만들지 못했는지 — 무해한 제목과 비교
    benign = _page(title="safe", description="d", image=None,
                   canonical="/s/melon:1", redirect_to="https://musiknot.github.io/")
    assert _tag_count(html_out) == _tag_count(benign), "주입으로 태그가 늘어남"


@pytest.mark.parametrize("evil", INJECTIONS)
def test_description_and_image_are_escaped_too(evil):
    html_out = _page(title="t", description=evil, image=f"https://x/{evil}",
                     canonical="/s/melon:1", redirect_to="https://musiknot.github.io/")
    for prop in ("og:description", "og:image"):
        value = _attr_value(html_out, prop)
        for ch in _RAW_IN_ATTR:
            assert ch not in value, f"{prop} 탈출: {value!r} 안에 {ch!r}"


def test_redirect_is_a_valid_js_string_literal():
    """JS 안에 넣는 URL 은 json.dumps 로 감싼다.

    파이썬 repr(!r)은 홑따옴표를 쓰고 이스케이프 규칙도 JS 와 미묘하게 달라서
    JS 문자열 리터럴로 항상 안전하다는 보장이 없다. json.dumps 는 항상 유효한
    JS 문자열을 만든다.
    """
    tricky = 'https://musiknot.github.io/?id=a%27b"c'
    html_out = _page(title="t", description="d", image=None,
                     canonical="/s/x", redirect_to=tricky)
    js = next(l for l in html_out.splitlines() if "location.replace" in l)
    inner = js.split("location.replace(", 1)[1].rsplit(")", 1)[0]
    import json as _json
    assert _json.loads(inner) == tricky   # 유효한 JSON/JS 문자열이어야 한다


def test_missing_image_omits_the_tag_entirely():
    """앨범아트가 없으면 빈 og:image 를 내보내지 않는다.

    빈 og:image 는 크롤러에 따라 깨진 이미지로 표시된다. 아예 없는 편이 낫다.
    """
    html_out = _page(title="t", description="d", image=None,
                     canonical="/s/melon:1", redirect_to="https://x/")
    assert "og:image" not in html_out


def test_redirect_target_is_present_for_humans():
    """크롤러는 meta refresh 도 JS 도 실행하지 않지만, 사람은 넘어가야 한다."""
    target = "https://musiknot.github.io/?id=melon%3A30314784"
    html_out = _page(title="t", description="d", image=None,
                     canonical="/s/melon:30314784", redirect_to=target)
    assert "http-equiv=\"refresh\"" in html_out
    assert "location.replace" in html_out
