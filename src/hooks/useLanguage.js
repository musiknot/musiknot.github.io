import { useState } from 'react'
import { translations } from '../constants/translations'

export function useLanguage() {
    const [lang, setLang] = useState(
        localStorage.getItem('lang') || 'ko'
    )

    const t = (key) => translations[lang][key] || key

    const setLanguage = (l) => {
        setLang(l)
        localStorage.setItem('lang', l)
    }

    return { lang, setLanguage, t }
}