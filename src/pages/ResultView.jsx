import { Music, ArrowUpRight } from 'lucide-react'
import { PlatformGrid } from '../components/PlatformGrid'

export function ResultView({ song, onBack, t }) {
    if (!song) return null

    return (
        <main className="relative z-10 flex flex-col items-center px-4 pt-6 pb-20 w-full max-w-lg mx-auto space-y-4">

            {/* 뒤로가기 */}
            <button
                onClick={onBack}
                className="self-start mb-2 px-3 py-1 text-sm font-bold text-gray-500 hover:text-blue-500 transition-colors flex items-center"
            >
                ← {t('back')}
            </button>

            {/* 미디어 (MV or 앨범아트) */}
            {song.mvId ? (
                <div className="w-full aspect-video rounded-2xl overflow-hidden shadow-2xl ring-1 ring-black/5 bg-black">
                    <iframe
                        className="w-full h-full"
                        src={`https://www.youtube.com/embed/${song.mvId}`}
                        allowFullScreen
                    />
                </div>
            ) : (
                <div className="w-full max-w-[240px] aspect-square rounded-3xl overflow-hidden shadow-2xl mx-auto mt-4 mb-2">
                    <img
                        src={song.albumArt}
                        alt={song.title}
                        className="w-full h-full object-cover"
                    />
                </div>
            )}

            {/* 곡 정보 */}
            <div className="w-full bg-white/70 dark:bg-zinc-900/70 backdrop-blur-2xl border border-gray-200 dark:border-zinc-800 p-6 rounded-3xl shadow-sm text-center">
                <h2 className="text-2xl font-extrabold tracking-tight mb-1">
                    {song.title}
                </h2>
                <div className="flex items-center justify-center text-sm font-semibold text-gray-600 dark:text-zinc-300 space-x-2">
                    <span>{song.artist}</span>
                    <span>•</span>
                    <span className="truncate max-w-[150px]">{song.album}</span>
                </div>
                <p className="text-sm text-gray-500 dark:text-zinc-400 mt-5 leading-relaxed">
                    {song.description}
                </p>
            </div>

            {/* 더 알아보기 버튼 */}
            <div className="w-full flex flex-col items-center space-y-3 py-3">
                <button className="flex items-center justify-center px-6 py-3 bg-zinc-900 dark:bg-zinc-100 text-white dark:text-zinc-900 font-bold text-sm rounded-full shadow-lg hover:scale-105 active:scale-95 transition-all">
                    <Music className="w-4 h-4 mr-2" />
                    {t('learnMore')}
                    <ArrowUpRight className="w-4 h-4 ml-1.5 opacity-70" />
                </button>
                <span className="text-[10px] text-gray-400 dark:text-zinc-600 tracking-widest uppercase font-bold">
                    Powered by Last.fm
                </span>
            </div>

            {/* 플랫폼 링크 그리드 */}
            <PlatformGrid />
        </main>
    )
}