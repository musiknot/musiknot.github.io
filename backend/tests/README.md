# 테스트

```bash
cd backend
uv sync --group dev
uv run pytest -q
```

네트워크를 쓰지 않습니다. 0.2초 안에 끝납니다.

## 무엇을 지키고 있나

### `scoring/test_matching.py` — 곡 매칭 회귀 (41곡)

한때 한국어·일본어 곡이 **하나도** 매칭되지 않았습니다 (한국곡 0/10, 일본곡 0/7). 원인은 검색이 아니라 채점이었습니다 — iTunes 에 `country` 를 안 보내면 US 스토어프론트로 가고, US 는 한국어 제목을 영어로 번역해 돌려줍니다. 그걸 한국어 입력과 문자열 비교하니 유사도가 0 이 됐습니다.

```
calc_score('물론', '허각', 'With you', 'Huh Gak') = 0.000   ← 정답인데 0점
```

이 테스트는 그 회귀를 막습니다. **실제로 잡는지 확인해 봤습니다** — `route_storefronts` 를 옛 동작(항상 US)으로 되돌리면 41/41 이 **10/41** 로 떨어집니다.

| 카테고리 | 곡 수 | 무엇을 잡나 |
|---|---|---|
| `kr_translated` | 10 | US 에 영문 제목이 있는 한국곡. 위 버그의 본체 |
| `kr_native_only` | 5 | 어떤 스토어프론트에도 영문 제목이 없는 곡. 우아하게 실패해야 함 |
| `jp_translated` | 7 | 일본곡 |
| `mixed_ascii` | 6 | ASCII 제목 + 원어 아티스트. `title.isascii() and artist.isascii()` 가 AND 라서 잘못 처리하던 경우 |
| `en_control` | 7 | 영문 대조군. 한/일을 고치다가 영어를 깨뜨리지 않았는지 |
| `tricky` | 6 | 노래방 커버, `(Inst.)` 쌍둥이, 재녹음 |

정답(`expected_apple_id`)은 추측이 아닙니다. 전부 `lookup?id=…&country=KR|JP` 로 원어 표기를 확인해 넣었고, 근거가 각 행의 `verified` 필드에 있습니다.

**오답과 무응답을 분리해서 셉니다.** 오답은 무응답보다 나쁩니다 — 사용자가 눌러서 엉뚱한 곡으로 가니까요. 채점 기준을 바꿀 때 무응답이 늘어나는 건 감수할 수 있지만 오답이 느는 건 안 됩니다.

### `test_youtube_pick.py` — 검색 결과에서 MV/Topic 고르기

`search.list` 는 호출당 100 유닛이고 할당량이 10,000/일입니다. 예전에는 MV 용과 Topic 용으로 두 번 검색해서 하루 50 파싱이 상한이었습니다. 한 번만 검색하고 결과에서 둘 다 골라내면 100 파싱이 됩니다. 고르는 로직이 순수 함수라 API 키 없이 검증됩니다.

## 어떻게 네트워크 없이 도는가

`scoring/itunes_fixtures.json` 에 iTunes 응답 **660건**이 녹화돼 있습니다 (3.3MB). `scoring/fake_itunes.py` 가 `services.itunes.httpx` 를 대체해 이걸 돌려줍니다.

**실제 `services/itunes.py` 와 `core/scoring.py` 를 그대로 채점합니다.** 사본을 만들어 채점하면 사본이 시간이 지나며 실제 코드와 어긋나고, 그러면 테스트가 통과해도 아무것도 보장하지 못합니다.

녹화되지 않은 요청은 `FixtureMiss` 로 **시끄럽게** 실패합니다. 이게 `httpx.HTTPError` 를 상속하지 않는 것이 중요합니다 — `itunes.py` 가 `HTTPError` 를 잡아 빈 리스트로 흡수하므로, 상속했다면 픽스처 누락이 '검색 결과 없음' 으로 둔갑해 테스트가 조용히 잘못된 것을 측정하게 됩니다.

## 이 벤치마크의 한계 — 반드시 알고 쓸 것

**포화 상태입니다.** 스코어러를 통째로 빼고 '스토어프론트 라우팅 + 아티스트 우선 질의 + 1위 채택' 만 해도 40/41 이 나옵니다. 즉 이 데이터가 검증하는 것은 주로 **검색 경로**이고, `core/scoring.py` 의 임계값들(`SEARCH_MATCH_THRESHOLD`, `ARTIST_GATE`, `P_VARIANT` …)은 여기서 **반증되지 않습니다.** 값을 0.30~0.95 어디에 두어도 41/41 이 나옵니다.

그러니 41/41 을 여유로 읽지 마세요. 채점 로직을 개선하려면 **새 데이터가 필요합니다.** 특히 다음이 비어 있습니다.

- 문자체계가 다른 아티스트명 (`지드래곤` vs `G-DRAGON`, `블랙핑크` vs `BLACKPINK`) — 현재 구조적으로 기권합니다
- 중국어 (한자만으로는 일본어와 구분되지 않아 JP 스토어프론트로 갑니다)
- 애플 뮤직 URL 이 입력인 경우 (영문 메타데이터로 파이프라인에 들어옵니다)
- 멜론·벅스·FLO 쪽 매칭 (지금은 iTunes 경로만 덮습니다)

## 픽스처 갱신

새 곡을 추가하려면 `bench_data.json` 에 행을 넣고, 그 곡에 필요한 iTunes 응답을 `itunes_fixtures.json` 에 추가합니다. 키는 **파라미터를 키 순으로 정렬한 전체 URL** 입니다.

```
https://itunes.apple.com/search?country=KR&entity=song&limit=5&media=music&term=아이유%20밤편지
```

`expected_apple_id` 는 반드시 `lookup?id=…&country=…` 로 확인하고 그 결과를 `verified` 에 적어 두세요. 추측한 정답은 벤치마크를 조용히 망가뜨립니다.
