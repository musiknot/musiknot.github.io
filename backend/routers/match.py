from fastapi import APIRouter
from models.schemas import SongRequest, MatchResponse
from services.melon import search_melon, merge_results
from services.musicbrainz import get_english_candidates

router = APIRouter()


@router.post("/match", response_model=MatchResponse)
async def match_song(req: SongRequest):

    # STEP 1: 원제 그대로 멜론 검색 (K-POP / POP은 대부분 여기서 해결)
    results = search_melon(req.title, req.artist)
    best    = results[0] if results else None

    if best and best.similarity >= 0.85:
        return MatchResponse(status="exact", results=[best])

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
            return MatchResponse(status="exact", results=[best2])

        # threshold 못 넘어도 결과 병합해서 유지
        results = merge_results(results, results2)

    # STEP 3: 최대 5개 후보 반환 → 프론트엔드에서 유저가 선택
    if results:
        return MatchResponse(status="multiple", results=results[:5])

    # 결과 없음
    return MatchResponse(status="not_found", results=[])