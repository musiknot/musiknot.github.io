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