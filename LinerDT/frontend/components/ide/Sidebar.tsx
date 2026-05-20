'use client'

import { ReactNode } from 'react'

interface SidebarProps {
  isOpen: boolean
  side: 'left' | 'right'
  width?: number
  children: ReactNode
  onClose?: () => void
  hideTitle?: boolean
}

export default function Sidebar({
  isOpen,
  side,
  width = 340,
  children,
  onClose,
  hideTitle = false,
}: SidebarProps) {
  if (!isOpen) return null

  const borderClass = side === 'left' ? 'border-r' : 'border-l'

  return (
    <div
      className={`${borderClass} border-white/10 bg-[#0d2137] flex flex-col shrink-0 overflow-hidden transition-all`}
      style={{ width }}
    >
      {/* 标题栏（可隐藏） */}
      {!hideTitle && (
        <div className="flex items-center justify-between px-3 py-2 border-b border-white/10 shrink-0">
          <div className="flex-1" />
          {onClose && (
            <button
              onClick={onClose}
              className="p-1 text-gray-500 hover:text-white hover:bg-white/10 rounded transition-colors"
            >
              <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>
          )}
        </div>
      )}

      {/* 内容 */}
      <div className="flex-1 overflow-hidden">
        {children}
      </div>
    </div>
  )
}
