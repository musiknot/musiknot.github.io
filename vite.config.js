import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'

export default defineConfig({
  plugins: [
    react(),
    tailwindcss(),
  ],
  base: '/',
  // 테스트 파일의 JSX 도 자동 런타임으로 변환한다. 이게 없으면 vitest 가
  // classic 변환을 써서 `React is not defined` 가 난다 — 앱 코드는 플러그인이
  // 처리하지만 테스트 파일은 그 경로를 타지 않는다.
  esbuild: { jsx: 'automatic' },
  test: {
    environment: 'jsdom',
    globals: true,
    setupFiles: './src/test/setup.js',
    include: ['src/**/*.test.{js,jsx}'],
  },
})