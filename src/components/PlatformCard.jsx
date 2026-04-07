export function PlatformCard({ platform, onClick, disabled }) {
    return (
        <div
            onClick={disabled ? null : onClick}
            className={`
                flex flex-col items-center justify-center w-full aspect-square
                rounded-2xl shadow-sm bg-white dark:bg-zinc-800
                border border-gray-100 dark:border-zinc-800
                transition-transform duration-200
                ${disabled
                    ? 'opacity-40 cursor-not-allowed'
                    : 'cursor-pointer hover:-translate-y-1'}
            `}
        >
            <div
                className="w-10 h-10 rounded-full flex items-center justify-center text-white font-bold text-lg mb-2"
                style={{ backgroundColor: platform.color }}
            >
                {platform.initial}
            </div>
            <span className="text-[10px] font-bold text-gray-800 dark:text-zinc-200 text-center whitespace-pre-line leading-tight">
                {platform.name}
            </span>
        </div>
    )
}