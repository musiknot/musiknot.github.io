/**
 * 마운트 시 URL 자동 검색이 **정확히 한 번만** 일어나는지.
 *
 * 이 앱에서 한 번의 /parse 는 백엔드에서 외부 서비스 호출 약 7건이 된다.
 * 그중에는 멜론·벅스·FLO 스크래핑이 포함되고, 그쪽에서 IP 가 차단당하는 것은
 * 이 시스템에서 유일하게 되돌릴 수 없는 실패다. 그래서 "몇 번 호출되는가"는
 * 성능 문제가 아니라 안전 문제다.
 *
 * 실제로 한 번 깨졌다. effect 의존성을 채웠더니 매 렌더마다 재실행되어
 * 초당 수천 건이 나갔다. 방어는 두 겹이고(useParse 의 메모이제이션,
 * App 의 didAutoSearch ref), 이 테스트는 그 결과를 검증한다.
 *
 * React StrictMode 는 개발 모드에서 effect 를 의도적으로 두 번 실행한다.
 * 아래 StrictMode 테스트가 그걸 재현한다 — 빗장이 없으면 2회가 된다.
 */
import { render, screen, waitFor } from '@testing-library/react'
import { StrictMode } from 'react'
import { describe, expect, it, vi } from 'vitest'
import App from './App'

const SONG = {
    title: '밤편지', artist: '아이유', album: 'Palette', albumArt: null, isrc: null,
    platforms: { spotify: null, appleMusic: '1219218446', youtube: null,
                 youtubeMusic: null, melon: '30314784', bugs: null, flo: null, amazon: null },
    shareId: 'melon:30314784',
}

function mockFetch() {
    const fn = vi.fn(async () => ({ ok: true, json: async () => SONG }))
    globalThis.fetch = fn
    return fn
}

/** jsdom 의 주소를 바꾼다. App 은 마운트 시 이걸 읽는다. */
function setUrl(search) {
    window.history.replaceState({}, '', `/${search}`)
}

describe('마운트 시 자동 검색', () => {
    it('?id= 로 들어오면 요청이 정확히 1회', async () => {
        const fetchMock = mockFetch()
        setUrl('?id=melon:30314784')

        render(<App />)

        await waitFor(() => expect(screen.getByRole('heading', { name: '밤편지' })).toBeInTheDocument())
        expect(fetchMock).toHaveBeenCalledTimes(1)
        expect(JSON.parse(fetchMock.mock.calls[0][1].body)).toEqual({ id: 'melon:30314784' })
    })

    it('?url= 로 들어오면 요청이 정확히 1회', async () => {
        const fetchMock = mockFetch()
        setUrl('?url=https%3A%2F%2Fwww.melon.com%2Fsong%2Fdetail.htm%3FsongId%3D30314784')

        render(<App />)

        await waitFor(() => expect(screen.getByRole('heading', { name: '밤편지' })).toBeInTheDocument())
        expect(fetchMock).toHaveBeenCalledTimes(1)
    })

    it('StrictMode 가 effect 를 두 번 돌려도 요청은 1회 (ref 빗장)', async () => {
        const fetchMock = mockFetch()
        setUrl('?id=melon:30314784')

        render(<StrictMode><App /></StrictMode>)

        await waitFor(() => expect(screen.getByRole('heading', { name: '밤편지' })).toBeInTheDocument())
        expect(fetchMock).toHaveBeenCalledTimes(1)
    })

    it('공유 시트가 text 에 제목과 링크를 섞어 보내도 1회', async () => {
        // 설치된 PWA 로 공유하면 여기로 들어온다. 안드로이드 앱들은 링크를
        // url 이 아니라 text 에 담아 보내는 경우가 많다.
        const fetchMock = mockFetch()
        setUrl('?text=' + encodeURIComponent(
            '밤편지 https://www.melon.com/song/detail.htm?songId=30314784'))

        render(<App />)

        await waitFor(() => expect(screen.getByRole('heading', { name: '밤편지' })).toBeInTheDocument())
        expect(fetchMock).toHaveBeenCalledTimes(1)
        expect(JSON.parse(fetchMock.mock.calls[0][1].body))
            .toEqual({ url: 'https://www.melon.com/song/detail.htm?songId=30314784' })
    })

    it('파라미터가 없으면 아무 요청도 하지 않는다', async () => {
        const fetchMock = mockFetch()
        setUrl('')

        render(<App />)

        // 자동 검색이 없으면 홈 화면이 뜬다
        await waitFor(() => expect(screen.getByRole('button', { name: /Musiknot/ })).toBeInTheDocument())
        expect(fetchMock).not.toHaveBeenCalled()
    })

    it('렌더가 여러 번 일어나도 요청이 늘어나지 않는다 (루프 회귀 방지)', async () => {
        const fetchMock = mockFetch()
        setUrl('?id=melon:30314784')

        const { rerender } = render(<App />)
        await waitFor(() => expect(screen.getByRole('heading', { name: '밤편지' })).toBeInTheDocument())

        rerender(<App />)
        rerender(<App />)
        rerender(<App />)
        await new Promise(r => setTimeout(r, 50))

        expect(fetchMock).toHaveBeenCalledTimes(1)
    })
})
