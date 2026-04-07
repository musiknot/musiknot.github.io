import { useState } from 'react'
import { validateUrl } from '../utils/urlValidator'

const API_URL = 'http://localhost:8000'

const mockResponse = {
    title:    "Blinding Lights",
    artist:   "The Weeknd",
    album:    "After Hours",
    albumArt: "https://is1-ssl.mzstatic.com/image/thumb/Music125/v4/a6/6e/bf/a66ebf79-5008-8948-b352-a790fc87446b/19UM1IM04638.rgb.jpg/600x600bb.jpg",
    isrc:     "CAUM72000073",
    platforms: {
        spotify:      "0VjIjW4GlUZAMYd2vXMi3b",
        appleMusic:   "1499378615",
        youtube:      "4NRXx6U8ABQ",
        youtubeMusic: "J7p4bzqLvCw",
        melon:        "32219271",
        bugs:         "5812157",
        flo:          "438092629",
        amazon:       "B086Q41M9C"
    }
}

export function useParse() {
    const [result,  setResult]  = useState(null)
    const [loading, setLoading] = useState(false)
    const [error,   setError]   = useState(null)

    const parse = async (input) => {
        setLoading(true)
        setResult(null)
        setError(null)

        try {
            // 1차 방어: URL 검증
            if (!validateUrl(input)) {
                throw new Error('지원하지 않는 링크입니다.')
            }

            // 백엔드 완성 후 아래 주석 해제
            /*
            const res = await fetch(`${API_URL}/parse`, {
                method:  'POST',
                headers: { 'Content-Type': 'application/json' },
                body:    JSON.stringify({ url: input })
            })
            if (!res.ok) throw new Error('서버 오류')
            setResult(await res.json())
            */

            // Mock 딜레이
            await new Promise(r => setTimeout(r, 800))
            setResult(mockResponse)

        } catch (e) {
            setError(e.message)
        } finally {
            setLoading(false)
        }
    }

    const reset = () => {
        setResult(null)
        setError(null)
    }

    return { result, loading, error, parse, reset }
}