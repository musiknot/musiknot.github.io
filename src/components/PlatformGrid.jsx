import { PlatformCard } from './PlatformCard'
import { platforms } from '../constants/platforms'

export function PlatformGrid({ platformIds }) {
    console.log("platformIds:", platformIds)  // ← 추가
    return (
        <div className="w-full space-y-4">
            {/* 글로벌 플랫폼 */}
            <div className="grid grid-cols-4 gap-3">
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