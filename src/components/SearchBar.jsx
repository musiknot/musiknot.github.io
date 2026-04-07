import { useState } from 'react'
import { Search, Clipboard } from 'lucide-react'

export function SearchBar({ onSearch, t }) {
    const [value, setValue] = useState('')

    const handleSubmit = (e) => {
        e.preventDefault()
        if (value.trim()) onSearch(value.trim())
    }

    const paste = async () => {
        const text = await navigator.clipboard.readText()
        setValue(text)
    }

    return (
        <form onSubmit={handleSubmit} className="relative group">
            <button
                type="button"
                onClick={paste}
                className="absolute inset-y-0 left-3 my-auto h-12 w-12 flex items-center justify-center text-gray-400 hover:text-blue-500 hover:bg-gray-100 dark:hover:bg-zinc-800 rounded-xl transition-colors z-10"
            >
                <Clipboard className="h-6 w-6" />
            </button>

            <input
                type="text"
                value={value}
                onChange={(e) => setValue(e.target.value)}
                placeholder={t('placeholder')}
                className="block w-full pl-16 pr-16 py-5 bg-white dark:bg-zinc-900 border-2 border-gray-200 dark:border-zinc-800 rounded-3xl text-lg placeholder-gray-400 dark:text-zinc-100 focus:outline-none focus:border-blue-500 focus:ring-4 focus:ring-blue-500/10 transition-all shadow-sm group-hover:border-gray-300 dark:group-hover:border-zinc-700"
            />

            <button
                type="submit"
                className="absolute inset-y-0 right-3 my-auto h-12 w-12 flex items-center justify-center text-white bg-blue-500 hover:bg-blue-600 rounded-xl transition-colors shadow-md z-10"
            >
                <Search className="h-6 w-6" />
            </button>
        </form>
    )
}