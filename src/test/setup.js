import '@testing-library/jest-dom/vitest'
import { cleanup } from '@testing-library/react'
import { afterEach, beforeEach, vi } from 'vitest'

// jsdom 에는 matchMedia 가 없다. useTheme 가 시스템 다크모드를 감지할 때 쓴다.
// 기본은 '시스템이 라이트 모드' 로 둔다 — 테마별 동작을 보려면 테스트에서
// 이 스텁을 덮어쓰면 된다.
if (!window.matchMedia) {
    window.matchMedia = (query) => ({
        matches: false,
        media: query,
        onchange: null,
        addEventListener: () => {},
        removeEventListener: () => {},
        addListener: () => {},      // 구형 API — 아직 쓰는 코드가 있을 수 있다
        removeListener: () => {},
        dispatchEvent: () => false,
    })
}

// 테스트가 실수로 진짜 네트워크를 때리지 못하게 막는다.
// 기본 구현을 '실패'로 두면, fetch 를 모킹하지 않은 테스트가 조용히
// 통과하는 대신 시끄럽게 깨진다.
beforeEach(() => {
    globalThis.fetch = vi.fn(() => {
        throw new Error(
            '이 테스트에서 모킹되지 않은 fetch 가 호출됐다. ' +
            '요청을 검증하려면 globalThis.fetch 를 명시적으로 모킹할 것.'
        )
    })
})

afterEach(() => {
    cleanup()
    vi.restoreAllMocks()
    vi.unstubAllGlobals()
})
