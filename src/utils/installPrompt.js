/**
 * 설치 프롬프트 포착 — **React 보다 먼저 실행되어야 한다.**
 *
 * 크롬은 페이지가 설치 조건을 만족하면 `beforeinstallprompt` 를 딱 한 번
 * 발화한다. 그런데 그 시점이 React 마운트보다 이를 수 있어서, 컴포넌트
 * 안에서 리스너를 걸면 **이미 지나간 이벤트를 영영 못 받는다.** 설치 버튼이
 * 어떤 기기에서는 뜨고 어떤 기기에서는 안 뜨는, 재현이 어려운 종류의 버그다.
 *
 * 그래서 이 모듈은 import 되는 즉시(= main.jsx 최상단) 리스너를 건다.
 * 이벤트를 붙잡아 모듈 변수에 넣어 두고, 나중에 훅이 그걸 꺼내 쓴다.
 */

let deferredPrompt = null
const listeners = new Set()

function notify() {
    for (const fn of listeners) fn()
}

if (typeof window !== 'undefined') {
    window.addEventListener('beforeinstallprompt', (e) => {
        // 기본 동작(크롬 하단의 작은 설치 배너)을 막고 우리 버튼으로 대체한다.
        // 우리가 안내 문구를 붙일 수 있고, 무엇보다 홈 화면 카드와 중복되지 않는다.
        e.preventDefault()
        deferredPrompt = e
        notify()
    })

    // 설치가 끝나면 버튼을 치운다. 이미 설치한 사람에게 "설치하세요" 를
    // 계속 보여주는 것만큼 성의 없어 보이는 것도 없다.
    window.addEventListener('appinstalled', () => {
        deferredPrompt = null
        notify()
    })
}

export function getInstallPrompt() {
    return deferredPrompt
}

export function subscribeInstallPrompt(fn) {
    listeners.add(fn)
    return () => listeners.delete(fn)
}

/**
 * 설치 프롬프트를 띄운다.
 *
 * @returns {Promise<'accepted'|'dismissed'|'unavailable'>}
 */
export async function showInstallPrompt() {
    const evt = deferredPrompt
    if (!evt) return 'unavailable'

    // prompt() 는 이벤트당 한 번만 쓸 수 있다. 결과와 무관하게 버린다.
    deferredPrompt = null
    notify()

    try {
        await evt.prompt()
        const { outcome } = await evt.userChoice
        return outcome === 'accepted' ? 'accepted' : 'dismissed'
    } catch {
        return 'dismissed'
    }
}

/** 설치된 앱으로 실행 중인가. */
export function isStandalone() {
    if (typeof window === 'undefined') return false
    const byMedia = window.matchMedia?.('(display-mode: standalone)')?.matches ?? false
    // iOS 사파리는 display-mode 를 안 주고 이 비표준 속성을 쓴다.
    const byIos = window.navigator?.standalone === true
    return byMedia || byIos
}

/**
 * 대략적인 OS 판정. 홈 화면 안내를 무엇으로 보여줄지 정하는 데만 쓴다.
 *
 * UA 스니핑은 원래 미덥지 않지만, 여기서 갈리는 것은 **안내 문구뿐**이고
 * 실제 기능은 각자 자기 조건으로 판단한다(설치 버튼은 beforeinstallprompt
 * 유무로, 공유 시트는 navigator.share 유무로). 그래서 틀려도 기능이 깨지지
 * 않는다.
 */
export function detectOs() {
    if (typeof navigator === 'undefined') return 'other'
    const ua = navigator.userAgent || ''

    if (/Android/i.test(ua)) return 'android'

    // 아이패드는 iPadOS 13 부터 UA 가 맥과 같아진다. 터치 지원 여부로 가른다.
    const isIpad = /Macintosh/.test(ua) && (navigator.maxTouchPoints ?? 0) > 1
    if (/iPhone|iPad|iPod/i.test(ua) || isIpad) return 'ios'

    return 'other'
}
