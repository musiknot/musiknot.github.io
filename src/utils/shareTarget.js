import { validateUrl } from './urlValidator'

/**
 * 공유 시트로 들어온 데이터에서 음원 링크를 찾아낸다.
 *
 * Web Share Target 은 `title` / `text` / `url` 세 칸을 주는데, **어느 칸에
 * 링크가 담기는지는 보내는 앱 마음이다.** 명세가 강제하지 않는다.
 * 실제로 이런 것들을 봐야 한다:
 *
 *     url  = "https://www.melon.com/song/detail.htm?songId=1"     깔끔한 경우
 *     text = "밤편지 https://www.melon.com/song/..."               제목이 섞인 경우
 *     text = "[Melon] 아이유 - 밤편지\nhttps://kko.to/abc"          줄바꿈과 대괄호
 *     title= "밤편지", text = "https://..."                        분리된 경우
 *
 * 그래서 세 칸을 모두 뒤지고, **지원하는 도메인을 먼저** 고른다. 공유 문구에
 * 우리가 못 다루는 링크(앱 스토어 주소 같은 것)가 같이 붙어 오는 일이 있어서,
 * 먼저 나온 URL 을 무조건 집으면 엉뚱한 걸 잡는다.
 *
 * 지원 도메인이 하나도 없으면 **그래도 찾은 URL 중 첫 번째를 돌려준다.**
 * 조용히 아무 일도 안 일어나는 것보다, 앱이 평소처럼 "지원하지 않는 링크"
 * 라고 말해 주는 편이 낫기 때문이다.
 *
 * @returns {string | null} 검색에 넘길 URL. 아무 URL 도 못 찾으면 null.
 */
export function extractSharedUrl({ url, text, title } = {}) {
    const candidates = []

    // url 칸이 있으면 가장 믿을 만하다 — 보내는 쪽이 명시적으로 링크라고 표시한 것이다
    if (typeof url === 'string' && url.trim()) candidates.push(url.trim())

    // 나머지는 문장 속에서 긁어낸다
    for (const source of [text, title]) {
        candidates.push(...findUrls(source))
    }

    if (candidates.length === 0) return null

    // 지원 도메인 우선. 없으면 첫 번째를 주고 앱이 평소 에러를 내게 한다.
    return candidates.find(validateUrl) ?? candidates[0]
}

/** 문자열 안의 http(s) URL 을 전부 찾는다. */
function findUrls(source) {
    if (typeof source !== 'string' || !source) return []

    const matches = source.match(/https?:\/\/[^\s<>"']+/gi)
    if (!matches) return []

    return matches.map(trimTrailingPunctuation).filter(Boolean)
}

/**
 * URL 끝에 붙은 문장부호를 떼어낸다.
 *
 * "이 노래 좋더라 (https://www.melon.com/song/detail.htm?songId=1)" 처럼
 * 괄호나 마침표가 URL 에 딸려 들어온다. 다만 **닫는 괄호를 무조건 떼면 안 된다** —
 * 위키피디아식 주소처럼 URL 안에 정상적으로 괄호가 들어가는 경우가 있어서,
 * 여는 괄호의 개수가 맞으면 남겨 둔다.
 */
function trimTrailingPunctuation(raw) {
    let s = raw
    while (s.length > 0) {
        const last = s[s.length - 1]

        if (')]}'.includes(last)) {
            const open = last === ')' ? '(' : last === ']' ? '[' : '{'
            const balanced = countChar(s, open) >= countChar(s, last)
            if (balanced) break            // URL 의 일부다. 그대로 둔다.
            s = s.slice(0, -1)
            continue
        }

        if ('.,;:!?"\''.includes(last)) {
            s = s.slice(0, -1)
            continue
        }

        break
    }
    return s
}

function countChar(s, ch) {
    let n = 0
    for (const c of s) if (c === ch) n += 1
    return n
}
