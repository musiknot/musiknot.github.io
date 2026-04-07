import { useState, useEffect } from 'react'

export function useTheme() {
    const [theme, setThemeState] = useState(
        localStorage.getItem('theme') || 'system'
    )

    const isDark = (t) =>
        t === 'dark' || (t === 'system' && window.matchMedia('(prefers-color-scheme: dark)').matches)

    useEffect(() => {
        const root = document.documentElement
        if (isDark(theme)) {
            root.classList.add('dark')
        } else {
            root.classList.remove('dark')
        }
        localStorage.setItem('theme', theme)
    }, [theme])

    // 시스템 테마 변경 감지
    useEffect(() => {
        if (theme !== 'system') return
        const mq = window.matchMedia('(prefers-color-scheme: dark)')
        const handler = (e) => {
            if (e.matches) document.documentElement.classList.add('dark')
            else           document.documentElement.classList.remove('dark')
        }
        mq.addEventListener('change', handler)
        return () => mq.removeEventListener('change', handler)
    }, [theme])

    return { theme, setTheme: setThemeState, isDark: isDark(theme) }
}