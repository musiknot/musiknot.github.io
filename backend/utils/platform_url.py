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
