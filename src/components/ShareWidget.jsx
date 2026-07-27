import { useEffect, useState } from 'react'
import { Link2, QrCode as QrIcon, Check, Share2, X } from 'lucide-react'
import { QrCode } from './QrCode'

// navigator.share 는 Android/iOS 에는 있고 대부분의 데스크톱 브라우저에는 없다.
// 렌더 중에 한 번만 읽는다 — 세션 도중 바뀌지 않는 값이다.
const CAN_NATIVE_SHARE = typeof navigator !== 'undefined' && !!navigator.share

/**
 * 공유 위젯 — 세 가지를 사용자가 **명시적으로** 고른다.
 *
 *   1. 링크 복사하기
 *   2. 공유 창 표시 (Android/iOS 에서만, 아이콘만)
 *   3. QR 코드 표시
 *
 * 예전에는 버튼 하나가 "네이티브 공유를 시도하고 실패하면 클립보드"로 동작했는데,
 * 그러면 누르기 전에 무슨 일이 일어날지 알 수 없었다.
 */
export function ShareWidget({ url, title, artist, t }) {
    const [copied, setCopied] = useState(false)
    const [qrOpen, setQrOpen] = useState(false)

    // Esc 로 QR 을 닫는다. 열려 있을 때만 리스너를 건다.
    useEffect(() => {
        if (!qrOpen) return
        const onKey = (e) => { if (e.key === 'Escape') setQrOpen(false) }
        window.addEventListener('keydown', onKey)
        return () => window.removeEventListener('keydown', onKey)
    }, [qrOpen])

    if (!url) return null

    const handleCopy = async () => {
        try {
            await navigator.clipboard.writeText(url)
            setCopied(true)
            setTimeout(() => setCopied(false), 2000)
        } catch {
            // 클립보드가 막힌 환경(권한 거부, 비보안 컨텍스트)에서는
            // 사용자가 직접 복사할 수 있게 선택해 준다.
            window.prompt(t('shareFailed'), url)
        }
    }

    const handleNativeShare = async () => {
        try {
            await navigator.share({ title, text: `${title} - ${artist}`, url })
        } catch (e) {
            // 사용자가 공유 시트를 닫은 것은 실패가 아니다.
            if (e?.name !== 'AbortError') console.error(e)
        }
    }

    const iconBtn = "flex items-center justify-center w-11 h-11 rounded-full " +
        "bg-white dark:bg-zinc-800 border border-gray-200 dark:border-zinc-700 " +
        "text-gray-700 dark:text-zinc-200 shadow-sm " +
        "hover:scale-105 active:scale-95 transition-all"

    return (
        <>
            {/* 세 버튼은 한 덩어리로 움직인다. flex-nowrap + shrink-0 이 없으면
                바깥 flex-wrap 이 이 안까지 쪼개서 좁은 화면에서 3줄이 된다. */}
            <div className="flex flex-nowrap shrink-0 items-center gap-2">
                {/* 1. 링크 복사하기 — 유일하게 라벨을 단다 */}
                <button
                    onClick={handleCopy}
                    aria-label={t('shareCopyLink')}
                    className="flex items-center justify-center h-11 px-5 rounded-full
                        bg-blue-600 text-white font-bold text-sm shadow-lg
                        hover:scale-105 active:scale-95 transition-all"
                >
                    {copied
                        ? <><Check className="w-4 h-4 mr-2" />{t('shareCopied')}</>
                        : <><Link2 className="w-4 h-4 mr-2" />{t('shareCopyLink')}</>}
                </button>

                {/* 2. 공유 창 — 모바일에서만. 아이콘만 표시한다.
                       데스크톱에서는 아예 렌더하지 않는다 — 눌러도 아무 일도
                       일어나지 않는 버튼을 보여주는 것보다 없는 게 낫다. */}
                {CAN_NATIVE_SHARE && (
                    <button
                        onClick={handleNativeShare}
                        aria-label={t('shareOpenSheet')}
                        title={t('shareOpenSheet')}
                        className={iconBtn}
                    >
                        <Share2 className="w-5 h-5" />
                    </button>
                )}

                {/* 3. QR 코드 */}
                <button
                    onClick={() => setQrOpen(true)}
                    aria-label={t('shareShowQr')}
                    title={t('shareShowQr')}
                    className={iconBtn}
                >
                    <QrIcon className="w-5 h-5" />
                </button>
            </div>

            {qrOpen && (
                <div
                    role="dialog"
                    aria-modal="true"
                    aria-label={t('shareShowQr')}
                    onClick={() => setQrOpen(false)}
                    className="fixed inset-0 z-50 flex items-center justify-center
                        bg-black/60 backdrop-blur-sm p-6"
                >
                    <div
                        onClick={(e) => e.stopPropagation()}
                        className="relative bg-white rounded-3xl p-6 shadow-2xl
                            flex flex-col items-center max-w-xs w-full"
                    >
                        <button
                            onClick={() => setQrOpen(false)}
                            aria-label={t('close')}
                            className="absolute top-3 right-3 p-1.5 rounded-full
                                text-gray-400 hover:text-gray-700 hover:bg-gray-100 transition-colors"
                        >
                            <X className="w-5 h-5" />
                        </button>

                        {/* QR 은 항상 흰 배경 위 검은 모듈이다. 다크 모드에서
                            색을 반전시키면 스캔이 안 되므로 카드째로 흰색을 쓴다. */}
                        <QrCode value={url} size={220} />

                        <p className="mt-4 text-sm font-bold text-gray-900 text-center">
                            {title}
                        </p>
                        <p className="text-xs text-gray-500 text-center">{artist}</p>
                    </div>
                </div>
            )}
        </>
    )
}
