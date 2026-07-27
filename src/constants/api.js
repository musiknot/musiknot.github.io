// 백엔드 API 베이스 URL — 프론트엔드 전체가 이 상수 하나만 공유한다.
//
// import.meta.env.DEV 는 vite 가 빌드 시점에 정적으로 치환하는 값이다.
//   npm run dev   → true  → http://localhost:8000
//   npm run build → false → Railway URL
// 프로덕션 빌드에서는 삼항식이 상수 폴딩되어 localhost 분기가
// 번들에서 완전히 제거된다 (dist 내 'localhost' 문자열 0건).
export const API_BASE_URL = import.meta.env.DEV
    ? 'http://localhost:8000'
    : 'https://musiknotgithubio-production.up.railway.app'
