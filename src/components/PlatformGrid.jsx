import { PlatformCard } from './PlatformCard'
import { platforms } from '../constants/platforms'

export function PlatformGrid({ platformIds }) {
    return (
        <div className="w-full space-y-4">
            {/* 글로벌 플랫폼 — 5개라 3+2 로 배치된다.
                한국 그리드와 열 수를 맞춰야 카드 크기가 같아지므로 3열 고정. */}
            <div className="grid grid-cols-3 gap-3">
                {platforms.global.map(p => (
                    <PlatformCard
                        key={p.id}
                        platform={p}
                        songId={platformIds?.[p.id]}
                        disabled={!platformIds?.[p.id]}
                    />
                ))}
            </div>

            <div className="px-2">
                <hr className="border-t border-gray-200 dark:border-zinc-800" />
            </div>

            {/* 한국 플랫폼 */}
            <div className="grid grid-cols-3 gap-3">
                {platforms.korea.map(p => (
                    <PlatformCard
                        key={p.id}
                        platform={p}
                        songId={platformIds?.[p.id]}
                        disabled={!platformIds?.[p.id]}
                    />
                ))}
            </div>
        </div>
    )
}