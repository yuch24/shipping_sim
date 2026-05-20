'use client'

import CountUpNumber from '../animations/CountUpNumber'

interface KPIWithTrendProps {
  value: number
  label: string
  unit?: string
  decimals?: number
  trend?: number
  trendLabel?: string
  icon?: React.ReactNode
  className?: string
}

export default function KPIWithTrend({
  value,
  label,
  unit = '',
  decimals = 1,
  trend,
  trendLabel,
  icon,
  className = '',
}: KPIWithTrendProps) {
  const getTrendColor = () => {
    if (trend === undefined || trend === 0) return 'text-gray-400'
    return trend > 0 ? 'text-green-400' : 'text-red-400'
  }

  const getTrendIcon = () => {
    if (trend === undefined || trend === 0) return null
    if (trend > 0) {
      return (
        <svg className="w-3 h-3" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 10l7-7m0 0l7 7m-7-7v18" />
        </svg>
      )
    }
    return (
      <svg className="w-3 h-3" fill="none" viewBox="0 0 24 24" stroke="currentColor">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 14l-7 7m0 0l-7-7m7 7V3" />
      </svg>
    )
  }

  return (
    <div className={`glass-panel p-4 ${className}`}>
      <div className="flex items-start justify-between">
        <div className="flex-1">
          <div className="text-xs text-gray-400 mb-1">{label}</div>
          <div className="flex items-baseline gap-1">
            <span className="text-3xl font-bold text-white">
              <CountUpNumber value={value} decimals={decimals} />
            </span>
            <span className="text-sm text-gray-400">{unit}</span>
          </div>
          {trend !== undefined && (
            <div className={`flex items-center gap-1 mt-1 text-xs ${getTrendColor()}`}>
              {getTrendIcon()}
              <span>{Math.abs(trend).toFixed(1)}%</span>
              {trendLabel && <span className="text-gray-500 ml-1">{trendLabel}</span>}
            </div>
          )}
        </div>
        {icon && (
          <div className="p-2 rounded-lg bg-marine-500/20 text-marine-400">
            {icon}
          </div>
        )}
      </div>
    </div>
  )
}