from enum import Enum
from pydantic import BaseModel, model_validator


# ── 도메인 모델 ────────────────────────────────────

class Platform(str, Enum):
    SPOTIFY       = "spotify"
    APPLE_MUSIC   = "appleMusic"
    YOUTUBE       = "youtube"
    YOUTUBE_MUSIC = "youtubeMusic"
    MELON         = "melon"
    BUGS          = "bugs"
    FLO           = "flo"
    AMAZON        = "amazon"


class Track(BaseModel):
    """모든 게이트웨이가 반환하는 통일된 곡 표현."""
    platform:   Platform
    track_id:   str
    title:      str
    artist:     str
    album:      str | None = None
    album_art:  str | None = None
    similarity: float | None = None    # search()에서만 채워짐, lookup_by_id()는 None


# ── /match API 스키마 ────────────────────────────

class SongRequest(BaseModel):
    title:    str
    artist:   str
    album:    str | None = None
    track_no: int | None = None


class SongResult(BaseModel):
    songId:     str
    title:      str
    artist:     str
    album:      str | None
    similarity: float


class MatchResponse(BaseModel):
    status:  str          # "exact" | "multiple" | "not_found"
    results: list[SongResult]


# ── /parse API 스키마 ────────────────────────────

class ParseRequest(BaseModel):
    """음원 URL 또는 공유 ID 중 **정확히 하나**를 받는다.

    공유 ID(`melon:30314784`)는 짧은 공유 링크용이다. 둘 다 오거나 둘 다
    없으면 조용히 하나를 고르지 않고 422 로 거절한다 — 어느 쪽을 썼는지
    호출자가 착각한 채로 동작하는 게 더 나쁘기 때문이다.
    """
    url: str | None = None
    id:  str | None = None

    @model_validator(mode="after")
    def _exactly_one(self):
        if bool(self.url) == bool(self.id):
            raise ValueError("url 과 id 중 정확히 하나를 지정해야 합니다")
        return self


class PlatformIds(BaseModel):
    spotify:      str | None = None
    appleMusic:   str | None = None
    youtube:      str | None = None
    youtubeMusic: str | None = None
    melon:        str | None = None
    bugs:         str | None = None
    flo:          str | None = None
    amazon:       str | None = None


class ParseResponse(BaseModel):
    title:     str
    artist:    str
    album:     str | None = None
    albumArt:  str | None = None
    isrc:      str | None = None
    platforms: PlatformIds
    # 공유 링크용 짧은 식별자 (`melon:30314784`). 입력 URL 이 가리키던 플랫폼
    # 기준으로 만든다. 프론트가 이 값으로 공유 URL 을 조립한다.
    shareId:   str | None = None


# ── 변환 헬퍼 ──────────────────────────────────────

def track_to_song_result(t: Track) -> SongResult:
    """도메인 Track → /match 응답 형태."""
    return SongResult(
        songId     = t.track_id,
        title      = t.title,
        artist     = t.artist,
        album      = t.album,
        similarity = t.similarity if t.similarity is not None else 0.0,
    )
