import { Clock, Trash2 } from 'lucide-react'
import { SearchBar } from '../components/SearchBar'

export function HomeView({ onSearch, history, onHistoryClick, onClearHistory, t }) {
    return (
        <main className="relative z-10 flex flex-col items-center px-4 pt-16 pb-12 max-w-3xl mx-auto space-y-12">

            {/* 타이틀 */}
            <div className="text-center space-y-4 w-full">
                <h1 className="text-3xl sm:text-5xl font-extrabold tracking-tight">
                    <span>{t('titleStart')}</span>
                    <span className="text-transparent bg-clip-text bg-gradient-to-r from-blue-500 to-purple-500">
                        {t('titleHighlight')}
                    </span>
                    <span>{t('titleEnd')}</span>
                </h1>
                <p className="text-gray-500 dark:text-zinc-400 text-sm sm:text-lg max-w-xl mx-auto leading-relaxed whitespace-pre-line">
                    {t('subtitle')}
                </p>
            </div>

            {/* 모바일 안내 */}
            <div className="bg-white/80 dark:bg-zinc-900/80 border border-gray-200 dark:border-zinc-800 p-5 rounded-2xl backdrop-blur-sm w-full max-w-md shadow-sm">
                <p className="text-xs text-gray-700 dark:text-zinc-200 text-center font-bold leading-snug">
                    {t('mobileNotice')}
                </p>
            </div>

            {/* 검색창 + 히스토리 */}
            <div className="w-full max-w-2xl space-y-8">
                <SearchBar onSearch={onSearch} t={t} />

                {/* 히스토리 */}
                <div className="space-y-4 px-2">
                    <div className="flex items-center justify-between text-[11px] font-bold text-gray-400 dark:text-zinc-500 uppercase tracking-widest">
                        <div className="flex items-center">
                            <Clock className="w-3.5 h-3.5 mr-2" />
                            {t('searchHistory')}
                        </div>
                        <button
                            onClick={onClearHistory}
                            className="hover:text-red-500 transition-colors flex items-center"
                        >
                            <Trash2 className="w-3.5 h-3.5 mr-1.5" />
                            {t('clearHistory')}
                        </button>
                    </div>

                    <div className="flex flex-wrap gap-2.5">
                        {history.map((item, idx) => (
                            <button
                                key={idx}
                                onClick={() => onHistoryClick(item)}
                                className="px-5 py-2.5 bg-white dark:bg-zinc-800 border border-gray-200 dark:border-zinc-700 rounded-full text-sm font-bold text-gray-800 dark:text-zinc-100 hover:border-blue-500 hover:text-blue-500 dark:hover:text-blue-400 transition-all shadow-sm active:scale-95"
                            >
                                {item}
                            </button>
                        ))}
                    </div>
                </div>
            </div>
        </main>
    )
}