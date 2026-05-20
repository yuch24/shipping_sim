'use client'

import { ReactNode, useState } from 'react'

interface PanelProps {
  children: ReactNode
  title?: string
  icon?: ReactNode
  collapsible?: boolean
  defaultExpanded?: boolean
  className?: string
  headerActions?: ReactNode
}

export default function Panel({
  children,
  title,
  icon,
  collapsible = false,
  defaultExpanded = true,
  className = '',
  headerActions,
}: PanelProps) {
  const [isExpanded, setIsExpanded] = useState(defaultExpanded)

  return (
    <div className={`glass-panel ${className}`}>
      {title && (
        <div
          className={`
            flex items-center justify-between px-4 py-3 border-b border-white/10
            ${collapsible ? 'cursor-pointer select-none' : ''}
          `.trim()}
          onClick={collapsible ? () => setIsExpanded(!isExpanded) : undefined}
        >
          <div className="flex items-center gap-2">
            {icon && <span className="text-marine-400">{icon}</span>}
            <h3 className="panel-title">{title}</h3>
          </div>
          <div className="flex items-center gap-2">
            {headerActions}
            {collapsible && (
              <svg
                className={`
                  w-5 h-5 text-gray-400 transition-transform duration-200
                  ${isExpanded ? 'rotate-180' : ''}
                `.trim()}
                fill="none"
                viewBox="0 0 24 24"
                stroke="currentColor"
              >
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
              </svg>
            )}
          </div>
        </div>
      )}
      <div
        className={`
          overflow-hidden transition-all duration-300 ease-in-out
          ${isExpanded ? 'max-h-[2000px] opacity-100' : 'max-h-0 opacity-0'}
        `.trim()}
      >
        <div className="p-4">{children}</div>
      </div>
    </div>
  )
}