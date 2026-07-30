# Frontend 구조 (musiknot.github.io)

음악 링크를 입력받아 여러 플랫폼의 동일한 곡 링크를 모아 보여주는 SPA입니다. React + Vite + Tailwind CSS 기반이며, 별도의 라우터·상태관리 라이브러리 없이 React Hooks와 조건부 렌더링으로 동작합니다.

> 최종 갱신 2026-07-27.

## 1. 기술 스택

| 분류 | 항목 | 버전 |
|---|---|---|
| Framework | React / React DOM | ^19.2.4 |
| Build Tool | Vite | ^8.0.4 |
| Styling | Tailwind CSS (`@tailwindcss/vite`) | ^4.2.2 |
| Icons | lucide-react | ^1.7.0 |
| Lint | ESLint + react-hooks/react-refresh | ^9.39.4 |
| Deploy | gh-pages | ^6.3.0 |

라우터·상태관리 라이브러리는 사용하지 않습니다.

## 2. 디렉터리 레이아웃

```
musiknot.github.io/
├── index.html              # 엔트리 HTML — 매니페스트·apple-touch-icon 링크
├── public/                 # 매니페스트 + PWA 아이콘 (빌드 시 dist 루트로 복사)
├── vite.config.js          # React + Tailwind 플러그인, base: '/'
├── src/
│   ├── main.jsx            # createRoot(StrictMode)
│   ├── App.jsx             # 최상위 — 전역 상태/뷰 전환
│   ├── index.css           # Tailwind import + 다크 모드 variant
│   ├── App.css             # 레거시 템플릿 스타일 (미사용)
│   ├── components/
│   │   ├── Header.jsx          # 로고, 테마/언어 스위처, 메뉴
│   │   ├── SearchBar.jsx       # URL 입력 + 클립보드 붙여넣기
│   │   ├── InstallCard.jsx     # 홈 안내 카드 — 설치/iOS/데스크톱 3분기
│   │   ├── ShareWidget.jsx     # 결과 공유 (복사·시트·QR)
│   │   ├── QrCode.jsx          # uqr → SVG 직접 렌더
│   │   ├── PlatformGrid.jsx    # 글로벌/한국 두 그리드
│   │   └── PlatformCard.jsx    # 개별 플랫폼 카드(딥링크 처리)
│   ├── pages/
│   │   ├── HomeView.jsx        # 실제 사용되는 검색 화면
│   │   ├── ResultView.jsx      # 곡 상세 화면
│   │   └── ShareLogView.jsx    # ?sharelog=1 — 공유 원본 파라미터 수집용
│   ├── hooks/
│   │   ├── useTheme.js         # light/dark/system + localStorage
│   │   ├── useLanguage.js      # ko/en i18n + t() 헬퍼
│   │   ├── useParse.js         # /parse 호출
│   │   ├── useInstall.js       # 설치 가능 여부 / OS / 설치 실행
│   │   └── useMelonMatch.js    # /match 호출 — 현재 미사용 (7장)
│   ├── constants/
│   │   ├── api.js              # ★ 백엔드 베이스 URL (단일 출처)
│   │   ├── translations.js     # ko/en 문자열
│   │   └── platforms.js        # 플랫폼 메타데이터 + 딥링크 빌더
│   ├── utils/
│   │   ├── urlValidator.js     # 지원 음원 서비스 URL 화이트리스트
│   │   ├── shareTarget.js      # 공유 파라미터에서 링크 추출
│   │   ├── shareLog.js         # 공유 원본 기록 (기기 안에만)
│   │   └── installPrompt.js    # beforeinstallprompt 포착 (React 보다 먼저)
│   └── assets/                 # 미사용 placeholder
├── legacy/                 # 구버전 정적 페이지 보관
└── backend/                # FastAPI 백엔드 (README_BACKEND.md 참고)
```

## 3. 부팅 흐름

1. `index.html` — `<div id="root">` + `<script type="module" src="/src/main.jsx">`
2. `src/main.jsx` — `createRoot(...).render(<StrictMode><App/></StrictMode>)`
3. `src/App.jsx` — 전역 상태(테마·언어·결과·히스토리)를 보유하며 화면 결정

## 4. 라우팅 / 화면 전환

React Router 미사용. `App.jsx`의 상태에 따라 로딩 스피너 / 에러 화면 / `ResultView` / `HomeView` 중 하나를 렌더링합니다.

URL 기반 자동 검색 두 가지를 지원합니다.

- **`?url=<음원-링크>`** — 정상 동작합니다. 쿼리스트링 파싱 후 `parse()` 자동 호출.
- **`/gets/<base64>`** — ⚠ **운영에서 동작하지 않습니다.** GitHub Pages는 정적 호스팅이라 존재하지 않는 경로에 404를 반환하고, `public/`에도 배포된 `gh-pages` 브랜치에도 `404.html`이 없어 React가 부팅조차 못 합니다. 로컬 dev에서 되는 건 Vite 개발 서버가 SPA fallback을 해주기 때문입니다. 경로 방식을 유지하려면 `public/404.html`을 `index.html` 복사본으로 두는 우회가 필요하고, 아니면 이 분기를 삭제하는 게 맞습니다.

- **`?id=<플랫폼:트랙ID>`** — 공유 링크. `?id=melon:30314784` 형태로, `useParse` 의 `parseById` 가 백엔드에 ID 를 그대로 넘깁니다. URL 이 아니므로 `validateUrl` 을 거치지 않고, 형식 검증은 백엔드가 합니다(플랫폼 화이트리스트 + 문자·길이 제한).

- **`?text=` / `?title=`** — 공유 시트에서 들어오는 경로(아래 PWA 절). `?url=` 과 함께 `extractSharedUrl` 이 세 칸을 훑습니다.

- **`?sharelog=1`** — 공유로 들어온 원본 파라미터를 보여주는 수집용 화면.

> 공유 링크는 **쿼리스트링 방식**이 정적 호스팅에서 확실히 동작합니다.

### PWA / 공유 타깃 — 링크를 앱 **안으로** 들여오기

`ShareWidget` 이 결과를 밖으로 내보내는 쪽이라면, 이쪽은 반대 방향입니다. 설치하면 멜론·유튜브뮤직의 공유 메뉴에 Musiknot 이 떠서, **음악앱 → 복사 → 브라우저 → 붙여넣기** 과정이 없어집니다.

| 파일 | 역할 |
|---|---|
| `public/manifest.webmanifest` | 매니페스트 + `share_target` |
| `utils/installPrompt.js` | `beforeinstallprompt` 포착, OS 판정 |
| `hooks/useInstall.js` | 카드가 쓸 상태 |
| `components/InstallCard.jsx` | 홈 화면 안내 (3분기) |
| `utils/shareTarget.js` | 들어온 파라미터에서 링크 추출 |
| `src/manifest.test.js` | 매니페스트가 설치 가능한 상태인지 고정 |

**서비스 워커는 넣지 않았습니다.** 예전에는 설치 필수 조건이었지만 Chromium 151 stable 의 설치 판정 코드(`installable_evaluator.cc`, `app_banner_manager.cc`)에는 검사 자체가 없고 관련 오류 코드(`NO_MATCHING_SERVICE_WORKER`, `NOT_OFFLINE_CAPABLE` 등)가 전부 `DEPRECATED` 입니다. 이 앱은 백엔드 없이는 아무것도 못 하므로 오프라인 셸이 줄 것도 없습니다. 반면 서비스 워커는 한번 배포하면 사용자 기기에 남아 회수가 어렵습니다. 얻는 것 없이 부채만 지는 거래라 뺐습니다.

**`action` 은 반드시 `/` 입니다.** 두 가지 이유가 겹칩니다.

- `"/share"` 같은 경로는 정적 호스팅에서 404 라 React 가 부팅조차 못 합니다 — `/gets/` 가 이미 그렇게 죽어 있습니다.
- `"/?share=1"` 처럼 표식을 심는 것도 안 됩니다. **명세상 GET 이면 `action` 의 쿼리는 공유 데이터로 통째로 덮어써집니다.** 공유 진입 판별은 "어떤 이름의 파라미터가 왔는가" 로만 해야 합니다.

**링크가 어느 칸에 오는지는 정해져 있지 않습니다.** 안드로이드 인텐트에는 URL 전용 칸이 없어서(`EXTRA_TEXT` 만 있음) 링크는 대개 `text` 에, 제목과 섞여서 옵니다. 그래서 `extractSharedUrl` 이 `url` → `text` → `title` 순으로 훑고 **지원 도메인을 우선** 고릅니다. 공유 문구에 앱스토어 링크가 같이 붙어 오는 일이 있어서 먼저 나온 URL 을 집으면 엉뚱한 걸 잡습니다.

지원 도메인이 하나도 없으면 그래도 찾은 첫 URL 을 넘깁니다 — 조용히 아무 일도 안 일어나는 것보다 앱이 평소의 "지원하지 않는 링크" 를 말해 주는 편이 낫습니다.

**앱별로 무엇이 오는지는 실측 중입니다.** 문서화될 성질의 정보가 아니라(각 앱의 구현 세부사항) 1차 출처가 없습니다. 그래서 공유 진입 시 원본 파라미터를 기기에 기록하고(`utils/shareLog.js`, 최근 20건) `?sharelog=1` 에서 확인합니다. 기록은 기기 밖으로 나가지 않습니다.

**iOS 는 공유 시트에 들어갈 수 없습니다.** WebKit 의 Web Share Target 이슈(#194593)는 2019년에 열려 지금도 미배정 상태이고, Safari 27 에도 없습니다. 그래서 iOS 카드는 **"홈 화면에 추가" 까지만 약속합니다.** 공유 메뉴를 약속하면 거짓말이 됩니다 — `InstallCard.test.jsx` 가 그 문구가 iOS 분기에 새어 들어오지 않는지 검사합니다. (참고로 `navigator.share` 는 iOS 에서 동작합니다. 내보내는 Web Share API 와 받는 Web Share **Target** 은 다른 API 입니다.)

> ⚠️ 안드로이드에서 공유 시트 등록은 **WebAPK 설치**에 달려 있습니다. 설치가 WebAPK 가 아니라 단순 바로가기로 떨어지면 홈 화면 아이콘은 생겨도 공유 메뉴에는 나타나지 않습니다.

### 공유 위젯 (`components/ShareWidget.jsx`)

`더 알아보기` 옆에 붙는 세 가지 동작입니다.

| 구성요소 | 표시 | 조건 |
|---|---|---|
| 링크 복사하기 | 라벨 있는 알약 버튼 | 항상 |
| 공유 창 표시 | 아이콘만 | `navigator.share` 존재 시 (Android·iOS) |
| QR코드 표시 | 아이콘 | 항상 |

공유 URL 은 `https://musiknot-api.duckdns.org/s/<shareId>` 입니다. **프론트 주소가 아니라 백엔드 주소인 이유**는 GitHub Pages 가 정적이라 곡마다 다른 미리보기 메타 태그를 줄 수 없기 때문입니다.

**세 갈래로 나눈 이유.** 예전에는 버튼 하나가 "네이티브 공유를 시도하고 실패하면 클립보드"로 동작했는데, 누르기 전에 무슨 일이 일어날지 알 수 없었습니다.

공유 창 버튼은 데스크톱에서 **아예 렌더하지 않습니다** — 눌러도 반응 없는 버튼보다 없는 편이 낫습니다. 사용자가 시트를 닫은 것(`AbortError`)은 실패가 아니므로 조용히 끝냅니다.

> ⚠️ `navigator.share` 와 `navigator.clipboard` 는 **보안 컨텍스트(HTTPS 또는 localhost)** 에서만 동작합니다. LAN IP 로 접속해 HTTP 로 테스트하면 공유 버튼이 사라지고 복사도 실패하는데, 이는 코드 문제가 아니라 브라우저 정책입니다. 폰 테스트는 배포본(HTTPS)으로 하세요.

### QR 코드 (`components/QrCode.jsx`)

`uqr`(MIT, 3.9 kB gzip, 의존성 0)로 모듈 행렬을 얻어 SVG 를 직접 그립니다. 외부 QR API 를 쓰지 않는 이유는 공유 URL 이 제3자 서버로 새기 때문입니다.

정확성에 직결되는 값 두 가지가 있습니다.

- **여백(quiet zone) 4모듈.** `uqr` 기본값은 1이라 부족합니다. 모자라면 스캐너가 코드 경계를 찾지 못합니다.
- **색을 테마에 맡기지 않습니다.** QR 과 모달 카드를 양쪽 테마에서 흰 배경·검은 모듈로 고정합니다. 다크 모드에서 반전시키면 **보기엔 멀쩡한데 스캔이 안 됩니다.**

49자 URL 은 ECC `M` 에서 41×41(여백 포함), 220px 권장입니다. 독립 디코더로 왕복 검증했습니다.

## 5. 상태 관리

| 위치 | 상태 | 비고 |
|---|---|---|
| `useTheme` | `theme`, `isDark` | localStorage 영속화, `<html>`에 `.dark` 토글 |
| `useLanguage` | `lang`, `t(key)` | localStorage 영속화 (기본 `ko`) |
| `useParse` | `result`, `loading`, `error` | `/parse` 응답 |
| `App.jsx` 로컬 | `history` | 최근 검색 최대 10개, 메모리 only |

## 6. 백엔드 연동

**`src/constants/api.js`가 백엔드 주소의 단일 출처입니다.**

```js
export const API_BASE_URL = import.meta.env.DEV
    ? 'http://localhost:8000'
    : 'https://musiknot-api.duckdns.org'
```

`useParse.js`와 `useMelonMatch.js`가 이 상수를 import합니다. 예전에는 두 훅이 각자 주소를 들고 있었고, 그래서 한쪽이 `localhost` 하드코딩인 채로 드리프트했습니다. 상수를 하나로 모아 그 원인을 제거했습니다.

| Endpoint | Method | 용도 | 호출 위치 |
|---|---|---|---|
| `/parse` | POST | 음원 URL → 곡 메타/플랫폼 링크 | `useParse` |
| `/match` | POST | 제목·아티스트 → 멜론 매칭 | `useMelonMatch` (미사용) |

### ⚠ 백엔드 주소를 바꿀 때

`import.meta.env.DEV`는 Vite가 **빌드 시점에 정적으로 치환**합니다. 프로덕션 빌드에서는 삼항식이 상수 폴딩되어 `localhost` 분기가 번들에서 완전히 사라집니다(`dist` 내 `localhost` 문자열 0건으로 확인됨).

**즉 이 값은 번들에 박힙니다.** 서버만 바꾸고 재배포하지 않으면 사이트는 옛 주소를 계속 호출합니다. 반드시 `npm run deploy`까지 해야 합니다.

CORS는 백엔드의 `allow_origins`에 `https://musiknot.github.io`가 들어 있어서 동작합니다. 백엔드 주소가 바뀌어도 그 목록은 건드리지 않습니다 — CORS 오리진은 *호출하는 쪽*(프론트)이지 *호출받는 쪽*이 아닙니다.

## 7. 컴포넌트 트리 / 그리드 배치

```
App
├── Header (테마 / 언어 / 홈 / 메뉴)
├── HomeView                    # result === null
│   └── SearchBar
└── ResultView                  # result !== null
    └── PlatformGrid
        ├── 글로벌 5개 (3열 → 3+2 배치)
        ├── 구분선
        └── 한국 3개 (3열)
```

**두 그리드 모두 `grid-cols-3`입니다.** 글로벌은 5개라 3+2로 배치됩니다.

예전에는 글로벌이 `grid-cols-4`였는데, 5개를 4열에 넣으니 Amazon이 모든 화면 폭에서 둘째 줄에 혼자 떨어졌습니다. 게다가 한국 그리드는 3열이라 카드 크기가 37~40% 달랐습니다.

`grid-cols-5`는 실측으로 기각했습니다. 카드 내용물(40px 원 + 8px 여백 + 2줄 라벨 25px)에 **약 75px**이 필요한데, 5열은 320px에서 48px, 414px에서도 66.8px라 어떤 폰에서도 내용물이 넘칩니다. 5열은 뷰포트 445px 이상에서만 성립합니다.

3열 실측치:

| 뷰포트 | 카드 크기 | 두 그리드 일치 | 75px 하한 |
|---|---|---|---|
| 320px | 88.0px | ✅ | ✅ |
| 375px | 106.3px | ✅ | ✅ |
| 390px | 111.3px | ✅ | ✅ |
| 512px | 152.0px | ✅ | ✅ |

## 8. 스타일링

- Tailwind CSS v4 유틸리티를 JSX에 직접 사용
- `src/index.css`에서 `@import "tailwindcss"` + `@variant dark (.dark &)`
- 다크 모드는 `<html>`의 `.dark` 클래스로 토글 (시스템 설정 반영 옵션 포함)
- CSS Modules / styled-components 미사용

## 9. 지원 음원 서비스 (`utils/urlValidator.js`)

- 글로벌: Spotify, Apple Music, YouTube / YouTube Music, Amazon Music
- 한국: Melon, Bugs, FLO
- 단축 링크: `kko.to` (Kakao), `flomuz.io` (FLO)

화이트리스트에 없는 URL은 검색 단계에서 거부됩니다.

> ⚠ **Spotify와 Amazon은 화이트리스트에 있지만 백엔드가 501을 반환합니다.** 사용자에게는 일반적인 "서버 오류"로 보입니다. 도메인을 빼거나 전용 메시지를 주는 편이 낫습니다.

## 10. 개발 / 배포 명령어

```bash
npm run dev        # Vite 개발 서버 (http://localhost:5173)
npm run build      # 프로덕션 빌드 → dist/
npm run preview    # 빌드 결과 로컬 미리보기 (기본 포트 4173)
npm run lint       # ESLint
npm test           # vitest 1회 실행
npm run test:watch # vitest 감시 모드
npm run deploy     # vite build && gh-pages -d dist  (GitHub Pages 배포)
```

> ⚠️ `npm run preview` 의 기본 포트 **4173 은 백엔드 CORS 허용 목록에 없습니다** (3000·5173만 있음). 프로덕션 빌드를 로컬에서 확인하려면 `npm run preview -- --port 5173` 을 쓰세요. 안 그러면 검색할 때 `Failed to fetch` 가 납니다 — 코드 버그가 아니라 설정 문제입니다.

배포 후 확인:

```bash
curl -s https://musiknot.github.io/ | grep -o 'assets/index-[A-Za-z0-9_-]*\.js'
# 새 해시로 바뀌었는지 확인 (반영에 30~60초 걸림)
```

## 11. 테스트

```bash
npm test    # 52개, 네트워크 없이 실행
```

`vitest` + `@testing-library/react` + `jsdom`. 설정은 `vite.config.js` 의 `test` 블록, 공통 준비는 `src/test/setup.js` 입니다.

**렌더링을 두루 확인하는 테스트가 아닙니다.** 이 프로젝트에서 실제로 깨졌거나 조용히 깨질 수 있는 것만 고정합니다.

| 파일 | 지키는 것 |
|---|---|
| `hooks/useParse.test.jsx` | `parse`·`reset`·`parseById` 의 **참조가 유지**되는가 (무한 루프의 근본 원인) |
| `App.test.jsx` | `?id=` / `?url=` 진입 시 요청이 **정확히 1회**인가 (StrictMode 이중 실행 포함) |
| `components/ShareWidget.test.jsx` | `navigator.share` 가 없을 때 버튼을 **렌더하지 않는가**, 클립보드 실패 폴백, QR 열기/닫기 |
| `components/InstallCard.test.jsx` | 분기마다 **약속하는 내용이 다르다** — iOS 에 공유 메뉴를 약속하지 않는가, 이미 설치했는데 또 설치하라고 하지 않는가 |
| `utils/shareTarget.test.js` | 링크가 `url`·`text`·`title` 중 어디로 와도 찾아내는가, 여러 개 중 지원 도메인을 고르는가 |
| `manifest.test.js` | 매니페스트가 **설치 가능한 상태로** 남아 있는가 (깨지면 공유 시트에서 조용히 사라진다) |

요청 횟수를 세는 이유는 성능이 아니라 **안전**입니다. `/parse` 한 번이 백엔드에서 외부 호출 약 7건이 되고 거기에 멜론·벅스·FLO 스크래핑이 포함되는데, 그쪽에서 IP 가 차단당하는 것은 이 시스템에서 유일하게 되돌릴 수 없는 실패입니다. 아래 12절의 사고가 바로 그것이었습니다.

회귀를 실제로 잡는지 확인했습니다 — `useParse` 의 `useCallback` 을 없애면 2개, `App` 의 `didAutoSearch` 빗장을 없애면 1개(StrictMode 케이스, 바로 그 루프), 공유 버튼을 조건 없이 렌더하면 1개가 실패합니다.

### 설정에서 걸리는 두 가지

- **`esbuild: { jsx: 'automatic' }` 가 없으면** vitest 가 테스트 파일의 JSX 를 classic 런타임으로 변환해 전부 `React is not defined` 로 죽습니다. 앱 코드는 `@vitejs/plugin-react` 가 처리하지만 테스트 파일은 그 경로를 타지 않습니다.
- **모킹되지 않은 `fetch` 는 예외를 던집니다.** `undefined` 를 돌려주면 네트워크 모킹을 깜빡한 테스트가 조용히 통과합니다. `setup.js` 는 `matchMedia` 도 스텁합니다 — jsdom 에 없고 `useTheme` 가 씁니다.

### 백엔드와의 경계 계약

플랫폼 식별자는 **네 곳**에 중복 정의돼 있습니다: 백엔드 `Platform` enum, `PlatformIds` 필드, 프론트 카드 `id`, `deepLinks` 키. 어긋나면 아무 오류 없이 해당 카드만 사라집니다. `backend/tests/test_platform_contract.py` 가 `src/constants/platforms.js` 를 직접 읽어 네 곳의 일치를 검증합니다 — 즉 **`platforms.js` 를 고치면 백엔드 `pytest` 가 깨질 수 있습니다.** 그게 의도입니다.

## 12. 알려진 문제

`npm run lint` 는 현재 **오류 0개**입니다.

**⚠️ `useParse` 의 `parse`·`reset` 은 반드시 `useCallback` 으로 감싸져 있어야 합니다.** 이걸 풀면 렌더마다 새 함수가 되고, 이를 의존성으로 쓰는 `App.jsx` 의 `handleSearch` → `useEffect` 가 매 렌더마다 재실행되어 **무한 루프**가 됩니다. 실제로 그렇게 만들었다가 백엔드가 멜론을 초당 수천 번 호출한 적이 있습니다.

방어가 두 겹입니다.
1. `useParse` 가 `parse`·`reset` 을 메모이제이션합니다 (근본 원인)
2. `App.jsx` 가 `didAutoSearch` ref 빗장으로 자동 검색을 1회로 못박습니다 — 다른 훅의 참조 안정성에 의존하지 않기 위해서입니다

`App.jsx` 의 마운트 effect 는 `react-hooks/set-state-in-effect` 를 의도적으로 끕니다. "URL 이라는 외부 시스템을 읽어 조회를 시작하는 것" 은 effect 의 정당한 용도이고, `queueMicrotask` 로 감싸면 규칙은 통과하지만 코드가 나아지지는 않습니다. 이유를 코드 주석에 남겨뒀습니다.

**아직 구현되지 않은 UI 요소들** — 의도된 자리표시자입니다.
- `ResultView.jsx`의 "더 알아보기" 버튼 (Last.fm 연동 예정, 현재 `onClick` 없음)
- "Powered by Last.fm" 표기 (연동 코드 없음)
- `Header.jsx` 메뉴의 "이용 방법" / "문의" (배포 시 추가 예정)
- 홈 부제의 단축 링크(`mus.kn`) 안내 — 도메인 비용 문제로 미구현

**헤더 드롭다운이 바깥 클릭으로 닫히지 않습니다.** `closeAll()`이 항목 선택 시에만 호출되고 document 클릭 리스너가 없습니다.

## 13. 그 밖에

- 모바일에서는 Android `intent://` 스킴으로 네이티브 앱을 직접 열고, 그 외에는 일반 `https://` 링크로 폴백합니다 (`PlatformCard` + `constants/platforms.js`).
- `platforms.js`에서 YouTube와 YT Music이 같은 색(`#FF0000`)과 같은 이니셜(`Y`)을 씁니다. 카드가 작을 때 10px 라벨로만 구분됩니다.
- `App.css`, `src/assets/*`는 Vite 템플릿 잔재로 현재 화면에서 사용되지 않습니다.
- `index.html.bak`는 React 도입 이전의 단일 HTML 스냅샷이며, 같은 맥락의 정적 페이지가 `legacy/`에도 있습니다.
