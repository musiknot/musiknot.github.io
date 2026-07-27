import logging

from fastapi import APIRouter

from core.scoring import EXACT_MATCH_THRESHOLD
from models.schemas import (
    MatchResponse,
    SongRequest,
    Track,
    track_to_song_result,
)
from services import melon

log    = logging.getLogger(__name__)
router = APIRouter()


@router.post("/match", response_model=MatchResponse)
async def match_song(req: SongRequest):
    """원제 그대로 멜론에서 찾는다.

    예전에는 여기서 멜론이 실패하면 MusicBrainz로 영문 후보를 만들어 다시
    검색했는데, 그 경로는 이득 없이 해롭기만 했다. 멜론은 원제를 색인하므로
    영문 질의는 애초에 맞을 수가 없고, 어쩌다 임계값을 넘으면 그건 '맞은' 게
    아니라 '다른 곡이 통과한' 것이다 — 문자열 유사도로는 번역을 검증할 수
    없으니 그 결과를 걸러낼 방법도 없었다. 게다가 MusicBrainz는 동기 라이브러리를
    스레드로 감싼 3~6초짜리 직렬 구간이었다.

    지금은 한 번의 멜론 검색이 전부고, 판정은 calc_score가 한다.
    """
    results: list[Track] = await melon.search(req.title, req.artist)
    if not results:
        log.info("Melon: no results for '%s' / '%s'", req.title, req.artist)
        return MatchResponse(status="not_found", results=[])

    best = results[0]

    # 확신할 만큼 붙으면 단일 결과로 확정
    if (best.similarity or 0) >= EXACT_MATCH_THRESHOLD:
        return MatchResponse(status="exact", results=[track_to_song_result(best)])

    # 아니면 후보 5개를 프론트로 넘겨 사용자가 고르게 한다
    return MatchResponse(
        status  = "multiple",
        results = [track_to_song_result(t) for t in results[:5]],
    )
