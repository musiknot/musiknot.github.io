/**
 * useParse 의 **참조 안정성**.
 *
 * 이 테스트는 실제로 일어난 장애에서 나왔다. `parse` 가 useCallback 으로
 * 감싸여 있지 않던 시절, App.jsx 의 마운트 effect 의존성을 채웠더니 무한
 * 렌더 루프가 생겼다:
 *
 *     parse → setLoading → 리렌더 → 새 parse → effect 재실행 → parse → …
 *
 * 프론트엔드에서는 조용히 도는 루프라 눈에 띄지 않았고, **백엔드가 멜론을
 * 초당 수천 번 호출하기 시작해서야** 발견됐다. 서비스 메모리 상한(384M)까지
 * 찼다.
 *
 * 그래서 여기서 지키는 것은 "동작이 맞다"가 아니라 "함수의 참조가 바뀌지
 * 않는다"이다. 그게 깨지는 순간 루프가 되살아난다.
 */
import { renderHook, act } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'
import { useParse } from './useParse'

const okResponse = (body) => ({ ok: true, json: async () => body })

describe('useParse — 참조 안정성', () => {
    it('리렌더를 반복해도 parse 와 reset 의 참조가 그대로여야 한다', () => {
        const { result, rerender } = renderHook(() => useParse())

        const first = { parse: result.current.parse, reset: result.current.reset }

        rerender()
        rerender()
        rerender()

        expect(result.current.parse).toBe(first.parse)
        expect(result.current.reset).toBe(first.reset)
    })

    it('상태가 바뀐 뒤에도 참조가 유지되어야 한다', async () => {
        globalThis.fetch = vi.fn(async () => okResponse({ title: 't', artist: 'a', platforms: {} }))

        const { result } = renderHook(() => useParse())
        const before = result.current.parse

        // 상태 변화(loading→result)를 실제로 일으킨다. 루프를 만들었던 그 경로다.
        await act(async () => {
            await result.current.parse('https://www.melon.com/song/detail.htm?songId=1')
        })

        expect(result.current.result).not.toBeNull()
        expect(result.current.parse).toBe(before)   // 여기가 깨지면 루프가 돌아온다
    })

    it('parseById 도 같은 보장을 가져야 한다', () => {
        const { result, rerender } = renderHook(() => useParse())
        const before = result.current.parseById
        rerender()
        expect(result.current.parseById).toBe(before)
    })
})

describe('useParse — 요청', () => {
    it('parse 는 url 을, parseById 는 id 를 보낸다', async () => {
        globalThis.fetch = vi.fn(async () => okResponse({ title: 't', artist: 'a', platforms: {} }))
        const { result } = renderHook(() => useParse())

        await act(async () => {
            await result.current.parse('https://www.melon.com/song/detail.htm?songId=1')
        })
        expect(JSON.parse(globalThis.fetch.mock.calls[0][1].body))
            .toEqual({ url: 'https://www.melon.com/song/detail.htm?songId=1' })

        await act(async () => { await result.current.parseById('melon:1') })
        expect(JSON.parse(globalThis.fetch.mock.calls[1][1].body)).toEqual({ id: 'melon:1' })
    })

    it('지원하지 않는 링크는 네트워크에 나가기 전에 막는다', async () => {
        globalThis.fetch = vi.fn()
        const { result } = renderHook(() => useParse())

        await act(async () => { await result.current.parse('https://example.com/nope') })

        expect(globalThis.fetch).not.toHaveBeenCalled()
        expect(result.current.error).toBeTruthy()
    })
})
