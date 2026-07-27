"""공유 링크 — `GET /s/{share_id}`

메신저에 붙여넣었을 때 곡 제목·아티스트·앨범아트가 담긴 미리보기 카드가 뜨게
하는 것이 목적이다. 프론트엔드는 GitHub Pages(정적)라 곡마다 다른 메타 태그를
줄 수 없다. 크롤러는 JavaScript 를 실행하지 않으므로 React 로 넣어봐야 소용이
없다. 그래서 동적인 백엔드가 이 역할을 맡는다.

**크롤러 종류에 의존하지 않는 형태로 만들었다.** 어떤 크롤러가 HTTP 리다이렉트를
따라가는지는 서비스마다 다르고 바뀌기도 한다. 그래서 3xx 를 쓰지 않는다 —
모두에게 메타 태그가 담긴 HTML 을 그대로 주고, 사람만 JavaScript 와
`<meta http-equiv="refresh">` 로 프론트엔드에 보낸다. 크롤러는 둘 다 실행하지
않으므로 메타 태그를 읽고 멈춘다. 리다이렉트 추종 여부와 무관하게 동작한다.

비용도 의도적으로 낮췄다. 미리보기에 필요한 건 제목·아티스트·앨범아트뿐이라
`lookup_by_id` **1회**면 된다. `/parse` 전체(외부 호출 약 7회)를 돌리지 않는다.
크롤러는 링크 하나를 여러 번, 미리 가져가기 때문에 이 차이가 크다.
"""
import html
import json
import logging
from urllib.parse import quote

from fastapi import APIRouter
from fastapi.responses import HTMLResponse

from models.schemas import Platform, Track
from services import bugs, flo, itunes, melon, youtube
from utils.platform_url import parse_share_id

log    = logging.getLogger(__name__)
router = APIRouter()

FRONTEND_ORIGIN = "https://musiknot.github.io"
# og:url 은 반드시 절대 URL 이어야 한다. 상대 경로를 주면 크롤러가 정규 URL을
# 잡지 못한다.
SHARE_ORIGIN    = "https://musiknot-api.duckdns.org"

# 리다이렉트 대상은 **상수**다. share_id 는 여기에 끼어들 수 없다.
# (열린 리다이렉트 방지 — 목적지가 입력에 의해 바뀌지 않는다.)
def _frontend_url(share_id: str) -> str:
    return f"{FRONTEND_ORIGIN}/?id={quote(share_id, safe='')}"


_LOOKUP_BY_PLATFORM = {
    Platform.APPLE_MUSIC:   itunes.lookup_by_id,
    Platform.MELON:         melon.lookup_by_id,
    Platform.BUGS:          bugs.lookup_by_id,
    Platform.FLO:           flo.lookup_by_id,
    Platform.YOUTUBE:       youtube.lookup_by_id,
    Platform.YOUTUBE_MUSIC: youtube.lookup_by_id,
}


def _page(*, title: str, description: str, image: str | None,
          canonical: str, redirect_to: str) -> str:
    """메타 태그가 담긴 HTML.

    모든 삽입 지점에 html.escape(quote=True) 를 쓴다. 곡 제목과 아티스트는
    멜론·벅스에서 **스크래핑해 온 값**이라 신뢰할 수 없다. 제목에 따옴표가
    하나 들어 있으면 `<meta content="...">` 속성을 탈출한다.
    quote=True 여야 " 와 ' 까지 이스케이프된다 — 기본값은 &, <, > 만 처리한다.
    """
    e = lambda s: html.escape(s or "", quote=True)
    t, d, c, r = e(title), e(description), e(canonical), e(redirect_to)
    img = f'\n  <meta property="og:image" content="{e(image)}">' if image else ""

    return f"""<!doctype html>
<html lang="ko">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{t}</title>
  <meta name="description" content="{d}">

  <meta property="og:type" content="music.song">
  <meta property="og:site_name" content="Musiknot">
  <meta property="og:title" content="{t}">
  <meta property="og:description" content="{d}">
  <meta property="og:url" content="{c}">{img}

  <meta name="twitter:card" content="summary_large_image">
  <meta name="twitter:title" content="{t}">
  <meta name="twitter:description" content="{d}">

  <link rel="canonical" href="{c}">
  <!-- 크롤러는 아래 둘 다 실행하지 않는다. 사람만 넘어간다. -->
  <meta http-equiv="refresh" content="0; url={r}">
</head>
<body>
  <p>이동 중… <a href="{r}">여기</a>를 눌러주세요.</p>
  <script>location.replace({json.dumps(redirect_to)});</script>
</body>
</html>"""


@router.get("/s/{share_id}", response_class=HTMLResponse)
async def share(share_id: str):
    """`melon:30314784` 같은 공유 ID 를 미리보기 카드가 달린 페이지로."""
    canonical = f"{SHARE_ORIGIN}/s/{quote(share_id, safe=':')}"
    parsed    = parse_share_id(share_id)

    # ID 가 잘못됐어도 사람은 어딘가 도착해야 한다. 홈으로 보낸다.
    if not parsed:
        log.info("Share: invalid id %r", share_id[:80])
        return HTMLResponse(
            _page(title="Musiknot",
                  description="음악 링크 하나로 여러 플랫폼의 같은 곡을 찾습니다.",
                  image=None, canonical=canonical, redirect_to=FRONTEND_ORIGIN),
            status_code=404,
        )

    platform, track_id = parsed
    redirect_to = _frontend_url(share_id)

    track: Track | None = None
    lookup = _LOOKUP_BY_PLATFORM.get(platform)
    if lookup:
        try:
            track = await lookup(track_id)
        except Exception as e:
            # 조회 실패가 크롤러에게 스택 트레이스로 새면 안 되고,
            # 사람의 이동도 막으면 안 된다. 일반 카드로 강등한다.
            log.warning("Share: lookup failed for %s: %s", share_id, e)

    if not track:
        return HTMLResponse(
            _page(title="Musiknot",
                  description="음악 링크 하나로 여러 플랫폼의 같은 곡을 찾습니다.",
                  image=None, canonical=canonical, redirect_to=redirect_to),
            status_code=200,   # 사람은 정상적으로 넘어가야 하므로 200
        )

    # 앨범아트는 제3자 CDN URL 이다. https 가 아니면 크롤러가 거부하는 경우가
    # 있어 그때는 이미지를 빼고 텍스트 카드로 낸다.
    image = track.album_art if (track.album_art or "").startswith("https://") else None

    log.info("Share: %s → %s / %s", share_id, track.title, track.artist)
    return HTMLResponse(_page(
        title       = f"{track.title} - {track.artist}",
        description = f"{track.artist} · 여러 음악 플랫폼에서 이 곡 듣기",
        image       = image,
        canonical   = canonical,
        redirect_to = redirect_to,
    ))
