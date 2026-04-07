import { useState, useEffect } from 'react'
import { useTheme } from './hooks/useTheme'
import { useLanguage } from './hooks/useLanguage'
import { useParse } from './hooks/useParse'
import { Header } from './components/Header'
import { HomeView } from './pages/HomeView'
import { ResultView } from './pages/ResultView'

export default function App() {
    const { theme, setTheme, isDark }   = useTheme()
    const { lang, setLanguage, t }      = useLanguage()
    const { result, loading, error, parse, reset } = useParse()
    const [history, setHistory]         = useState([])

    // ?url= 파라미터로 자동 검색
    useEffect(() => {
        const params = new URLSearchParams(window.location.search)
        const url = params.get('url')
        if (url) handleSearch(url)
    }, [])

    const handleSearch = (val) => {
        // 히스토리 추가 (중복 제거, 최대 10개)
        setHistory(prev => [val, ...prev.filter(h => h !== val)].slice(0, 10))
        parse(val)
        window.scrollTo(0, 0)
    }

    const handleBack = () => {
        reset()
    }

    return (
        <div className="min-h-screen relative overflow-x-hidden bg-gray-50 text-gray-900 dark:bg-zinc-950 dark:text-zinc-100 transition-colors duration-500">

            {/* 배경 그라데이션 */}
            {result && (
                <div
                    className="absolute inset-0 pointer-events-none transition-opacity duration-1000"
                    style={{
                        background: `radial-gradient(circle at 50% 0%, rgba(138, 43, 226, 0.4) 0%, transparent 60%)`
                    }}
                />
            )}

            {/* 헤더 */}
            <Header
                theme={theme}
                setTheme={setTheme}
                isDark={isDark}
                lang={lang}
                setLanguage={setLanguage}
                t={t}
                onHome={handleBack}
            />

            {/* 로딩 */}
            {loading && (
                <div className="flex items-center justify-center pt-32">
                    <div className="flex flex-col items-center space-y-4">
                        <div className="w-10 h-10 border-4 border-blue-500 border-t-transparent rounded-full animate-spin" />
                        <p className="text-sm text-gray-500 dark:text-zinc-400">
                            검색 중...
                        </p>
                    </div>
                </div>
            )}

            {/* 에러 */}
            {!loading && error && (
                <div className="flex items-center justify-center pt-32">
                    <div className="text-center space-y-4">
                        <p className="text-red-500 font-bold">{error}</p>
                        <button
                            onClick={handleBack}
                            className="px-4 py-2 text-sm font-bold text-blue-500 hover:underline"
                        >
                            ← {t('back')}
                        </button>
                    </div>
                </div>
            )}

            {/* 뷰 전환 */}
            {!loading && !error && (
                result ? (
                    <ResultView
                        song={result}
                        onBack={handleBack}
                        t={t}
                    />
                ) : (
                    <HomeView
                        onSearch={handleSearch}
                        history={history}
                        onHistoryClick={handleSearch}
                        onClearHistory={() => setHistory([])}
                        t={t}
                    />
                )
            )}
        </div>
    )
}