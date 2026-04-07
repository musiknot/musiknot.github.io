from pydantic import BaseModel

# ── /match 요청/응답 ──────────────────────────────

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


# ── /parse 요청/응답 ──────────────────────────────

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
    title:    str
    artist:   str
    album:    str | None = None
    albumArt: str | None = None
    isrc:     str | None = None
    platforms: PlatformIds