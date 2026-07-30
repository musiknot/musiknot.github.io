/**
 * 매니페스트가 **설치 가능한 상태로** 남아 있는지.
 *
 * 이 파일의 값이 하나라도 어긋나면 설치가 조용히 안 되고, 설치가 안 되면
 * 공유 시트에 Musiknot 이 뜨지 않는다 — Web Share Target 은 설치된 앱에만
 * 등록되기 때문이다. 화면에는 아무 오류도 안 뜨고 그냥 기능이 없어진다.
 *
 * 기준은 추측이 아니라 Chromium 151 stable 브랜치의 설치 판정 코드
 * (installable_evaluator.cc, manifest_icon_selector.cc) 와 W3C appmanifest
 * 초안(2026-07-23)에서 확인한 것이다.
 *
 * 참고로 **서비스 워커는 넣지 않았다.** 예전에는 필수였지만 현재 코드에는
 * 검사 자체가 없고(NO_MATCHING_SERVICE_WORKER 등이 전부 DEPRECATED), 이 앱은
 * 백엔드 없이는 아무것도 못 하므로 오프라인 셸이 줄 게 없다. 반면 서비스
 * 워커는 한번 배포하면 기기에 남아 회수가 어렵다.
 */
import { describe, expect, it } from 'vitest'

// Vite 의 ?raw 로 읽는다. node:fs + import.meta.url 은 jsdom 환경에서
// file: 스킴이 아니라 실패하고, process.cwd() 는 브라우저 전역만 허용하는
// 린트 설정에 걸린다. ?raw 는 둘 다 피하면서 경로가 실제로 유효한지도 검증한다.
import manifestRaw from '../public/manifest.webmanifest?raw'

const manifest = JSON.parse(manifestRaw)

const DISPLAY_OK = ['standalone', 'fullscreen', 'minimal-ui', 'window-controls-overlay', 'unframed', 'tabbed']
const MIME_OK    = ['image/png', 'image/svg+xml', 'image/webp']

describe('매니페스트 — 설치 판정', () => {
    it('이름이 있다', () => {
        expect(manifest.name || manifest.short_name).toBeTruthy()
    })

    it('start_url 을 명시한다', () => {
        // 추론된 기본값으로는 엄격 판정을 통과하지 못한다.
        expect(manifest.start_url).toBe('/')
    })

    it('start_url 에 쿼리가 없다', () => {
        // ?url= 이 붙은 화면에서 설치하면 그 주소가 그대로 굳어서
        // 앱을 열 때마다 같은 곡을 다시 검색하게 된다.
        expect(manifest.start_url).not.toContain('?')
    })

    it('설치 가능한 display 값이다', () => {
        expect(DISPLAY_OK).toContain(manifest.display)
    })

    it('purpose=any 인 144px 이상 아이콘이 있다', () => {
        // maskable 전용 아이콘은 설치 판정에서 무시된다. any 가 따로 있어야 한다.
        const usable = manifest.icons.filter(i => {
            const purposes = (i.purpose ?? 'any').split(/\s+/)
            const largest = Math.max(...i.sizes.split('x').map(Number))
            return purposes.includes('any') && largest >= 144
        })
        expect(usable.length).toBeGreaterThan(0)
    })

    it('아이콘 형식이 전부 허용 목록 안이다', () => {
        for (const icon of manifest.icons) {
            expect(MIME_OK).toContain(icon.type)
        }
    })

    it('maskable 아이콘도 함께 제공한다', () => {
        // 없으면 안드로이드 런처가 아이콘을 흰 사각형 안에 넣어 축소한다.
        const maskable = manifest.icons.filter(i => (i.purpose ?? '').split(/\s+/).includes('maskable'))
        expect(maskable.length).toBeGreaterThan(0)
    })
})

describe('매니페스트 — 공유 타깃', () => {
    const st = manifest.share_target

    it('선언되어 있다', () => {
        expect(st).toBeTruthy()
    })

    it('GET 이다', () => {
        // POST 는 요청 본문을 읽을 서버나 서비스 워커가 필요한데 여기는
        // GitHub Pages 정적 호스팅이라 원리적으로 불가능하다.
        expect((st.method ?? 'GET').toUpperCase()).toBe('GET')
    })

    it('action 이 루트이고 scope 안이다', () => {
        // "/share" 같은 경로를 쓰면 정적 호스팅에서 404 가 나고 React 가
        // 부팅조차 못 한다 — App.jsx 의 /gets/ 주석에 이미 적힌 함정이다.
        expect(st.action).toBe('/')
        expect(st.action.startsWith(manifest.scope)).toBe(true)
    })

    it('action 에 쿼리스트링을 넣지 않는다', () => {
        // 명세상 GET 이면 action 의 쿼리는 공유 데이터로 **통째로 덮어써진다.**
        // "/?share=1" 같은 표식은 도착하지 않는다.
        expect(st.action).not.toContain('?')
    })

    it('title·text·url 세 칸을 모두 받는다', () => {
        // 안드로이드에는 URL 전용 인텐트 칸이 없어서 링크가 text 로,
        // 대개 제목과 섞여서 온다. 세 칸을 다 받아야 놓치지 않는다.
        expect(Object.keys(st.params).sort()).toEqual(['text', 'title', 'url'])
    })

    it('params.url 이 기존 처리기와 같은 이름이다', () => {
        // ?url= 은 붙여넣기 경로에서 이미 쓰고 있다. 이름을 맞추면 재사용된다.
        expect(st.params.url).toBe('url')
    })
})
