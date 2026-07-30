import { useState } from 'react'
import { Copy, Check, Trash2 } from 'lucide-react'

import { clearShareLog, readShareLog } from '../utils/shareLog'

/**
 * 공유 시트로 들어온 원본 파라미터를 보여주는 화면 (`?sharelog=1`).
 *
 * 앱마다 링크를 title/text/url 중 어디에 담는지는 문서로 알 수 없어서
 * 실기기에서 모은다. 폰에서 보고 그대로 옮겨 적을 수 있도록 **JSON 전체
 * 복사**를 제일 크게 뒀다 — 작은 글씨를 보고 손으로 옮기면 그 과정에서
 * 틀린다.
 *
 * 개발용 화면이라 번역하지 않는다. 링크로 직접 들어와야만 보인다.
 */
export function ShareLogView() {
    const [entries, setEntries] = useState(readShareLog)
    const [copied, setCopied] = useState(false)

    const json = JSON.stringify(entries, null, 2)

    const copy = async () => {
        try {
            await navigator.clipboard.writeText(json)
            setCopied(true)
            setTimeout(() => setCopied(false), 2000)
        } catch {
            // 클립보드가 막힌 환경에서는 직접 선택할 수 있게 띄운다
            window.prompt('복사하세요', json)
        }
    }

    return (
        <main className="relative z-10 max-w-2xl mx-auto px-4 py-10 space-y-6">
            <div>
                <h1 className="text-2xl font-extrabold">공유 수집 로그</h1>
                <p className="mt-2 text-sm text-gray-500 dark:text-zinc-400 leading-relaxed">
                    각 음악 앱에서 곡을 공유했을 때 <strong>실제로 무엇이 들어왔는지</strong> 기록한
                    것입니다. 이 기기 안에만 저장되며 어디로도 전송되지 않습니다.
                    최근 {entries.length}건.
                </p>
            </div>

            <div className="flex gap-2">
                <button
                    onClick={copy}
                    disabled={entries.length === 0}
                    className="flex items-center justify-center h-11 px-5 rounded-full
                        bg-blue-600 text-white font-bold text-sm shadow-lg
                        disabled:opacity-40 disabled:shadow-none
                        hover:scale-105 active:scale-95 transition-all"
                >
                    {copied
                        ? <><Check className="w-4 h-4 mr-2" />복사됨</>
                        : <><Copy className="w-4 h-4 mr-2" />전체 복사 (JSON)</>}
                </button>
                <button
                    onClick={() => { clearShareLog(); setEntries([]) }}
                    disabled={entries.length === 0}
                    className="flex items-center justify-center h-11 px-5 rounded-full
                        bg-white dark:bg-zinc-800 border border-gray-200 dark:border-zinc-700
                        text-gray-700 dark:text-zinc-200 font-bold text-sm
                        disabled:opacity-40 hover:scale-105 active:scale-95 transition-all"
                >
                    <Trash2 className="w-4 h-4 mr-2" />비우기
                </button>
            </div>

            {entries.length === 0 && (
                <div className="rounded-2xl border border-dashed border-gray-300 dark:border-zinc-700 p-6
                    text-sm text-gray-500 dark:text-zinc-400 leading-relaxed">
                    아직 기록이 없습니다.
                    <br />
                    홈 화면에 설치한 뒤, 음악 앱에서 곡을 <strong>공유 → Musiknot</strong> 으로
                    보내고 다시 이 주소로 들어오세요.
                </div>
            )}

            {entries.map((e, i) => (
                <div key={i} className="rounded-2xl border border-gray-200 dark:border-zinc-800
                    bg-white dark:bg-zinc-900 p-4 space-y-3">
                    <div className="text-[11px] font-bold uppercase tracking-widest text-gray-400">
                        {e.at}
                    </div>

                    {['url', 'text', 'title'].map(k => (
                        <div key={k} className="text-sm">
                            <span className="inline-block w-12 font-bold text-gray-400">{k}</span>
                            {/* 줄바꿈이 들어오는 경우가 있어 그대로 보여준다 */}
                            <span className="break-all whitespace-pre-wrap">
                                {e.raw?.[k] ?? <em className="text-gray-400">(없음)</em>}
                            </span>
                        </div>
                    ))}

                    <div className="text-sm pt-2 border-t border-gray-100 dark:border-zinc-800">
                        <span className="inline-block w-12 font-bold text-gray-400">고름</span>
                        <span className="break-all">
                            {e.picked ?? <em className="text-red-500">못 찾음</em>}
                        </span>
                    </div>

                    <div className="text-[11px] text-gray-400 break-all">{e.ua}</div>
                </div>
            ))}
        </main>
    )
}
