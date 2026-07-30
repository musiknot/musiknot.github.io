/**
 * 공유 시트로 들어온 **원본 파라미터**를 기기에 기록한다.
 *
 * 왜 필요한가. Web Share Target 명세는 title/text/url 세 칸을 정의하지만
 * **보내는 앱이 링크를 어디 담을지는 강제하지 않는다.** 멜론이 url 에 넣는지
 * text 에 넣는지, 제목을 같이 붙이는지, 단축 링크로 바꾸는지 — 문서로는
 * 알 수 없고 앱마다 다르다. 그래서 추측 대신 실기기에서 직접 모은다.
 *
 * 사용법: 폰에 설치한 뒤 각 앱에서 곡을 공유하고, `?sharelog=1` 로 들어와
 * 무엇이 들어왔는지 본다.
 *
 * 기록은 **이 기기 안에만** 남는다. 어디로도 보내지 않는다.
 */

const KEY = 'musiknot:sharelog'
const MAX = 20        // 링 버퍼. 오래된 것부터 버린다.

/**
 * 공유 진입 1건을 기록한다.
 *
 * 절대 예외를 던지면 안 된다 — 기록은 부수적인 일인데 이것 때문에 정작
 * 검색이 안 되면 본말이 전도된다. localStorage 는 사파리 시크릿 모드나
 * 용량 초과에서 그냥 던진다.
 */
export function recordShare(params, picked) {
    try {
        const entry = {
            at: new Date().toISOString(),
            ua: navigator.userAgent,
            raw: params,
            picked: picked ?? null,
        }
        const log = readShareLog()
        log.unshift(entry)
        localStorage.setItem(KEY, JSON.stringify(log.slice(0, MAX)))
    } catch {
        // 기록 실패는 무시한다.
    }
}

export function readShareLog() {
    try {
        const parsed = JSON.parse(localStorage.getItem(KEY) || '[]')
        return Array.isArray(parsed) ? parsed : []
    } catch {
        return []
    }
}

export function clearShareLog() {
    try {
        localStorage.removeItem(KEY)
    } catch {
        // 무시
    }
}
