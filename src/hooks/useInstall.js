import { useCallback, useEffect, useState } from 'react'

import {
    detectOs,
    getInstallPrompt,
    isStandalone,
    showInstallPrompt,
    subscribeInstallPrompt,
} from '../utils/installPrompt'

/**
 * 홈 화면 안내 카드가 무엇을 보여줄지 결정하는 데 필요한 것들.
 *
 * OS 판정과 "설치 가능한가" 를 **따로** 들고 있는 게 핵심이다. 안드로이드
 * 크롬이라고 항상 설치할 수 있는 게 아니고(이미 설치했거나, 조건을 못 채웠거나),
 * 반대로 데스크톱 크롬에서도 설치는 된다. UA 로 기능을 단정하면 둘 다 틀린다.
 */
export function useInstall() {
    const [canInstall, setCanInstall] = useState(() => !!getInstallPrompt())

    useEffect(() => subscribeInstallPrompt(() => {
        setCanInstall(!!getInstallPrompt())
    }), [])

    // useCallback 이 필수다. 이 값들이 렌더마다 새로 만들어지면 이걸 의존성으로
    // 쓰는 쪽에서 effect 가 매번 다시 돈다 — 예전에 그렇게 무한 루프를 만든 적이 있다.
    const install = useCallback(() => showInstallPrompt(), [])

    return {
        os: detectOs(),
        canInstall,
        installed: isStandalone(),
        install,
    }
}
