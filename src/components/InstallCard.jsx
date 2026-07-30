import { Download, Share, Check } from 'lucide-react'

import { useInstall } from '../hooks/useInstall'

/**
 * 홈 화면의 안내 카드.
 *
 * 원래 기획에는 OS 별로 세 갈래가 있었는데(안드로이드 설치 / iOS 단축어 /
 * 데스크톱 안내) React 로 옮기는 과정에서 앞의 둘과 OS 판정이 통째로 빠지고
 * **데스크톱용 문구만 조건 없이** 남았다. 그래서 모바일에서도
 * "모바일로 접속하세요" 라고 말하고 있었다. 그걸 되살린 것이다.
 *
 * 이 카드가 파는 것은 **링크를 앱 안으로 들여오는 경로**다. 지금은 사용자가
 * 음악앱 → 복사 → 브라우저 → 붙여넣기를 손으로 해야 한다. 설치하면 음악 앱의
 * 공유 메뉴에 Musiknot 이 떠서 그 과정이 없어진다.
 *
 * 분기는 UA 가 아니라 **기능**으로 정한다. 안드로이드 크롬이라고 항상 설치할
 * 수 있는 게 아니고(이미 설치했거나 조건을 못 채웠거나), 데스크톱 크롬에서도
 * 설치는 된다. UA 는 iOS 안내 문구를 고를 때만 쓴다 — 사파리에는 설치를
 * 알려주는 신호가 아예 없기 때문이다.
 */
export function InstallCard({ t }) {
    const { os, canInstall, installed, install } = useInstall()

    // 이미 설치해서 앱으로 실행 중이면 설치 얘기를 꺼낼 이유가 없다.
    // 대신 공유 메뉴를 써 보라고 알려준다 — 설치의 목적이 그것이었으므로.
    if (installed) {
        return (
            <Card>
                <div className="flex items-center justify-center text-sm font-bold text-gray-700 dark:text-zinc-200">
                    <Check className="w-4 h-4 mr-2 text-green-500 shrink-0" />
                    <span>{t('installedNote')}</span>
                </div>
            </Card>
        )
    }

    // 설치 가능하면 버튼을 준다. 브라우저가 직접 알려준 신호라 가장 믿을 만하다.
    if (canInstall) {
        return (
            <Card>
                <p className="text-sm font-bold text-center">{t('installTitle')}</p>
                <p className="mt-1.5 text-xs text-gray-500 dark:text-zinc-400 text-center leading-relaxed">
                    {t('installBody')}
                </p>
                <button
                    onClick={install}
                    className="mt-4 w-full flex items-center justify-center h-12 rounded-2xl
                        bg-blue-600 text-white font-bold text-sm shadow-lg
                        hover:scale-[1.02] active:scale-95 transition-all"
                >
                    <Download className="w-4 h-4 mr-2" />
                    {t('installAction')}
                </button>
            </Card>
        )
    }

    // iOS 사파리는 beforeinstallprompt 를 안 준다. 설치 가능 여부를 알 방법이
    // 없으므로 UA 로 판단하고, 버튼 대신 손으로 하는 방법을 알려준다.
    //
    // 여기에 "공유 시트에 Musiknot 이 뜬다" 고 쓰면 안 된다. iOS 는 Web Share
    // Target 을 지원하지 않아서 홈 화면에 추가해도 공유 메뉴에는 나타나지 않는다.
    // 문구가 약속하는 것은 딱 '홈 화면에서 바로 열기' 까지다.
    if (os === 'ios') {
        return (
            <Card>
                <p className="text-sm font-bold text-center">{t('iosTitle')}</p>
                <p className="mt-1.5 text-xs text-gray-500 dark:text-zinc-400 text-center leading-relaxed">
                    <Share className="w-3.5 h-3.5 inline-block mr-1 -mt-0.5" />
                    {t('iosBody')}
                </p>
            </Card>
        )
    }

    // 그 밖 — 데스크톱이거나, 설치를 이미 마쳤거나, 브라우저가 지원하지 않는다.
    return (
        <Card>
            <p className="text-xs text-gray-700 dark:text-zinc-200 text-center font-bold leading-snug">
                {t('mobileNotice')}
            </p>
        </Card>
    )
}

function Card({ children }) {
    return (
        <div className="bg-white/80 dark:bg-zinc-900/80 border border-gray-200 dark:border-zinc-800
            p-5 rounded-2xl backdrop-blur-sm w-full max-w-md shadow-sm">
            {children}
        </div>
    )
}
