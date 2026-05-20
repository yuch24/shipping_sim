'use client'

type BadgeVariant = 'success' | 'warning' | 'danger' | 'info' | 'default'
type BadgeSize = 'sm' | 'md'

interface BadgeProps {
  children: React.ReactNode
  variant?: BadgeVariant
  size?: BadgeSize
  dot?: boolean
  className?: string
}

const variantClasses: Record<BadgeVariant, string> = {
  success: 'badge-success',
  warning: 'badge-warning',
  danger: 'badge-danger',
  info: 'badge-info',
  default: 'bg-gray-500/20 text-gray-300 border border-gray-500/30',
}

const sizeClasses: Record<BadgeSize, string> = {
  sm: 'px-1.5 py-0.5 text-[10px]',
  md: 'px-2 py-0.5 text-xs',
}

const dotColors: Record<BadgeVariant, string> = {
  success: 'bg-green-400',
  warning: 'bg-yellow-400',
  danger: 'bg-red-400',
  info: 'bg-blue-400',
  default: 'bg-gray-400',
}

export default function Badge({
  children,
  variant = 'default',
  size = 'md',
  dot = false,
  className = '',
}: BadgeProps) {
  return (
    <span
      className={`
        badge ${variantClasses[variant]} ${sizeClasses[size]}
        inline-flex items-center gap-1.5
        ${className}
      `.trim()}
    >
      {dot && (
        <span
          className={`
            w-1.5 h-1.5 rounded-full ${dotColors[variant]}
            ${variant === 'success' ? 'animate-pulse' : ''}
          `.trim()}
        />
      )}
      {children}
    </span>
  )
}