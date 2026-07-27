// 백엔드 API 베이스 URL — 프론트엔드 전체가 이 상수 하나만 공유한다.
//
// import.meta.env.DEV 는 vite 가 빌드 시점에 정적으로 치환하는 값이다.
//   npm run dev   → true  → http://localhost:8000
//   npm run build → false → 운영 백엔드
// 프로덕션 빌드에서는 삼항식이 상수 폴딩되어 localhost 분기가
// 번들에서 완전히 제거된다 (dist 내 'localhost' 문자열 0건).
//
// 운영 백엔드는 Oracle Cloud(ap-osaka-1) VM 에서 uvicorn 이 127.0.0.1:8000 에
// 떠 있고 Caddy 가 TLS 를 종단해 역방향 프록시한다. 호스트명은 DuckDNS 다.
// 이 값이 바뀌면 반드시 `npm run deploy` 로 다시 배포해야 한다 —
// 빌드 시점에 번들에 박히므로 서버만 바꾸면 사이트는 옛 주소를 계속 부른다.
export const API_BASE_URL = import.meta.env.DEV
    ? 'http://localhost:8000'
    : 'https://musiknot-api.duckdns.org'
