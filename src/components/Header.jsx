import { useState } from 'react'
import { Menu, X, Sun, Moon, Monitor } from 'lucide-react'

export function Header({ theme, setTheme, isDark, lang, setLanguage, t, onHome }) {
    const [menuOpen,  setMenuOpen]  = useState(false)
    const [themeOpen, setThemeOpen] = useState(false)
    const [langOpen,  setLangOpen]  = useState(false)

    const closeAll = () => {
        setMenuOpen(false)
        setThemeOpen(false)
        setLangOpen(false)
    }

    return (
        <header className="relative flex items-center justify-between p-4 max-w-3xl mx-auto z-50">

            {/* 왼쪽: 메뉴 + 로고 */}
            <div className="flex items-center space-x-3">

                {/* 햄버거 메뉴 */}
                <div className="relative">
                    <button
                        onClick={(e) => { e.stopPropagation(); const o = !menuOpen; closeAll(); setMenuOpen(o) }}
                        className="p-2 -ml-2 rounded-full hover:bg-gray-200/50 dark:hover:bg-zinc-800/50 transition-all"
                    >
                        {menuOpen
                            ? <X     className="w-6 h-6" />
                            : <Menu  className="w-6 h-6" />
                        }
                    </button>
                    {menuOpen && (
                        <div className="absolute left-0 top-full mt-2 bg-white/95 dark:bg-zinc-900/95 backdrop-blur-xl border border-gray-200 dark:border-zinc-800 rounded-2xl shadow-xl p-2 z-50 w-48">
                            <button className="w-full text-left px-4 py-3 text-sm font-bold hover:bg-gray-100 dark:hover:bg-zinc-800 rounded-xl transition-colors">
                                {t('howToUse')}
                            </button>
                            <button className="w-full text-left px-4 py-3 text-sm font-bold hover:bg-gray-100 dark:hover:bg-zinc-800 rounded-xl text-red-500 transition-colors">
                                {t('contact')}
                            </button>
                        </div>
                    )}
                </div>

                {/* 로고 */}
                <button
                    onClick={onHome}
                    className="flex items-center font-bold text-xl tracking-tight hover:scale-105 transition-transform"
                >
                    <span className="text-blue-600 mr-1">🎵</span>
                    Musi<span className="text-blue-600 dark:text-blue-500">knot</span>
                </button>
            </div>

            {/* 오른쪽: 테마 + 언어 */}
            <div className="flex items-center space-x-2">

                {/* 테마 */}
                <div className="relative">
                    <button
                        onClick={(e) => { e.stopPropagation(); const o = !themeOpen; closeAll(); setThemeOpen(o) }}
                        className="p-2 rounded-full hover:bg-gray-200/50 dark:hover:bg-zinc-800/50 transition-colors"
                    >
                        {isDark ? <Moon className="w-5 h-5" /> : <Sun className="w-5 h-5" />}
                    </button>
                    {themeOpen && (
                        <div className="absolute right-0 top-full mt-2 bg-white/95 dark:bg-zinc-900/95 backdrop-blur-xl border border-gray-200 dark:border-zinc-800 rounded-2xl shadow-xl p-2 z-50 w-48">
                            <button onClick={() => { setTheme('system'); closeAll() }} className="flex items-center w-full px-4 py-2.5 text-sm font-bold hover:bg-gray-100 dark:hover:bg-zinc-800 rounded-xl transition-colors">
                                <Monitor className="w-4 h-4 mr-3" /> {t('themeSystem')}
                            </button>
                            <button onClick={() => { setTheme('light'); closeAll() }} className="flex items-center w-full px-4 py-2.5 text-sm font-bold hover:bg-gray-100 dark:hover:bg-zinc-800 rounded-xl transition-colors">
                                <Sun className="w-4 h-4 mr-3" /> {t('themeLight')}
                            </button>
                            <button onClick={() => { setTheme('dark'); closeAll() }} className="flex items-center w-full px-4 py-2.5 text-sm font-bold hover:bg-gray-100 dark:hover:bg-zinc-800 rounded-xl transition-colors">
                                <Moon className="w-4 h-4 mr-3" /> {t('themeDark')}
                            </button>
                        </div>
                    )}
                </div>

                {/* 언어 */}
                <div className="relative">
                    <button
                        onClick={(e) => { e.stopPropagation(); const o = !langOpen; closeAll(); setLangOpen(o) }}
                        className="p-2 rounded-full hover:bg-gray-200/50 dark:hover:bg-zinc-800/50 transition-colors text-xl"
                    >
                        {lang === 'ko' ? '🇰🇷' : '🇺🇸'}
                    </button>
                    {langOpen && (
                        <div className="absolute right-0 top-full mt-2 bg-white/95 dark:bg-zinc-900/95 backdrop-blur-xl border border-gray-200 dark:border-zinc-800 rounded-2xl shadow-xl p-2 z-50 w-32">
                            <button onClick={() => { setLanguage('ko'); closeAll() }} className="flex items-center w-full px-4 py-2.5 text-sm font-bold hover:bg-gray-100 dark:hover:bg-zinc-800 rounded-xl transition-colors">
                                <span className="mr-3">🇰🇷</span> 한국어
                            </button>
                            <button onClick={() => { setLanguage('en'); closeAll() }} className="flex items-center w-full px-4 py-2.5 text-sm font-bold hover:bg-gray-100 dark:hover:bg-zinc-800 rounded-xl transition-colors">
                                <span className="mr-3">🇺🇸</span> English
                            </button>
                        </div>
                    )}
                </div>
            </div>
        </header>
    )
}