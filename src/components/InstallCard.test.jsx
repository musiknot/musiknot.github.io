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
 *   Android    → 설치 버튼 또는 수동 설치 경로 (설치 신호가 없어도 안내한다)
 *   iOS      → 단축어 설치              (iOS 는 Web Share Target 을 지원하지
 *                                      않으므로 Apple 단축어로 공유 메뉴를 연다)
 *   설치됨    → "공유 메뉴를 써 보세요" (설치하라고 또 말하면 안 된다)
 */
import { render, screen } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'

import { translations } from '../constants/translations'
import { IOS_SHORTCUT_URL } from '../constants/shortcuts'

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

    it('iOS 에는 단축어 설치 링크를 준다', async () => {
        // iOS 는 Web Share Target 을 지원하지 않는다. PWA 설치를 권하는 대신
        // 음악 앱의 공유 시트에서 실행할 iCloud 단축어를 제공한다.
        const Card = await mockInstall({ os: 'ios' })
        render(<Card t={t} />)

        expect(screen.getByText(t('iosShortcutTitle'))).toBeInTheDocument()
        expect(screen.getByRole('link', { name: t('iosShortcutAction') }))
            .toHaveAttribute('href', IOS_SHORTCUT_URL)
        expect(screen.queryByText(t('installTitle'))).not.toBeInTheDocument()
        expect(screen.queryByText('홈 화면에 추가')).not.toBeInTheDocument()
    })

    it('데스크톱에서는 기존 안내를 그대로 둔다', async () => {
        const Card = await mockInstall({ os: 'other' })
        render(<Card t={t} />)

        expect(screen.getByText(t('mobileNotice'))).toBeInTheDocument()
        expect(screen.queryByRole('button')).not.toBeInTheDocument()
    })

    it('설치 신호가 없는 안드로이드에도 수동 PWA 설치 경로를 안내한다', async () => {
        // beforeinstallprompt가 없어도 Chrome 메뉴에서는 설치가 가능할 수 있다.
        // 일반 모바일 안내로 떨어뜨리면 사용자가 그 경로를 알 수 없다.
        const Card = await mockInstall({ os: 'android', canInstall: false })
        render(<Card t={t} />)

        expect(screen.getByText(t('androidInstallTitle'))).toBeInTheDocument()
        expect(screen.getByText(t('androidInstallBody'))).toBeInTheDocument()
        expect(screen.queryByText(t('mobileNotice'))).not.toBeInTheDocument()
        expect(screen.queryByRole('button')).not.toBeInTheDocument()
    })
})
