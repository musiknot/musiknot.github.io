import re

from models.schemas import Platform


# 정규식 + 플랫폼 매핑 — 순수 regex, 외부 호출 없음
_PATTERNS: list[tuple[Platform, re.Pattern[str]]] = [
    (Platform.SPOTIFY,       re.compile(r"open\.spotify\.com/track/([A-Za-z0-9]+)")),
    (Platform.APPLE_MUSIC,   re.compile(r"music\.apple\.com/[a-z]+/album/[^/]+/\d+\?i=(\d+)")),
    (Platform.APPLE_MUSIC,   re.compile(r"music\.apple\.com/[a-z]+/song/[^/]+/(\d+)")),
    (Platform.YOUTUBE_MUSIC, re.compile(r"music\.youtube\.com/watch\?v=([A-Za-z0-9_-]+)")),
    (Platform.YOUTUBE,       re.compile(r"(?:youtube\.com/watch\?v=|youtu\.be/)([A-Za-z0-9_-]+)")),
    (Platform.MELON,         re.compile(r"melon\.com/.*[?&]songId=(\d+)")),
    (Platform.BUGS,          re.compile(r"(?:music|m)\.bugs\.co\.kr/track/(\d+)")),
    (Platform.FLO,           re.compile(r"music-flo\.com/detail/track/(\d+)")),
    (Platform.AMAZON,        re.compile(r"music\.amazon\.com/tracks/([A-Za-z0-9]+)")),
]


def extract_platform_id(url: str) -> tuple[Platform, str] | None:
    """URL에서 (platform, track_id) 추출. 매칭 안 되면 None."""
    for platform, pattern in _PATTERNS:
        m = pattern.search(url)
        if m:
            return platform, m.group(1)
    return None


# ── 공유 ID ────────────────────────────────────────
#
# 공유 링크용 짧은 식별자. `melon:30314784` 형태다.
#
# 저장소가 필요 없다는 게 핵심이다. extract_platform_id 가 이미 모든 입력 URL을
# (platform, track_id) 로 줄여주므로, 같은 곡의 어떤 URL 형태(단축 URL, 애플의
# ?i= 형과 /song/ 형, 추적 파라미터가 붙은 것)든 하나의 ID 로 모인다. 짧은
# 코드를 발급하고 보관할 DB 가 필요 없다.
#
# 길이도 실용적인 차이를 만든다. `?url=` 로 원본 URL 을 인코딩해 넘기면 99자인데
# 이건 45자다. QR 로 만들면 버전이 한 단계 낮아져 스캔이 쉬워진다.

# track_id 허용 문자. 현재 지원 플랫폼을 모두 덮는다 —
# 멜론·벅스·FLO·애플은 숫자, 유튜브는 base64url([A-Za-z0-9_-]),
# 스포티파이·아마존은 영숫자.
_TRACK_ID = re.compile(r"^[A-Za-z0-9_-]{1,64}$")

_PLATFORM_BY_VALUE = {p.value: p for p in Platform}


def build_share_id(platform: Platform, track_id: str) -> str:
    """(platform, track_id) → 'melon:30314784'"""
    return f"{platform.value}:{track_id}"


def parse_share_id(share_id: str) -> tuple[Platform, str] | None:
    """'melon:30314784' → (Platform.MELON, '30314784'). 형식이 틀리면 None.

    검증을 엄격하게 하는 이유: 이 값은 URL 경로에서 오고 그대로 외부 서비스
    조회에 쓰인다. 플랫폼 이름은 Platform enum 화이트리스트로만 받고,
    track_id 는 문자 종류와 길이를 모두 제한한다. 경로 탈출(`../`), 널 바이트,
    과도하게 긴 입력은 여기서 전부 걸러진다.
    """
    if not share_id or not isinstance(share_id, str):
        return None
    # 콜론이 여러 개여도 첫 번째만 구분자로 본다 (track_id 에는 콜론이 올 수 없으므로
    # 나머지는 아래 문자 검사에서 걸린다)
    name, _, track_id = share_id.partition(":")
    platform = _PLATFORM_BY_VALUE.get(name)
    if platform is None or not _TRACK_ID.match(track_id):
        return None
    return platform, track_id
