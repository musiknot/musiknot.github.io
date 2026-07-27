import logging
import re

import httpx

log = logging.getLogger(__name__)


async def resolve_url(url: str) -> str:
    """
    단축 URL을 최종 URL로 변환.
    - kko.to/xxx        → https://www.melon.com/song/detail.htm?songId=xxx
    - flomuz.io/s/xxx   → https://www.music-flo.com/detail/track/xxx/trackList.html
    """
    try:
        async with httpx.AsyncClient(follow_redirects=True, timeout=5) as client:
            res = await client.get(url)
            final_url = str(res.url)

            # FLO share URL: 응답 HTML에서 실제 track ID 추출
            if "share.music-flo.com" in final_url:
                match = re.search(r"/detail/track/(\d+)", res.text)
                if not match:
                    raise ValueError("FLO track ID를 찾을 수 없습니다.")
                track_id = match.group(1)
                return f"https://www.music-flo.com/detail/track/{track_id}/trackList.html"

            return final_url

    except httpx.HTTPError as e:
        raise ValueError(f"URL 리다이렉트 실패: {e}") from e
