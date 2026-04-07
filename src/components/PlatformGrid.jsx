import { PlatformCard } from './PlatformCard'
import { platforms } from '../constants/platforms'

export function PlatformGrid() {
    return (
        <div className="w-full space-y-4">
            {/* 글로벌 플랫폼 */}
            <div className="grid grid-cols-4 gap-3">
                {platforms.global.map(p => (
                    <PlatformCard
                        key={p.id}
                        platform={p}
                        onClick={() => console.log(`${p.id} 클릭`)}
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
                        onClick={() => console.log(`${p.id} 클릭`)}
                    />
                ))}
            </div>
        </div>
    )
}