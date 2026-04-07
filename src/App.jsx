import { useState } from 'react'
import { useTheme } from './hooks/useTheme'
import { useLanguage } from './hooks/useLanguage'
import { Header } from './components/Header'
import { HomeView } from './pages/HomeView'
import { ResultView } from './pages/ResultView'

const mockData = {
    'example_music': {
        title:       "Never Gonna Give You Up",
        artist:      "Rick Astley",
        album:       "Whenever You Need Somebody (1987)",
        description: "Rick Astley의 데뷔 싱글로, 전 세계적으로 히트한 곡입니다. 릭롤링 밈으로 유명합니다.",
        albumArt:    "https://images.unsplash.com/photo-1614613535308-eb5fbd3d2c17?auto=format&fit=crop&w=500&q=80",
        mvId:        "dQw4w9WgXcQ",
        color:       "138, 43, 226"
    },
    'example_music_2': {
        title:       "Example Music 2",
        artist:      "Second Artist",
        album:       "Midnight Vibes (2026)",
        description: "밤하늘의 별빛을 닮은 신디사이저 사운드가 돋보이는 곡입니다.",
        albumArt:    "https://images.unsplash.com/photo-1514525253161-7a46d19cd819?auto=format&fit=crop&w=500&q=80",
        mvId:        null,
        color:       "255, 99, 71"
    }
}

export default function App() {
    const { theme, setTheme, isDark }     = useTheme()
    const { lang, setLanguage, t }        = useLanguage()
    const [currentSong, setCurrentSong]   = useState(null)
    const [history, setHistory]           = useState(['example_music', 'example_music_2'])

    const handleSearch = (val) => {
        const data = mockData[val]
        if (!data) {
            alert('Mock Data Only: example_music / example_music_2')
            return
        }
        // 히스토리 추가 (중복 제거)
        setHistory(prev => [val, ...prev.filter(h => h !== val)].slice(0, 10))
        setCurrentSong(data)
        window.scrollTo(0, 0)
    }

    const handleBack = () => setCurrentSong(null)

    return (
        <div
            className="min-h-screen relative overflow-x-hidden bg-gray-50 text-gray-900 dark:bg-zinc-950 dark:text-zinc-100 transition-colors duration-500"
            onClick={() => {}}
        >
            {/* 배경 그라데이션 */}
            {currentSong && (
                <div
                    className="absolute inset-0 pointer-events-none transition-opacity duration-1000"
                    style={{
                        background: `radial-gradient(circle at 50% 0%, rgba(${currentSong.color}, 0.4) 0%, transparent 60%)`
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

            {/* 뷰 전환 */}
            {currentSong ? (
                <ResultView
                    song={currentSong}
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
            )}
        </div>
    )
}