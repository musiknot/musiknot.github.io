import { useState, useCallback } from 'react'
import { validateUrl } from '../utils/urlValidator'
import { API_BASE_URL } from '../constants/api'

export function useParse() {
    const [result,  setResult]  = useState(null)
    const [loading, setLoading] = useState(false)
    const [error,   setError]   = useState(null)

    // useCallback 이 필수다. 이게 없으면 렌더마다 새 함수가 되고, 이걸
    // 의존성으로 쓰는 쪽(App.jsx 의 handleSearch → useEffect)이 매 렌더마다
    // 다시 실행되어 무한 루프가 된다. 실제로 그렇게 만들었다가 백엔드가 멜론을
    // 초당 수천 번 때린 적이 있다. setState 함수들은 React 가 안정성을
    // 보장하므로 의존성 배열은 비워도 안전하다.
    const parse = useCallback(async (input) => {
        setLoading(true)
        setResult(null)
        setError(null)

        try {
            if (!validateUrl(input)) {
                throw new Error('지원하지 않는 링크입니다.')
            }

            const res = await fetch(`${API_BASE_URL}/parse`, {
                method:  'POST',
                headers: { 'Content-Type': 'application/json' },
                body:    JSON.stringify({ url: input })
            })
            if (!res.ok) throw new Error('서버 오류')
            setResult(await res.json())
        } catch (e) {
            setError(e.message)
        } finally {
            setLoading(false)
        }
    }, [])

    // 공유 ID(`melon:30314784`)로 조회. URL 이 아니므로 validateUrl 을 거치지
    // 않고, 형식 검증은 백엔드가 한다(플랫폼 화이트리스트 + 문자·길이 제한).
    const parseById = useCallback(async (id) => {
        setLoading(true)
        setResult(null)
        setError(null)

        try {
            const res = await fetch(`${API_BASE_URL}/parse`, {
                method:  'POST',
                headers: { 'Content-Type': 'application/json' },
                body:    JSON.stringify({ id })
            })
            if (!res.ok) throw new Error('서버 오류')
            setResult(await res.json())
        } catch (e) {
            setError(e.message)
        } finally {
            setLoading(false)
        }
    }, [])

    const reset = useCallback(() => {
        setResult(null)
        setError(null)
    }, [])

    return { result, loading, error, parse, parseById, reset }
}
