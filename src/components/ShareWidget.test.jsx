/**
 * 공유 위젯 — 환경에 따라 무엇이 보이는가.
 *
 * 핵심은 하나다: `navigator.share` 가 없는 환경(대부분의 데스크톱, 그리고
 * HTTP 로 접속한 모든 경우)에서 공유 시트 버튼을 **아예 렌더하지 않는 것**.
 * 눌러도 아무 일이 없는 버튼을 보여주는 것보다 없는 편이 낫다.
 *
 * `navigator.share` 와 `navigator.clipboard` 는 보안 컨텍스트(HTTPS 또는
 * localhost)에서만 존재한다. LAN IP 로 폰에서 테스트하면 둘 다 사라지는데,
 * 그건 버그가 아니라 브라우저 정책이다.
 */
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { ShareWidget } from './ShareWidget'

const t = (k) => k          // 번역 키를 그대로 돌려준다 — 라벨 대신 키로 찾는다
const URL = 'https://musiknot-api.duckdns.org/s/melon:30314784'

const renderWidget = (props = {}) =>
    render(<ShareWidget url={URL} title="밤편지" artist="아이유" t={t} {...props} />)

afterEach(() => {
    // ShareWidget 은 모듈 로드 시점에 navigator.share 를 읽으므로
    // 모듈 캐시를 비워야 다음 테스트가 새로 판단한다.
    vi.resetModules()
})

describe('공유 시트 버튼', () => {
    it('navigator.share 가 없으면 렌더하지 않는다', async () => {
        vi.stubGlobal('navigator', { clipboard: { writeText: vi.fn() } })
        const { ShareWidget: Fresh } = await import('./ShareWidget?nonative')

        render(<Fresh url={URL} title="밤편지" artist="아이유" t={t} />)

        expect(screen.queryByLabelText('shareOpenSheet')).not.toBeInTheDocument()
        // 나머지 둘은 항상 있어야 한다
        expect(screen.getByLabelText('shareCopyLink')).toBeInTheDocument()
        expect(screen.getByLabelText('shareShowQr')).toBeInTheDocument()
    })
})

describe('링크 복사', () => {
    it('클립보드에 공유 URL 을 쓰고 확인 표시를 보여준다', async () => {
        const writeText = vi.fn(async () => {})
        vi.stubGlobal('navigator', { clipboard: { writeText } })

        renderWidget()
        await userEvent.click(screen.getByLabelText('shareCopyLink'))

        expect(writeText).toHaveBeenCalledWith(URL)
        expect(await screen.findByText('shareCopied')).toBeInTheDocument()
    })

    it('클립보드가 막혀 있으면 사용자가 직접 복사할 수 있게 안내한다', async () => {
        vi.stubGlobal('navigator', {
            clipboard: { writeText: vi.fn(async () => { throw new Error('denied') }) },
        })
        const prompt = vi.fn()
        vi.stubGlobal('prompt', prompt)

        renderWidget()
        await userEvent.click(screen.getByLabelText('shareCopyLink'))

        expect(prompt).toHaveBeenCalledWith('shareFailed', URL)
    })
})

describe('QR 코드', () => {
    it('버튼을 누르면 열리고, 안에 QR SVG 가 있다', async () => {
        vi.stubGlobal('navigator', { clipboard: { writeText: vi.fn() } })
        renderWidget()

        expect(screen.queryByRole('dialog')).not.toBeInTheDocument()
        await userEvent.click(screen.getByLabelText('shareShowQr'))

        const dialog = await screen.findByRole('dialog')
        expect(dialog).toBeInTheDocument()
        // QrCode 는 공유 URL 을 aria-label 로 단다
        expect(screen.getByLabelText(URL)).toBeInTheDocument()
    })

    it('Escape 로 닫힌다', async () => {
        vi.stubGlobal('navigator', { clipboard: { writeText: vi.fn() } })
        renderWidget()

        await userEvent.click(screen.getByLabelText('shareShowQr'))
        expect(await screen.findByRole('dialog')).toBeInTheDocument()

        await userEvent.keyboard('{Escape}')
        expect(screen.queryByRole('dialog')).not.toBeInTheDocument()
    })
})

describe('공유 URL 이 없을 때', () => {
    it('아무것도 렌더하지 않는다', () => {
        const { container } = renderWidget({ url: null })
        expect(container).toBeEmptyDOMElement()
    })
})
