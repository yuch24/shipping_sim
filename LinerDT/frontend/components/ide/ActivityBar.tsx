'use client'

import { ActivityBarItem } from './types'

interface ActivityBarProps {
  items: ActivityBarItem[]
  activeId: string | null
  onSelect: (id: string | null) => void
}

export default function ActivityBar({ items, activeId, onSelect }: ActivityBarProps) {
  return (
    <div className="flex flex-col items-center gap-1 py-2 px-1 border-r border-white/10 bg-[#0d1e30] w-10 shrink-0">
      {items.map((item) => {
        const isActive = activeId === item.id
        return (
          <button
            key={item.id}
            onClick={() => onSelect(isActive ? null : item.id)}
            className={`p-1.5 rounded-lg transition-all relative ${
              isActive
                ? 'bg-marine-500/20 text-marine-400'
                : 'text-gray-500 hover:text-gray-300 hover:bg-white/5'
            }`}
            title={item.label}
          >
            {isActive && (
              <span className="absolute left-[-5px] top-1/2 -translate-y-1/2 w-0.5 h-4 rounded-full bg-marine-400" />
            )}
            <div className="w-4 h-4 flex items-center justify-center">
              {item.icon}
            </div>
          </button>
        )
      })}
    </div>
  )
}
