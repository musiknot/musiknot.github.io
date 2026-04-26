import logging

from fastapi import APIRouter

from core.scoring import EXACT_MATCH_THRESHOLD
from models.schemas import (
    MatchResponse,
    SongRequest,
    Track,
    track_to_song_result,
)
from services import melon, musicbrainz

log    = logging.getLogger(__name__)
router = APIRouter()


@router.post("/match", response_model=MatchResponse)
async def match_song(req: SongRequest):
    # STEP 1: 원제 그대로 멜론 검색 (K-POP / POP은 대부분 여기서 해결)
    results: list[Track] = await melon.search(req.title, req.artist)
    best = results[0] if results else None

    if best and (best.similarity or 0) >= EXACT_MATCH_THRESHOLD:
        return MatchResponse(status="exact", results=[track_to_song_result(best)])

    # STEP 2: MusicBrainz로 영문 후보를 만들어 다시 멜론 검색
    candidates = await musicbrainz.get_english_candidates(req.title, req.artist)
    for cand in candidates:
        en_title  = cand["english_title"]
        en_artist = cand["english_artist"]
        log.info("MusicBrainz candidate: %s / %s", en_title, en_artist)

        results2 = await melon.search(en_title, en_artist)
        best2    = results2[0] if results2 else None

        if best2 and (best2.similarity or 0) >= EXACT_MATCH_THRESHOLD:
            return MatchResponse(status="exact", results=[track_to_song_result(best2)])

        results = melon.merge_results(results, results2)

    # STEP 3: 임계 미달이면 후보 5개를 프론트로
    if results:
        return MatchResponse(
            status  = "multiple",
            results = [track_to_song_result(t) for t in results[:5]],
        )

    return MatchResponse(status="not_found", results=[])
