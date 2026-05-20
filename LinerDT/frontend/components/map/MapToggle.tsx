'use client'

interface MapToggleProps {
  currentType: '3d' | '2d'
  onTypeChange: (type: '3d' | '2d') => void
}

export default function MapToggle({ currentType, onTypeChange }: MapToggleProps) {
  return (
    <div className="absolute top-20 left-4 glass-panel p-1 flex items-center gap-1 z-30">
      <button
        onClick={() => onTypeChange('3d')}
        className={`
          flex items-center gap-2 px-3 py-1.5 rounded-md text-sm font-medium transition-all duration-200
          ${currentType === '3d'
            ? 'bg-marine-500/20 text-marine-400'
            : 'text-gray-400 hover:text-white hover:bg-white/5'
          }
        `.trim()}
      >
        <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 12a9 9 0 01-9 9m9-9a9 9 0 00-9-9m9 9H3m9 9a9 9 0 01-9-9m9 9c1.657 0 3-4.03 3-9s-1.343-9-3-9m0 18c-1.657 0-3-4.03-3-9s1.343-9 3-9m-9 9a9 9 0 019-9" />
        </svg>
        3D
      </button>
      <button
        onClick={() => onTypeChange('2d')}
        className={`
          flex items-center gap-2 px-3 py-1.5 rounded-md text-sm font-medium transition-all duration-200
          ${currentType === '2d'
            ? 'bg-marine-500/20 text-marine-400'
            : 'text-gray-400 hover:text-white hover:bg-white/5'
          }
        `.trim()}
      >
        <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 20l-5.447-2.724A1 1 0 013 16.382V5.618a1 1 0 011.447-.894L9 7m0 13l6-3m-6 3V7m6 10l4.553 2.276A1 1 0 0021 18.382V7.618a1 1 0 00-.553-.894L15 4m0 13V4m0 0L9 7" />
        </svg>
        2D
      </button>
    </div>
  )
}