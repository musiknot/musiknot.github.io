import { useState } from 'react'
import { API_BASE_URL } from '../constants/api'

export function useMelonMatch() {
    const [result,  setResult]  = useState(null)
    const [loading, setLoading] = useState(false)
    const [error,   setError]   = useState(null)

    const match = async (title, artist) => {
        setLoading(true)
        setResult(null)
        setError(null)

        try {
            const res = await fetch(`${API_BASE_URL}/match`, {
                method:  'POST',
                headers: { 'Content-Type': 'application/json' },
                body:    JSON.stringify({ title, artist })
            })
            if (!res.ok) throw new Error('서버 오류')
            setResult(await res.json())
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

    return { result, loading, error, match, reset }
}