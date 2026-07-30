/**
 * 홈 화면 안내 카드가 **환경에 맞는 말만** 하는지.
 *
 * 이 카드는 원래 OS 별 세 갈래였는데 React 이전 때 판정 로직이 통째로 빠지고
 * 데스크톱용 문구만 남았다. 그래서 모바일에서도 "모바일로 접속하세요" 라고
 * 말하고 있었다.
 *
 * 여기서 지키는 것은 렌더링이 아니라 **문구가 하는 약속**이다. 분기마다
 * 약속하는 게 다르고, 틀린 분기가 뜨면 없는 기능을 광고하게 된다:
 *
 *   설치 가능 → "공유 메뉴에 뜬다"    (설치해야 실제로 그렇게 된다)
 *   iOS      → "홈 화면에 추가"       (iOS 는 Web Share Target 을 지원하지
 *                                      않으므로 공유 메뉴는 약속하면 안 된다)
 *   설치됨    → "공유 메뉴를 써 보세요" (설치하라고 또 말하면 안 된다)
 */
import { render, screen } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'

import { translations } from '../constants/translations'

const t = (key) => translations.ko[key] ?? key

/**
 * useInstall 이 돌려주는 값을 고정한다. 진짜 브라우저 신호(beforeinstallprompt,
 * display-mode)는 테스트에서 만들 수 없다.
 *
 * **InstallCard 를 정적으로 import 하면 안 된다.** 그러면 모듈이 먼저 캐시되어
 * 첫 동적 import 가 모킹되지 않은 실물을 돌려주고, 두 번째 테스트부터만
 * 모킹이 먹는다 — 테스트가 실행 순서에 의존하게 된다. 실제로 그렇게 만들었다가
 * 첫 테스트만 실패했다.
 */
async function mockInstall(state) {
    vi.resetModules()
    vi.doMock('../hooks/useInstall', () => ({
        useInstall: () => ({ os: 'other', canInstall: false, installed: false, install: vi.fn(), ...state }),
    }))
    return (await import('./InstallCard')).InstallCard
}

afterEach(() => {
    vi.resetModules()
    vi.doUnmock('../hooks/useInstall')
})

describe('InstallCard', () => {
    it('설치 가능하면 설치 버튼을 준다', async () => {
        const Card = await mockInstall({ os: 'android', canInstall: true })
        render(<Card t={t} />)

        expect(screen.getByRole('button', { name: t('installAction') })).toBeInTheDocument()
        expect(screen.getByText(t('installTitle'))).toBeInTheDocument()
    })

    it('버튼을 누르면 설치 프롬프트를 띄운다', async () => {
        const install = vi.fn()
        const Card = await mockInstall({ os: 'android', canInstall: true, install })
        render(<Card t={t} />)

        screen.getByRole('button', { name: t('installAction') }).click()
        expect(install).toHaveBeenCalledTimes(1)
    })

    it('이미 설치했으면 설치하라고 하지 않는다', async () => {
        const Card = await mockInstall({ os: 'android', canInstall: true, installed: true })
        render(<Card t={t} />)

        expect(screen.queryByRole('button')).not.toBeInTheDocument()
        expect(screen.getByText(t('installedNote'))).toBeInTheDocument()
    })

    it('iOS 에는 공유 메뉴를 약속하지 않는다', async () => {
        // iOS 는 Web Share Target 을 지원하지 않는다. 홈 화면에 추가해도
        // 음악 앱의 공유 메뉴에는 Musiknot 이 나타나지 않는다.
        const Card = await mockInstall({ os: 'ios' })
        render(<Card t={t} />)

        expect(screen.getByText(t('iosTitle'))).toBeInTheDocument()
        expect(screen.queryByText(t('installTitle'))).not.toBeInTheDocument()
        expect(screen.queryByRole('button')).not.toBeInTheDocument()
    })

    it('데스크톱에서는 기존 안내를 그대로 둔다', async () => {
        const Card = await mockInstall({ os: 'other' })
        render(<Card t={t} />)

        expect(screen.getByText(t('mobileNotice'))).toBeInTheDocument()
        expect(screen.queryByRole('button')).not.toBeInTheDocument()
    })

    it('설치 불가한 안드로이드에 설치 버튼을 띄우지 않는다', async () => {
        // UA 가 안드로이드라고 무조건 설치할 수 있는 게 아니다. 눌러도 아무
        // 일이 없는 버튼을 보여주느니 없는 게 낫다.
        const Card = await mockInstall({ os: 'android', canInstall: false })
        render(<Card t={t} />)

        expect(screen.queryByRole('button')).not.toBeInTheDocument()
    })
})
