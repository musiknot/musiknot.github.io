import { useState } from 'react'
import { Music, ArrowUpRight, Share2 } from 'lucide-react'
import { PlatformGrid } from '../components/PlatformGrid'
import { API_BASE_URL } from '../constants/api'

export function ResultView({ song, onBack, t }) {
    const [shareState, setShareState] = useState(null)   // null | 'copied' | 'failed'

    // 공유 URL 은 백엔드를 가리킨다. 프론트는 GitHub Pages(정적)라 곡마다 다른
    // 미리보기 메타 태그를 줄 수 없기 때문이다. 백엔드의 /s/<id> 가 메타 태그를
    // 내려주고 사람은 프론트로 넘긴다.
    const shareUrl = song?.shareId
        ? `${API_BASE_URL}/s/${encodeURIComponent(song.shareId)}`
        : null

    const handleShare = async () => {
        if (!shareUrl) return
        const payload = { title: song.title, text: `${song.title} - ${song.artist}`, url: shareUrl }

        // 모바일이 주 사용처라 네이티브 공유 시트를 먼저 시도한다.
        if (navigator.share) {
            try {
                await navigator.share(payload)
                return
            } catch (e) {
                // 사용자가 시트를 닫은 것은 실패가 아니다 — 조용히 끝낸다.
                if (e?.name === 'AbortError') return
                // 그 외에는 클립보드로 폴백
            }
        }
        try {
            await navigator.clipboard.writeText(shareUrl)
            setShareState('copied')
        } catch {
            setShareState('failed')
        }
        setTimeout(() => setShareState(null), 2000)
    }

    if (!song) return null

    const hasMV = !!song.platforms?.youtube

    return (
        <main className="relative z-10 flex flex-col items-center px-4 pt-6 pb-20 w-full max-w-lg mx-auto space-y-4">

            {/* 뒤로가기 */}
            <button
                onClick={onBack}
                className="self-start mb-2 px-3 py-1 text-sm font-bold text-gray-500 hover:text-blue-500 transition-colors flex items-center"
            >
                ← {t('back')}
            </button>

            {/* 미디어: MV 있으면 YouTube embed, 없으면 앨범아트 */}
            {hasMV ? (
                <div className="w-full aspect-video rounded-2xl overflow-hidden shadow-2xl ring-1 ring-black/5 bg-black">
                    <iframe
                        className="w-full h-full"
                        src={`https://www.youtube.com/embed/${song.platforms.youtube}`}
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
                {song.isrc && (
                    <p className="text-xs text-gray-400 dark:text-zinc-500 mt-2">
                        ISRC: {song.isrc}
                    </p>
                )}
            </div>

            {/* 공유 + 더 알아보기 */}
            <div className="w-full flex flex-col items-center space-y-3 py-3">
                {shareUrl && (
                    <button
                        onClick={handleShare}
                        className="flex items-center justify-center px-6 py-3 bg-blue-600 text-white font-bold text-sm rounded-full shadow-lg hover:scale-105 active:scale-95 transition-all"
                    >
                        <Share2 className="w-4 h-4 mr-2" />
                        {shareState === 'copied' ? t('shareCopied')
                            : shareState === 'failed' ? t('shareFailed')
                            : t('share')}
                    </button>
                )}
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
            <PlatformGrid platformIds={song.platforms} />
        </main>
    )
}