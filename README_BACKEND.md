# Backend 구조 (musiknot.github.io)

음원 URL을 받아 여러 음악 플랫폼의 동일 곡 링크를 모아주는 FastAPI 서버입니다. 비동기(`async/await`) HTTP 클라이언트와 부분적 웹 스크래핑을 조합해, 7개 플랫폼의 검색·상세 조회를 병렬로 처리합니다.

> 본 문서는 백엔드 코드의 *현재 상태*를 설명합니다. 최종 갱신 2026-07-27.

---

## 1. 기술 스택

| 분류 | 항목 | 비고 |
|---|---|---|
| Language | Python | 3.13 (`.python-version`) |
| Framework | FastAPI 0.135.3 | + Uvicorn 0.34.0 (ASGI 서버) |
| HTTP Client | httpx 0.28.1 | 비동기 / 단축 URL 리다이렉트 추적 / JSON & HTML |
| Scraping | beautifulsoup4 4.14.3 | Melon, Bugs HTML 파싱 |
| Env loader | python-dotenv 1.1.0 | `.env` → `os.environ` |
| Multipart | python-multipart 0.0.20 | FastAPI form/file 처리 (현 시점 미사용) |
| Package Mgr | **uv** | `pyproject.toml` + `uv.lock` (lockfile 커밋) |
| Deploy | **Oracle Cloud** | systemd + Caddy. 10장 참고 |

**제거된 의존성** — `musicbrainzngs`(6장), `requests`·`ytmusicapi`(둘 다 import 0건이었음).

**개발 의존성** — `pytest`. `uv sync --group dev` 로 설치합니다. 운영 서버에는 `uv sync --no-dev` 로 배포하므로 들어가지 않습니다.

---

## 2. 디렉터리 레이아웃

```
backend/
├── main.py                   # FastAPI 앱·CORS·라우터 등록·헬스체크
├── pyproject.toml            # 의존성 정의 (uv)
├── uv.lock                   # 잠금 파일 (커밋 대상)
├── .python-version           # 3.13
├── README.md                 # (빈 파일. pyproject의 readme= 가 참조)
│
├── core/
│   └── scoring.py            # 동일성 판정 + 스토어프론트 라우팅 + 임계값
│
├── models/
│   └── schemas.py            # Pydantic 스키마 (도메인 + I/O)
│
├── routers/
│   ├── parse.py              # POST /parse — URL 또는 공유 ID → 멀티플랫폼 ID
│   ├── match.py              # POST /match — 제목·아티스트 → 멜론 검색
│   └── share.py              # GET /s/{id} — 크롤러용 OG 카드 (3xx 없음)
│
├── services/                 # 외부 API/스크래퍼 어댑터 (전부 async)
│   ├── url_resolver.py       # 단축 URL 해제
│   ├── itunes.py             # Apple Music (스토어프론트 라우팅)
│   ├── melon.py              # 멜론 (BS4)
│   ├── bugs.py               # 벅스 (BS4 + sc:* 메타)
│   ├── flo.py                # FLO (JSON API + x-gm-* 헤더)
│   └── youtube.py            # YouTube Data API v3
│
├── utils/
│   └── platform_url.py       # 정규식 → (Platform, track_id) + 공유 ID 빌드/파싱
│
└── tests/                    # pytest 115개. 네트워크 없이 0.7초 (tests/README.md 참고)
    ├── scoring/              # 검증된 41곡 + iTunes 응답 660건 녹화
    ├── test_bugs.py          # 벅스 파싱 회귀 (+ bugs_fixtures/ 녹화 페이지)
    ├── test_share.py         # 공유 ID 왕복 + OG 페이지 이스케이프
    ├── test_youtube_pick.py
    └── test_platform_contract.py   # ⚠ 프론트 src/constants/platforms.js 를 읽는다
```

`__init__.py`는 모두 빈 파일이지만 *명시적 패키지화*를 위해 존재합니다 (PEP 420 namespace package 회피).

---

## 3. 진입점 — `main.py`

```python
app = FastAPI(title="Musiknot API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://musiknot.github.io",   # 운영 (GitHub Pages)
        "http://localhost:3000",
        "http://localhost:5173",         # Vite dev
    ],
    allow_methods=["*"],
    allow_headers=["*"],
)
```

- **CORS의 의미**: `allow_origins`는 *이 API를 호출해도 되는 쪽*의 목록입니다. 즉 프론트엔드 주소입니다. 백엔드 자신의 호스트명(`musiknot-api.duckdns.org`)은 여기 들어가지 **않습니다**. 백엔드 주소가 바뀌어도 이 목록은 그대로 둡니다.
- **로깅**: `logging.basicConfig(level=INFO)`. 모든 모듈이 `logging.getLogger(__name__)`. `print` 없음.
- **헬스체크**: `GET /` → `{"status": "ok", "service": "Musiknot API"}`
- **prefix 없음**: `/parse`, `/match`가 루트 직속.

---

## 4. 엔드포인트

### `POST /parse` — URL 파싱

**Request** — `url` 또는 `id` 중 **정확히 하나**. 둘 다 오거나 둘 다 없으면 422 로 거절한다.

```json
{ "url": "https://www.melon.com/song/detail.htm?songId=30314784" }
{ "id":  "melon:30314784" }
```

**Response** (`ParseResponse`)
```json
{
  "title": "밤편지", "artist": "아이유", "album": "...", "albumArt": "https://...",
  "isrc": null,
  "platforms": {
    "spotify": null, "appleMusic": "1219218446", "youtube": null,
    "youtubeMusic": null, "melon": "30314784", "bugs": "30598121",
    "flo": null, "amazon": null
  },
  "shareId": "melon:30314784"
}
```

`shareId` 는 공유 링크용 짧은 식별자다. 입력 URL 이 가리키던 플랫폼 기준으로 만들며, 프론트가 이 값으로 공유 URL 을 조립한다.

**처리 흐름** (`routers/parse.py`)

```
[req.url]
   ▼
STEP 1  단축 URL 해제 (kko.to, flomuz.io만 해당) → 실패 시 400
   ▼
STEP 2  플랫폼 감지 (utils/platform_url) — 순수 정규식 → 실패 시 400
   ▼
STEP 3  원본 곡 lookup — _LOOKUP_BY_PLATFORM[platform]
        Spotify, Amazon → 미등록 → 501 / 결과 없음 → 404
   ▼
STEP 4  album/album_art 보강 (_enrich_track) — 누락 시 iTunes로 1건만
   ▼
STEP 5  크로스플랫폼 ID 병렬 조회 (asyncio.gather)
        fetch_apple / fetch_melon / fetch_bugs / fetch_flo / fetch_youtube
   ▼
ParseResponse
```

**핵심**: STEP 5는 **모든 플랫폼에 원문 그대로** 질의합니다. 번역하지 않습니다. 이유는 6장에.

### `GET /s/{share_id}` — 공유 링크 + 미리보기 카드

`melon:30314784` 같은 짧은 ID 를 받아, 메신저 미리보기용 메타 태그가 담긴 HTML 을 돌려주고 사람은 프론트엔드로 넘긴다.

**왜 백엔드가 이걸 하는가.** 프론트는 GitHub Pages(정적)라 곡마다 다른 메타 태그를 줄 수 없고, 크롤러는 JavaScript 를 실행하지 않으므로 React 로 넣어봐야 소용이 없다. 동적 서버만 할 수 있는 일이다.

**왜 3xx 를 쓰지 않는가.** 어떤 크롤러가 리다이렉트를 따라가는지는 서비스마다 다르고 바뀐다. 그래서 모두에게 메타 태그를 주고, 사람만 `<meta http-equiv="refresh">` 와 `location.replace` 로 넘긴다. 크롤러는 둘 다 실행하지 않으므로 **추종 여부와 무관하게** 카드가 살아남는다.

실제로 확인된 곳: **카카오톡, 네이버 블로그, 네이버 카페.** 네이버는 자체 크롤러(Yeti)라 카카오와 별개 검증이다. curl 로는 페이스북·X·디스코드·슬랙 UA 도 200 과 정상 메타 태그를 받는 것까지 확인했지만, 그 서비스들이 실제로 어떻게 렌더링하는지는 아직 미확인이다.

**비용.** 미리보기에 필요한 건 제목·아티스트·아트뿐이라 `lookup_by_id` **1회**만 쓴다. `/parse` 전체(외부 호출 약 7회)를 돌리지 않는다. 크롤러는 링크를 반복·선행 조회하므로 이 차이가 크다.

**보안.** 곡 제목은 멜론·벅스에서 스크래핑해 온 값이라 그대로 HTML 에 넣으면 따옴표 하나로 속성을 탈출한다. 모든 삽입 지점에 `html.escape(quote=True)` 를 쓰고, JS 에 넣는 URL 은 `json.dumps` 로 감싼다(파이썬 `!r` 은 유효한 JS 리터럴이라는 보장이 없다). 리다이렉트 대상은 모듈 상수라 ID 가 끼어들 수 없다.

| 상황 | 응답 |
|---|---|
| 정상 | 200 + 곡 메타 태그 |
| ID 형식 오류 | 404 + 일반 카드, 사람은 홈으로 |
| 조회 실패·타임아웃 | 200 + 일반 카드 (사람은 넘어가야 하므로) |

### `POST /match` — 곡 검색 (멜론 기반)

`{title, artist}` → 멜론 검색 1회. 최상위 결과가 `EXACT_MATCH_THRESHOLD`(0.90) 이상이면 `status="exact"`로 단건, 아니면 상위 5개를 `status="multiple"`로, 결과가 없으면 `not_found`.

> 이 엔드포인트는 **현재 프론트에서 호출되지 않습니다**. `src/hooks/useMelonMatch.js`가 유일한 호출자인데 어디서도 import되지 않습니다.

---

## 5. 모델 — `models/schemas.py`

```python
class Platform(str, Enum):
    SPOTIFY="spotify"; APPLE_MUSIC="appleMusic"; YOUTUBE="youtube"
    YOUTUBE_MUSIC="youtubeMusic"; MELON="melon"; BUGS="bugs"
    FLO="flo"; AMAZON="amazon"

class Track(BaseModel):
    platform: Platform; track_id: str; title: str; artist: str
    album: str | None = None; album_art: str | None = None
    similarity: float | None = None    # search()만 채움
```

응답 키는 **camelCase**(`appleMusic`, `albumArt`) — 프론트 컨벤션에 맞춘 의도적 선택. 내부 도메인은 snake_case이며 `ParseResponse` 생성 시 명시적으로 매핑합니다.

---

## 6. 동일성 판정 — `core/scoring.py`

이 파일이 이 저장소에서 가장 중요합니다. **왜 이렇게 생겼는지**를 먼저 이해해야 합니다.

### 근본 문제: 문자열 유사도로는 번역을 검증할 수 없다

iTunes Search API는 `country` 파라미터를 안 보내면 **US 스토어프론트**로 갑니다. US는 한국어/일본어 곡의 제목을 **영어로 번역해서** 돌려줍니다.

```
calc_score('물론',   '허각',   'With you',           'Huh Gak') = 0.000
calc_score('밤편지', '아이유', 'Through the Night',  'IU')      = 0.05
```

둘 다 **정답인데 버려졌습니다.** 그리고 이건 임계값을 낮춰서 해결되지 않습니다. 오히려 악화됩니다 — 원어 제목을 그대로 쓴 **노래방 커버**가 점수를 더 받기 때문입니다. 실제 사례로 `사건의 지평선`을 검색하면 NEWAGES의 커버가 0.6, 진짜 윤하 곡이 0.06이었습니다.

구조적으로 이렇습니다. **번역이 성공했으면 유사도는 정의상 0이고, 유사도가 높으면 번역이 안 된 것입니다.** 유사도는 이 둘을 구분할 수 없습니다.

### 해법: 번역을 검증하지 말고, 애초에 생기지 않게 한다

`country`는 스토어프론트뿐 아니라 **메타데이터 언어**를 고릅니다. 그래서 입력의 문자체계에 맞는 스토어프론트에 질의하면 양쪽이 같은 문자체계가 되고, 평범한 유사도가 다시 유효해집니다.

```python
route_storefronts(title, artist) -> list[str]
    한글 포함        → ["KR", "US"]
    가나/한자 포함   → ["JP", "US"]
    그 외            → ["US"]
```

라우팅은 **핵심 제목**(괄호·`feat`·` - ` 꼬리표 제거)과 **대표 아티스트**(첫 협연 구분자 앞)만 봅니다. 국내 플랫폼은 `Shape of You (Feat. 아무개)`처럼 표기하는데, 게스트 크레딧 때문에 영어 곡이 KR로 가면 안 되기 때문입니다.

### 점수 구조

`calc_score(inp_title, inp_artist, res_title, res_artist, res_album="")` → `[0.0, 1.0]`

1. **동일성 정규화** — NFKC + casefold + 글자/숫자/CJK 이외 제거. `버스커 버스커`와 `버스커버스커`, `옛사랑`과 `옛 사랑`이 같은 키가 됩니다.
2. **녹음본 구분** — 괄호/대괄호/` - ` 꼬리표를 집합으로 뽑아 한쪽에만 있는 것에 벌점. 아는 변형 표지(live/inst/remix/카라오케/오르골/여자키…)는 크게(`P_VARIANT` 0.42), 모르는 꼬리표도 "정량화되지 않은 위험"으로 조금(`P_UNKNOWN` 0.22). 앨범명에만 나타나는 표지도 별도 벌점(`P_ALBUM` 0.25) — 라이브 음원은 트랙명은 멀쩡하고 앨범명에서만 자백하는 경우가 많습니다.
3. **결합** — `(title ** 0.62) * (artist ** 0.38)`, **곱셈**입니다.

곱셈인 이유가 중요합니다. 이전의 선형 `0.6*제목 + 0.4*아티스트`는 *"아티스트가 다르니 커버다"* 라고 말할 수 없습니다. 아티스트에서 잃는 0.4를 제목에서 언제든 벌충할 수 있기 때문이고, 노래방 커버가 진짜 곡을 이긴 경로가 정확히 그것이었습니다. **곱은 매수당하지 않습니다.**

추가로 게이트가 있습니다 — `ARTIST_GATE`(0.34) 미만이면 다른 연주자로 보고 즉시 0점, `TITLE_GATE`(0.34) 미만이면 다른 곡으로 보고 0점.

### 임계값

```python
SEARCH_MATCH_THRESHOLD = 0.62   # 외부 검색 채택
WEAK_MATCH_THRESHOLD   = 0.55   # 모든 스토어프론트를 본 뒤 최후 채택
EXACT_MATCH_THRESHOLD  = 0.90   # /match 단건 확정
RANK_TIEBREAK          = 0.012  # 순위당 가산점
```

`RANK_TIEBREAK`은 **동일성을 대체하지 않습니다.** 0점(다른 곡/다른 연주자)은 가산점을 아예 못 받으므로 커버가 순위로 진짜 곡을 이길 수 없습니다. 메타데이터가 완전히 같은 프레싱들(같은 녹음, 다른 앨범) 사이에서만 작동합니다.

### 측정 결과

검증된 정답을 가진 41곡 벤치마크(iTunes 응답 캐시, 결정적 재현):

| 카테고리 | 이전 | 현재 |
|---|---|---|
| 한국곡(영문 제목 있음) | 0/10 | **10/10** |
| 한국곡(영문 제목 없음) | 4/5 (오탐 1) | **5/5** |
| 일본곡 | 0/7 | **7/7** |
| ASCII 제목 + 원어 아티스트 | 6/6 | 6/6 |
| 영문 대조군 | 6/7 | **7/7** |
| 함정(커버·inst·재녹음) | 2/6 | **6/6** |
| **합계** | **18/41 (43.9%)** | **41/41 (100%)** |
| 오탐(틀린 id 반환) | 4 | **0** |

**단, 41/41을 여유로 읽으면 안 됩니다.** 벤치마크가 포화 상태입니다 — 스코어러를 완전히 빼고 "스토어프론트 라우팅 + 아티스트 우선 검색어 + 1위 채택"만 해도 40/41이 나옵니다. 즉 이 벤치마크가 검증한 것은 주로 **검색(retrieval)** 쪽이고, 스코어러의 임계값들은 이 데이터로는 반증되지 않았습니다. 스코어러의 값어치는 벤치마크 밖에서 나옵니다 — 10가지 변형(NFD, 전각, feat 접미, OST 태그, 협연 아티스트 등) 스트레스 테스트를 전부 통과했고, 두 함정 곡을 순위 운이 아니라 구조적으로 0.000점 처리해 기각합니다.

### 알려진 한계

**문자체계가 다른 아티스트명은 기권합니다.** `지드래곤` vs `G-DRAGON`, `블랙핑크` vs `BLACKPINK`, `에스파` vs `aespa`는 모두 `artist_score` 0.0 → 전체 0점입니다. Apple의 KR 스토어프론트가 이런 아티스트를 라틴 문자로 표기하기 때문입니다. **틀린 링크(-1)보다 빈 슬롯(0)이 낫다**는 판단이며, 로마자 변환 비교를 붙이기 전까지 유지합니다.

**중국어는 JP 스토어프론트로 갑니다.** 한자만으로는 중국어와 일본어 한자를 구분할 수 없습니다. 보통은 기권(안전한 실패)하지만 해결되지는 않습니다.

---

## 7. 서비스 어댑터

모든 서비스는 공용 인터페이스를 따릅니다.

```python
async def search(title: str, artist: str, limit: int = 5) -> list[Track]
async def lookup_by_id(track_id: str) -> Track | None
```

| 파일 | 대상 | 통신 | 특이점 |
|---|---|---|---|
| `url_resolver.py` | kko.to / flomuz.io | httpx redirect | FLO share는 HTML에서 `/detail/track/(\d+)` 추출 |
| `itunes.py` | Apple Music | REST | **스토어프론트 라우팅**. 아래 참고 |
| `melon.py` | Melon | BS4 스크래핑 | 메인 페이지 사전 방문으로 쿠키 확보, detail → 검색 폴백 |
| `bugs.py` | Bugs | BS4 스크래핑 | 곡정보 표 + `sc:*` 메타 |
| `flo.py` | FLO | 내부 JSON API | `x-gm-*` 헤더, `imgList[size==500]` |
| `youtube.py` | YouTube | Data API v3 | MV → Topic → fallback. ⚠ 쿼터 한계 (12장) |

### 7.1 iTunes — 스토어프론트 라우팅

```python
term = f"{artist} {title}"          # 순서가 결과를 바꾼다
for country in route_storefronts(title, artist):
    results = await _get(SEARCH_URL, {... "country": country})
    cand, ranked, score = _best_candidate(...)
    if ranked >= SEARCH_MATCH_THRESHOLD:
        return [...]                 # 조기 반환
# 전부 본 뒤 WEAK_MATCH_THRESHOLD 로 최후 채택, 아니면 []
```

- **검색어 순서**: `아티스트 제목`입니다. `아이유 밤편지`는 정답을, `밤편지 아이유`는 엉뚱한 곡을 1위로 줍니다.
- **상위 5개를 훑습니다**(`SCAN_LIMIT`). 정답이 1위가 아닌 경우가 실제로 있습니다.
- **호출 비용**: 네이티브 스토어프론트에서 임계값을 넘으면 거기서 **조기 반환**하므로 보통 1회입니다. 다만 네이티브가 실패하면 US까지 2회가 되고, `_enrich_track`이 album/album_art를 보강할 때 1회가 더 붙습니다. 즉 `/parse` 당 **1~3회**입니다. 아래 레이트리밋(분당 약 20회)과 직결됩니다.
- `search()`는 단일 best를 리스트로 감싸 반환합니다(호출부 인터페이스 통일).
- 채택할 만한 후보가 없으면 **빈 리스트**를 반환합니다. 틀린 곡보다 빈 슬롯이 낫다는 원칙.

### 7.2 멜론 — 봇 탐지 우회

```python
async with httpx.AsyncClient(headers=MELON_HEADERS, timeout=10) as client:
    await client.get("https://www.melon.com")   # ① 쿠키 확보
    track = await _lookup_via_detail(client, track_id)   # ② 상세
    return await _lookup_via_search(client, track_id)    # ③ 폴백
```

- Chrome UA 위장 + `Referer: https://www.melon.com`.
- **쿠키 워밍업은 요청 간에 유지되지 않습니다.** `AsyncClient`가 함수 스코프라 반환 시 쿠키 저장소가 파기됩니다. 즉 이 워밍업은 *같은 요청 내* 상세 조회에만 효과가 있습니다. IP 고정 여부와는 무관합니다.

### 7.3 벅스 — 무엇을 믿고 무엇을 안 믿는가

한동안 벅스 링크 입력이 전부 404였습니다. 페이지는 HTTP 200인데 셀렉터 4개 중 3개가 사라진 DOM을 가리켰고, 남은 하나(`p.artist a`)는 **곡 정보가 아니라 페이지 아래쪽 뮤직비디오 목록**의 아티스트 라벨을 잡고 있었습니다. 뮤비 아티스트가 곡 아티스트와 같아서 값이 맞아떨어졌을 뿐입니다.

지금은 필드마다 다른 근거를 씁니다.

| 필드 | 1순위 | 폴백 | 왜 |
|---|---|---|---|
| 제목 | `<meta property="sc:track_title">` | `header.pgTitle h1` | 벅스가 공유 카드용으로 박아두는 값. 페이지에 `h1`이 9~13개라 순진한 `h1` 폴백은 '안내'를 집습니다 |
| 아티스트 | 곡정보 표 `<th>아티스트</th>` 행의 첫 `/artist/` 링크 | `sc:artist_nm` (경고 로그와 함께) | 협연곡에서 `sc:artist_nm`은 대표가 아니라 **앨범 크레딧**을 줍니다 — `Golden`이 `HUNTR/X`가 아니라 `KPop Demon Hunters Cast`가 됩니다 |
| 앨범 | `sc:album_title` | 표 `<th>앨범</th>` 행 | '앨범' 행은 '참여 정보' 유무에 따라 2번째/3번째로 밀려서 위치로는 못 찾습니다 |
| 앨범아트 | `og:image` | 없음 | 이미 500px이고 캐시버스터 쿼리가 없습니다. 본문 이미지는 200px에 `?version=`이 붙습니다 |

**`og:title`은 폴백으로도 쓰지 않습니다.** 벅스는 없는 곡을 404가 아니라 **302로 `/noMusic`** 에 보내고, 그 페이지는 200에 `og:title='나를 위한 플리, 벅스'`와 벅스 로고 이미지를 달고 옵니다. 그래서 방어가 두 겹입니다 — 리다이렉트를 **따라가지 않는 것**(302에서 `raise_for_status`가 걸립니다)이 1차, `og:title`을 안 믿는 것이 2차입니다. `follow_redirects=True`를 켜는 순간 삭제된 곡이 그럴듯한 가짜 Track이 됩니다.

앨범아트에는 경로 가드(`image.bugsm.co.kr/album/images/`)가 있습니다. 없으면 커버가 없는 곡에 벅스 로고가 앨범 아트인 척 박힙니다.

**아티스트 셀은 세 가지 모양입니다** (검색 결과 400행 실측).

| 모양 | 건수 |
|---|---|
| `<a href=".../artist/123" title="…">` 하나 | 373 |
| 위 + `<a class="more" title="아티스트 전체보기">` (협연) | 13 |
| `<a>` 없는 평문 — `Unknown`·`Various Artists`·`Cover Artist` | 27 |

그래서 앵커는 클래스가 아니라 **`a[href*="/artist/"]`** 입니다 — `a[title]`로 잡으면 '아티스트 전체보기' 버튼 라벨이 아티스트 이름으로 섞입니다. 세 번째 부류는 `search()`가 **조용히 버리고 있었고**, 그 탓에 OST·컴필레이션 곡이 벅스에서 통째로 사라졌습니다. 곡을 버릴지는 파서가 아니라 스코어러가 정할 일입니다.

> **알려진 불일치**: `search()`는 아티스트명의 괄호 병기를 떼고(`The Weeknd(위켄드)` → `The Weeknd`), `lookup_by_id()`는 남깁니다. 같은 곡이 들어온 경로에 따라 다른 문자열을 갖습니다. 어느 쪽으로 통일하든 `calc_score` 결과가 달라지는 **매칭 정책** 문제라 일부러 손대지 않았고, `test_bugs.py`가 이 사실을 고정해 두고 있습니다.

---

## 8. 유틸 — `utils/platform_url.py`

정규식 목록으로 URL → `(Platform, track_id)`. **순서가 중요합니다** — `music.youtube.com`이 `youtube.com`보다 앞에 있어야 합니다. Apple Music은 `/album/.../?i=ID`와 `/song/.../ID` 두 형태를 모두 지원합니다. 외부 호출이 없는 순수 함수로, 단위 테스트가 가장 쉬운 모듈입니다.

---

## 9. 외부 통합 / 환경 변수

| 외부 | 인증 | 레이트리밋 |
|---|---|---|
| iTunes Search/Lookup | 무인증 | **약 20회/분**, 초과 시 429 + `retry-after` 19~29초 |
| Melon / Bugs | UA 위장 | 명시적 제한 없음. HTML 구조 변경 시 파싱 깨짐 |
| FLO | `x-gm-*` 헤더 | 비공식 API |
| YouTube Data API v3 | API Key | **쿼터 10,000 유닛/일** — 12장 참고 |

### 환경 변수

- `YOUTUBE_API_KEY` — 누락 시 youtube 관련 함수가 `None` 반환(경고 로그 1줄). `/parse`는 정상 응답하지만 `youtube`/`youtubeMusic`이 빕니다.
- 운영에서는 `/etc/musiknot/musiknot.env`에 root 소유 600으로 두고 systemd `EnvironmentFile`로 주입합니다.

### 타임아웃 / 에러 정책

- httpx 기본 5초. **Melon `lookup_by_id`만 10초**.
- 각 서비스는 외부 실패를 `try/except httpx.HTTPError`로 흡수 후 `None`/`[]` 반환 → 한 플랫폼이 죽어도 응답 전체는 살아남습니다.
- 라우터에서 `HTTPException`으로 승격되는 것만: `400`(단축 URL 실패/미지원 플랫폼), `404`(곡 없음), `501`(lookup 미구현 — Spotify, Amazon).

---

## 10. 실행 / 배포

### 로컬 실행

```bash
cd backend
uv sync
uv run uvicorn main:app --reload      # http://localhost:8000
```

자동 문서: `/docs` (Swagger UI), `/redoc`.

### 테스트

```bash
cd backend
uv sync --group dev
uv run pytest -q          # 115개, 네트워크 없이 0.7초
```

무엇을 왜 지키는지는 [`tests/README.md`](backend/tests/README.md) 에 있습니다. 여기서는 두 가지만 짚습니다.

**매칭 벤치마크(41곡)는 포화 상태입니다.** 41/41 이 스코어러가 좋다는 뜻이 아닙니다 — 6장 끝을 참고하세요.

**`test_platform_contract.py` 는 프론트엔드 소스를 읽습니다.** 플랫폼 식별자가 `Platform` enum, `PlatformIds` 필드, 프론트 카드 `id`, 프론트 `deepLinks` 키 네 곳에 중복 정의돼 있고 어긋나면 조용히 카드가 사라지기 때문입니다. 그래서 `src/constants/platforms.js` 를 고치면 백엔드 `pytest` 가 깨질 수 있습니다. 반대로 이 파일들의 위치를 옮기면 테스트가 파일을 못 찾아 실패합니다 — 이것도 의도된 동작입니다.

### 운영 — Oracle Cloud

Railway에서 이전했습니다(무료 체험 만료). 현재 구성:

```
브라우저 → https://musiknot.github.io          GitHub Pages
              ↓ fetch
         https://musiknot-api.duckdns.org      Let's Encrypt, Caddy 자동 갱신
              ↓ 역방향 프록시
         127.0.0.1:8000                         uvicorn — 외부 노출 없음
              ↓
         Oracle VM.Standard.E2.1.Micro / ap-osaka-1 (Always Free)
```

| 구성요소 | 위치 |
|---|---|
| 코드 | `/home/ubuntu/musiknot` (git clone) |
| 서비스 | `musiknot-api.service` — `Restart=always`, `MemoryMax=512M`, 하드닝 적용 |
| 비밀값 | `/etc/musiknot/musiknot.env` (root:root 600) |
| TLS | Caddy + `/etc/caddy/Caddyfile` — 만료 30일 전 자동 갱신, cron 불필요 |
| DNS | DuckDNS + `duckdns-update.timer` (15분 주기) |
| 방화벽 | OCI 보안목록 **및** 호스트 iptables — **두 계층 모두** 필요 |

**중요한 함정들**

- **방화벽이 2계층입니다.** OCI 콘솔에서 80/443을 열어도 Ubuntu 이미지의 iptables INPUT 체인 끝에 catch-all REJECT가 있습니다. `-A`로 추가하면 REJECT *뒤*에 붙어 무효입니다. 반드시 `-I`로 REJECT **앞에** 삽입해야 합니다.
- **80번도 열어야 합니다.** Let's Encrypt HTTP-01 검증이 80번으로 들어옵니다.
- **systemd는 `~/.local/bin`을 PATH에 넣지 않습니다.** uv를 홈에 설치하면 서비스가 못 찾습니다. `/usr/local/bin`에 설치했습니다.
- **`Procfile`은 삭제했습니다.** VM에는 버프팩이 없어 무의미했고, `--host 0.0.0.0`이라 그대로 실행하면 Caddy를 우회해 uvicorn이 외부에 직접 노출되는 위험이 있었습니다.

### 배포 절차

```bash
# 로컬에서 커밋·push 후
ssh ubuntu@<서버>
cd ~/musiknot && git pull
cd backend && uv sync
sudo systemctl restart musiknot-api
```

프론트엔드는 별도입니다 — `src/constants/api.js`의 주소는 **빌드 시점에 번들에 박히므로**, 백엔드 주소가 바뀌면 반드시 `npm run deploy`로 재배포해야 합니다.

### 과금 안전성

Oracle 문서: *"Oracle doesn't charge for Always Free resources after you upgrade, and will only charge you for resource usage above the Always Free limits."* 유일한 과금 경로는 아웃바운드 트래픽이고 **월 10TB 무료**입니다.

> **지켜야 할 규칙**: `/parse`는 앨범아트를 **링크로만** 반환합니다. 이미지를 프록시하도록 바꾸면 (150KB × 요청 수)로 산수가 완전히 달라집니다. 이 성질이 "과금 불가"를 지탱합니다.

---

## 11. 응답 데이터 흐름

```
클라이언트 ──POST /parse──▶ main.py ──▶ routers/parse.py:parse_url
                                          ├─ url_resolver.resolve_url()
                                          ├─ utils.platform_url.extract_platform_id()
                                          ├─ services.<X>.lookup_by_id()
                                          ├─ _enrich_track() → itunes
                                          └─ _find_cross_platform_ids()
                                              └─ asyncio.gather(
                                                   itunes.search,   ← route_storefronts
                                                   melon.search,    ← 원문 질의
                                                   bugs.search,     ← 원문 질의
                                                   flo.search,      ← 원문 질의
                                                   youtube.search_*)
                                          Track → ParseResponse (camelCase)
```

---

## 12. 알려진 문제

**~~벅스 링크 입력이 404입니다.~~** 고쳤습니다 — 7장의 `bugs.py` 항목과 `tests/test_bugs.py` 참고.

**YouTube 쿼터가 실질적 상한입니다.** `search.list`는 호출당 100 유닛이고 기본 쿼터가 10,000/일입니다. `/parse` 한 번이 `search_mv_and_topic()` 으로 **1회만** 호출하므로 **하루 약 100회 파싱**이 한계입니다. (예전에는 MV용·Topic용으로 2회 호출해서 50회였습니다.) 더 늘리려면 캐싱이나 쿼터 증설이 필요합니다.

**멜론이 지원하지 않는 압축을 광고합니다.** `melon.py`가 `Accept-Encoding: gzip, deflate, br`을 보내지만 이 환경의 httpx는 brotli를 디코드할 수 없습니다(brotli 패키지 미설치). 현재는 멜론이 gzip으로 응답해 문제가 없지만, `br`로 응답하면 깨집니다.

**`isrc`는 항상 `null`입니다.** 조사 결과 현재 연동된 7개 플랫폼 중 ISRC를 내보내는 곳이 하나도 없습니다(iTunes 무료 API 28키 전수 확인, FLO JSON, 멜론·벅스 페이지 모두 0건). 즉 **ISRC는 매칭의 입력이 될 수 없습니다** — 먼저 퍼지 매칭으로 곡을 특정해야 조회가 가능하기 때문입니다. Deezer(`/2.0/track/isrc:{ISRC}`, 무인증)로 사후 보강은 가능합니다.

**`/match`와 `merge_results`는 도달 불가 코드입니다.** 프론트에서 호출하지 않습니다.

**레이트리밋 방어가 없습니다.** 자체 구현이 없고 스톡 Caddy에도 속도 제한 모듈이 없습니다. 남용 시 박스가 느려지거나 죽는 쪽으로 실패합니다(과금되지는 않습니다). `/parse` 폭주는 곧 멜론·벅스·FLO로의 폭주이므로, 박스 건강보다 **IP가 차단당하는 것**이 더 큰 위험입니다.

---

## 13. 향후 개선 후보

- 매칭 벤치마크 확장 — 현재 41곡은 포화 상태라 채점 임계값을 반증하지 못합니다. 비어 있는 케이스는 `tests/README.md` 참고.
- 아티스트명 로마자 변환 비교(`지드래곤` ↔ `G-DRAGON`).
- Deezer로 `isrc` 필드 채우기.
- Spotify 연동 — URL 정규식은 이미 있고 `/parse`에서 501. ISRC를 주고받는 유일한 무료 경로지만, 2026년 2월 정책 변경으로 개발자 본인의 Premium 구독이 필요합니다.
- iTunes 응답 캐싱 — 분당 20회 제한 대비.
