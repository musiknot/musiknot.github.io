from enum import Enum
from pydantic import BaseModel


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
    url: str


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
