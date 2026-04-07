const ALLOWED_DOMAINS = [
    'open.spotify.com',
    'music.apple.com',
    'music.youtube.com',
    'www.youtube.com',
    'youtu.be',
    'www.melon.com',
    'music.bugs.co.kr',
    'm.bugs.co.kr',
    'www.music-flo.com',
    'flomuz.io',
    'kko.to',
    'music.amazon.com',
]

export function validateUrl(input) {
    if (!input || typeof input !== 'string') return false

    // 길이 제한
    if (input.length > 500) return false

    // https:// 없으면 붙여서 파싱 시도
    let url
    try {
        url = new URL(input.startsWith('http') ? input : `https://${input}`)
    } catch {
        return false
    }

    // 허용된 도메인인지 확인
    const domain = url.hostname
    if (!ALLOWED_DOMAINS.some(d => domain === d || domain.endsWith(`.${d}`))) return false

    return true
}