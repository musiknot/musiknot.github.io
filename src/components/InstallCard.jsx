import { Download, Share, Check, ExternalLink } from 'lucide-react'

import { useInstall } from '../hooks/useInstall'
import { IOS_SHORTCUT_URL } from '../constants/shortcuts'

/**
 * 홈 화면의 안내 카드.
 *
 * OS별 진입점은 세 갈래다. Android/Chromium은 설치한 PWA가 Web Share Target으로
 * 음악 링크를 받고, iOS는 이 기능을 지원하지 않아 검증된 Apple 단축어로 같은
 * 역할을 한다. 그 밖의 환경에는 모바일 안내만 남긴다.
 *
 * 이 카드가 파는 것은 **링크를 앱 안으로 들여오는 경로**다. 지금은 사용자가
 * 음악앱 → 복사 → 브라우저 → 붙여넣기를 손으로 해야 한다. 설치하면 음악 앱의
 * 공유 메뉴에 Musiknot 이 떠서 그 과정이 없어진다.
 *
 * 설치 버튼은 브라우저의 `beforeinstallprompt` 신호를 따른다. 다만 Android에서
 * 이 신호가 없다고 데스크톱 안내로 떨어지면 사용자가 설치 경로를 잃는다.
 * Android에는 항상 PWA 설치 카드를 보여 주고, 신호가 없을 때는 Chrome 메뉴의
 * 수동 설치 경로를 안내한다.
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

    // 일부 Android 브라우저는 설치 조건을 아직 만족하지 않았거나 자체 UI를
    // 우선해 beforeinstallprompt를 내보내지 않는다. 이때도 사용자가 Chrome
    // 메뉴에서 PWA를 설치할 수 있으므로, 데스크톱용 일반 안내 대신 설치 경로를
    // 명시한다. 실제 프롬프트가 없으므로 눌러도 아무 일 없는 버튼은 만들지 않는다.
    if (os === 'android') {
        return (
            <Card>
                <p className="text-sm font-bold text-center">{t('androidInstallTitle')}</p>
                <p className="mt-1.5 text-xs text-gray-500 dark:text-zinc-400 text-center leading-relaxed">
                    {t('androidInstallBody')}
                </p>
            </Card>
        )
    }

    // iOS는 Web Share Target을 지원하지 않는다. 홈 화면에 앱을 추가해도 음악
    // 앱의 공유 메뉴에는 나타나지 않으므로, 설치 방법을 안내하는 대신 단축어
    // 설치 링크를 직접 제공한다.
    if (os === 'ios') {
        return (
            <Card>
                <p className="text-sm font-bold text-center">{t('iosShortcutTitle')}</p>
                <p className="mt-1.5 text-xs text-gray-500 dark:text-zinc-400 text-center leading-relaxed">
                    <Share className="w-3.5 h-3.5 inline-block mr-1 -mt-0.5" />
                    {t('iosShortcutBody')}
                </p>
                <a
                    href={IOS_SHORTCUT_URL}
                    target="_blank"
                    rel="noreferrer"
                    className="mt-4 w-full flex items-center justify-center h-12 rounded-2xl
                        bg-blue-600 text-white font-bold text-sm shadow-lg
                        hover:scale-[1.02] active:scale-95 transition-all"
                >
                    <Download className="w-4 h-4 mr-2" />
                    {t('iosShortcutAction')}
                    <ExternalLink className="w-3.5 h-3.5 ml-1.5 opacity-80" />
                </a>
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
