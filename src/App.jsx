import { useState, useEffect, useCallback, useRef } from 'react'
import { useTheme } from './hooks/useTheme'
import { useLanguage } from './hooks/useLanguage'
import { useParse } from './hooks/useParse'
import { Header } from './components/Header'
import { HomeView } from './pages/HomeView'
import { ResultView } from './pages/ResultView'

export default function App() {
    const { theme, setTheme, isDark }   = useTheme()
    const { lang, setLanguage, t }      = useLanguage()
    const { result, loading, error, parse, reset } = useParse()
    const [history, setHistory]         = useState([])

    // URL 자동 검색이 두 번 이상 일어나지 않게 하는 빗장.
    //
    // 이게 있는 이유: 예전에 아래 effect 의 의존성을 채우다가 무한 루프를
    // 만든 적이 있다. useParse 의 parse 가 메모이제이션돼 있지 않아 렌더마다
    // 새 함수가 됐고, 그래서 effect 가 매 렌더마다 재실행되면서 백엔드가
    // 멜론을 초당 수천 번 때렸다. parse 는 이제 useCallback 으로 안정화됐지만,
    // 이 파일이 아니라 다른 훅의 사정 때문에 다시 깨질 수 있는 구조다.
    // 자동 검색은 본질적으로 '최초 1회' 동작이므로 그 사실을 코드로 못박는다.
    const didAutoSearch = useRef(false)

    // useEffect보다 먼저 선언해야 한다. 아래 effect가 이걸 참조하는데,
    // 선언이 뒤에 있으면 effect가 캡처한 값이 이후 변경을 반영하지 못한다.
    const handleSearch = useCallback((val) => {
        // 히스토리 추가 (중복 제거, 최대 10개)
        setHistory(prev => [val, ...prev.filter(h => h !== val)].slice(0, 10))
        parse(val)
        window.scrollTo(0, 0)
    }, [parse])

    // 최초 진입 시 URL로 자동 검색.
    //
    // react-hooks/set-state-in-effect 를 여기서만 끈다. 이 규칙은 effect 안에서
    // 동기적으로 setState 하면 렌더가 연쇄된다고 경고하는데, 여기서 하는 일은
    // "브라우저 URL이라는 외부 시스템을 읽어 그에 맞는 조회를 시작하는 것"이라
    // effect 의 정당한 용도다. 마운트 시 한 번만 실행되므로 연쇄 렌더 우려도
    // 해당하지 않는다. queueMicrotask 로 감싸면 규칙은 통과하지만 그건 린터를
    // 속이는 것일 뿐 코드가 나아지지 않는다.
    /* eslint-disable react-hooks/set-state-in-effect */
    useEffect(() => {
        if (didAutoSearch.current) return
        didAutoSearch.current = true

        // ?url= 쿼리스트링 — 정적 호스팅에서 확실히 동작하는 방식
        const params = new URLSearchParams(window.location.search)
        const urlParam = params.get('url')
        if (urlParam) {
            handleSearch(urlParam)
            return
        }

        // /gets/<base64> 경로
        // 주의: GitHub Pages는 정적이라 이 경로로 들어오면 404를 반환하고
        // React가 부팅조차 못 한다. public/404.html 우회를 넣지 않는 한
        // 이 분기는 로컬 dev에서만 동작한다.
        const path = window.location.pathname
        const getsPrefix = '/gets/'
        if (path.startsWith(getsPrefix)) {
            const encoded = path.slice(getsPrefix.length)
            if (encoded) {
                try {
                    handleSearch(atob(encoded))
                } catch {
                    console.error('Base64 디코딩 실패')
                }
            }
        }
    }, [handleSearch])
    /* eslint-enable react-hooks/set-state-in-effect */

    const handleBack = () => {
        reset()
    }

    return (
        <div className="min-h-screen relative overflow-x-hidden bg-gray-50 text-gray-900 dark:bg-zinc-950 dark:text-zinc-100 transition-colors duration-500">

            {/* 배경 그라데이션 */}
            {result && (
                <div
                    className="absolute inset-0 pointer-events-none transition-opacity duration-1000"
                    style={{
                        background: `radial-gradient(circle at 50% 0%, rgba(138, 43, 226, 0.4) 0%, transparent 60%)`
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

            {/* 로딩 */}
            {loading && (
                <div className="flex items-center justify-center pt-32">
                    <div className="flex flex-col items-center space-y-4">
                        <div className="w-10 h-10 border-4 border-blue-500 border-t-transparent rounded-full animate-spin" />
                        <p className="text-sm text-gray-500 dark:text-zinc-400">
                            검색 중...
                        </p>
                    </div>
                </div>
            )}

            {/* 에러 */}
            {!loading && error && (
                <div className="flex items-center justify-center pt-32">
                    <div className="text-center space-y-4">
                        <p className="text-red-500 font-bold">{error}</p>
                        <button
                            onClick={handleBack}
                            className="px-4 py-2 text-sm font-bold text-blue-500 hover:underline"
                        >
                            ← {t('back')}
                        </button>
                    </div>
                </div>
            )}

            {/* 뷰 전환 */}
            {!loading && !error && (
                result ? (
                    <ResultView
                        song={result}
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
                )
            )}
        </div>
    )
}