/**
 * 공유 시트로 들어온 데이터에서 링크 뽑아내기.
 *
 * 이 함수가 존재하는 이유는 명세의 빈틈이다. Web Share Target 은 title/text/url
 * 세 칸을 정의하지만 **보내는 앱이 링크를 어디 담을지는 강제하지 않는다.**
 * 그래서 "url 칸에 오겠지" 라고 가정하면 실제 기기에서 조용히 아무 일도
 * 일어나지 않는다 — 사용자 입장에서는 공유했는데 홈 화면만 뜨는 것이다.
 *
 * 아래 케이스는 안드로이드 앱들이 실제로 만들어내는 모양을 옮긴 것이다.
 */
import { describe, expect, it } from 'vitest'
import { extractSharedUrl } from './shareTarget'

const MELON = 'https://www.melon.com/song/detail.htm?songId=30314784'
const KKO   = 'https://kko.to/abcdef'

describe('extractSharedUrl — 링크가 어느 칸에 오든', () => {
    it('url 칸에 깔끔하게 오는 경우', () => {
        expect(extractSharedUrl({ url: MELON })).toBe(MELON)
    })

    it('text 에 제목과 섞여 오는 경우', () => {
        expect(extractSharedUrl({ text: `밤편지 ${MELON}` })).toBe(MELON)
    })

    it('줄바꿈과 대괄호가 섞인 경우', () => {
        expect(extractSharedUrl({ text: `[Melon] 아이유 - 밤편지\n${KKO}` })).toBe(KKO)
    })

    it('title 에만 있는 경우', () => {
        expect(extractSharedUrl({ title: MELON })).toBe(MELON)
    })

    it('앞뒤 공백은 떼어낸다', () => {
        expect(extractSharedUrl({ url: `  ${MELON}  ` })).toBe(MELON)
    })
})

describe('extractSharedUrl — 여러 링크 중 고르기', () => {
    it('지원하는 도메인을 우선한다', () => {
        // 공유 문구에 앱스토어 링크가 같이 붙어 오는 일이 흔하다.
        // 먼저 나온 URL 을 집으면 엉뚱한 걸 잡는다.
        const text = `이 앱으로 들어보세요 https://play.google.com/store/apps/x 곡: ${MELON}`
        expect(extractSharedUrl({ text })).toBe(MELON)
    })

    it('url 칸이 지원 도메인이 아니고 text 가 맞으면 text 를 고른다', () => {
        expect(extractSharedUrl({ url: 'https://example.com/x', text: MELON })).toBe(MELON)
    })

    it('지원 도메인이 하나도 없으면 첫 URL 을 돌려준다', () => {
        // 조용히 실패하는 대신 앱이 평소의 "지원하지 않는 링크" 에러를 내게 한다.
        const url = 'https://example.com/song'
        expect(extractSharedUrl({ text: `들어봐 ${url}` })).toBe(url)
    })
})

describe('extractSharedUrl — 끝에 붙은 문장부호', () => {
    it('닫는 괄호가 URL 밖이면 떼어낸다', () => {
        expect(extractSharedUrl({ text: `좋더라 (${MELON})` })).toBe(MELON)
    })

    it('마침표와 쉼표를 떼어낸다', () => {
        expect(extractSharedUrl({ text: `${MELON}.` })).toBe(MELON)
        expect(extractSharedUrl({ text: `${MELON}, 어때?` })).toBe(MELON)
    })

    it('URL 안의 정상적인 괄호는 남긴다', () => {
        // 괄호 짝이 맞으면 URL 의 일부로 본다.
        const withParens = 'https://music.apple.com/kr/album/foo_(bar)'
        expect(extractSharedUrl({ text: withParens })).toBe(withParens)
    })
})

describe('extractSharedUrl — 아무것도 없을 때', () => {
    it.each([
        ['빈 객체',        {}],
        ['인자 없음',      undefined],
        ['URL 없는 텍스트', { text: '밤편지 아이유', title: '공유' }],
        ['빈 문자열',      { url: '', text: '', title: '' }],
        ['숫자가 들어온 경우', { url: 42, text: null }],
    ])('%s → null', (_, input) => {
        expect(extractSharedUrl(input)).toBeNull()
    })
})
