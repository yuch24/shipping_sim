'use client'

import Button from '../ui/Button'

interface EmptyStateProps {
  title: string
  description?: string
  icon?: React.ReactNode
  action?: {
    label: string
    onClick: () => void
  }
  className?: string
}

export default function EmptyState({
  title,
  description,
  icon,
  action,
  className = '',
}: EmptyStateProps) {
  return (
    <div className={`flex flex-col items-center justify-center text-center py-8 px-4 ${className}`}>
      {icon && (
        <div className="mb-4 p-4 rounded-full bg-marine-500/10 text-marine-400">
          {icon}
        </div>
      )}
      <h3 className="text-lg font-semibold text-white mb-2">{title}</h3>
      {description && (
        <p className="text-sm text-gray-400 mb-4 max-w-sm">{description}</p>
      )}
      {action && (
        <Button onClick={action.onClick} size="sm">
          {action.label}
        </Button>
      )}
    </div>
  )
}

interface SimNotStartedProps {
  onStart: () => void
  className?: string
}

export function SimNotStarted({ onStart, className = '' }: SimNotStartedProps) {
  return (
    <div className={`absolute inset-0 flex items-center justify-center bg-[#0a1929]/80 backdrop-blur-sm z-10 ${className}`}>
      <div className="text-center">
        <div className="relative mb-6">
          <div className="w-24 h-24 mx-auto rounded-full bg-marine-500/20 flex items-center justify-center animate-pulse">
            <svg
              className="w-12 h-12 text-marine-400"
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={1.5}
                d="M13 10V3L4 14h7v7l9-11h-7z"
              />
            </svg>
          </div>
          <div className="absolute -inset-2 rounded-full border-2 border-marine-500/30 animate-ping" />
        </div>
        <h2 className="text-2xl font-bold text-white mb-2">LinerDT</h2>
        <p className="text-gray-400 mb-6">班轮航运数字孪生仿真平台</p>
        <Button onClick={onStart} size="lg" leftIcon={
          <svg className="w-5 h-5" fill="currentColor" viewBox="0 0 24 24">
            <path d="M8 5v14l11-7z" />
          </svg>
        }>
          启动仿真
        </Button>
      </div>
    </div>
  )
}

interface LoadingStateProps {
  message?: string
  className?: string
}

export function LoadingState({ message = '加载中...', className = '' }: LoadingStateProps) {
  return (
    <div className={`flex flex-col items-center justify-center py-8 ${className}`}>
      <div className="relative w-12 h-12 mb-4">
        <div className="absolute inset-0 border-4 border-marine-500/20 rounded-full" />
        <div className="absolute inset-0 border-4 border-transparent border-t-marine-500 rounded-full animate-spin" />
      </div>
      <p className="text-sm text-gray-400">{message}</p>
    </div>
  )
}