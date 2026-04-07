import { useState } from 'react'
import { validateUrl } from '../utils/urlValidator'

const API_URL = import.meta.env.DEV 
    ? 'http://localhost:8000'
    : 'https://musiknotgithubio-production.up.railway.app'

const mockDB = {
    // Blinding Lights - MV 있음
    "CAUM72000073": {
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
    },
    // 水平線のような僕らへ - MV 없음
    "TCJPR2275478": {
        title:    "水平線のような僕らへ",
        artist:   "Vivid Lila",
        album:    "Air of Celeste",
        albumArt: "https://is1-ssl.mzstatic.com/image/thumb/Music116/v4/3b/16/af/3b16af7e-14e4-7613-ef01-81c0bbd40838/859758152994_cover.jpg/600x600bb.jpg",
        isrc:     "TCJPR2275478",
        platforms: {
            spotify:      "764RaAqzJ4vjkkZDMZyiUi",
            appleMusic:   "1621423052",
            youtube:      null,
            youtubeMusic: "JWX2eik5gRM",
            melon:        null,
            bugs:         null,
            flo:          "453525028",
            amazon:       "B09Z1YKS9Z"
        }
    }
}

// URL에서 플랫폼 ID 추출 후 mockDB에서 ISRC로 조회
function getMockResponse(url) {
    for (const [isrc, data] of Object.entries(mockDB)) {
        for (const id of Object.values(data.platforms)) {
            if (id && url.includes(id)) return data
        }
    }
    return null
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
            if (!validateUrl(input)) {
                throw new Error('지원하지 않는 링크입니다.')
            }

            
            const res = await fetch(`${API_URL}/parse`, {
                method:  'POST',
                headers: { 'Content-Type': 'application/json' },
                body:    JSON.stringify({ url: input })
            })
            if (!res.ok) throw new Error('서버 오류')
            setResult(await res.json())
            
/*
            await new Promise(r => setTimeout(r, 800))
            const mock = getMockResponse(input)
            if (!mock) throw new Error('등록되지 않은 링크입니다. (Mock DB)')
            setResult(mock)
*/
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