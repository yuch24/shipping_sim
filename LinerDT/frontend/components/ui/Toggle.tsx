'use client'

interface ToggleProps {
  checked: boolean
  onChange: (checked: boolean) => void
  disabled?: boolean
  size?: 'sm' | 'md' | 'lg'
  label?: string
  description?: string
}

const sizeClasses = {
  sm: {
    track: 'w-8 h-4',
    thumb: 'w-3 h-3',
    translate: 'translate-x-4',
  },
  md: {
    track: 'w-11 h-6',
    thumb: 'w-5 h-5',
    translate: 'translate-x-5',
  },
  lg: {
    track: 'w-14 h-7',
    thumb: 'w-6 h-6',
    translate: 'translate-x-7',
  },
}

export default function Toggle({
  checked,
  onChange,
  disabled = false,
  size = 'md',
  label,
  description,
}: ToggleProps) {
  const sizeConfig = sizeClasses[size]

  return (
    <label className={`flex items-start gap-3 ${disabled ? 'opacity-50 cursor-not-allowed' : 'cursor-pointer'}`}>
      <input
        type="checkbox"
        role="switch"
        checked={checked}
        disabled={disabled}
        onChange={(e) => onChange(e.target.checked)}
        className="sr-only"
      />
      <div
        className={`
          relative inline-flex items-center shrink-0 rounded-full
          transition-colors duration-200 ease-in-out
          focus-within:outline-none focus-within:ring-2 focus-within:ring-marine-500 focus-within:ring-offset-2 focus-within:ring-offset-gray-900
          ${sizeConfig.track}
          ${checked ? 'bg-marine-500' : 'bg-gray-600'}
          ${disabled ? '' : 'hover:bg-gray-500'}
        `.trim()}
      >
        <span
          className={`
            inline-block rounded-full bg-white shadow-lg
            transform transition-transform duration-200 ease-in-out
            ${sizeConfig.thumb}
            ${checked ? sizeConfig.translate : 'translate-x-0.5'}
          `.trim()}
        />
      </div>
      {(label || description) && (
        <div className="flex flex-col">
          {label && (
            <span className="text-sm font-medium text-white">{label}</span>
          )}
          {description && (
            <span className="text-xs text-gray-400">{description}</span>
          )}
        </div>
      )}
    </label>
  )
}