'use client'

import { useEffect, useState, useRef } from 'react'
import Panel from '../ui/Panel'
import Badge from '../ui/Badge'

interface ShipData {
  unique_id: string
  name: string
  state: string
  current_speed: number
  design_speed?: number
  economic_speed?: number
  lat: number | null
  lon: number | null
  current_port: string | null
  next_port: string | null
  co2_emissions?: number
  cii_rating?: string
  cii_ratio?: number
  cumulative_delay?: number
  service?: string
  currentLoadTEU?: number
  maxCapacityTEU?: number
  deliveredRevenue?: number
}

interface ShipDetailAnimationProps {
  ship: ShipData
  onClose?: () => void
  onViewDetail?: () => void
}

const STATE_LABELS: Record<string, string> = {
  IDLE: '空闲',
  SAILING: '航行中',
  ARRIVING: '到港',
  BERTHING: '在港',
  WAITING: '等待',
  LOADING: '装卸中',
  DEPARTING: '离港',
  at_port: '在港',
  sailing: '航行中',
}

function useAnimatedNumber(target: number, duration = 600) {
  const [current, setCurrent] = useState(target)
  const prevRef = useRef(target)

  useEffect(() => {
    const from = prevRef.current
    const diff = target - from
    if (diff === 0) return

    const startTime = performance.now()
    let raf: number

    const animate = (now: number) => {
      const elapsed = now - startTime
      const progress = Math.min(elapsed / duration, 1)
      const eased = 1 - Math.pow(1 - progress, 3)
      const value = from + diff * eased
      setCurrent(Math.round(value))
      if (progress < 1) {
        raf = requestAnimationFrame(animate)
      } else {
        prevRef.current = target
        setCurrent(target)
      }
    }

    raf = requestAnimationFrame(animate)
    return () => cancelAnimationFrame(raf)
  }, [target, duration])

  useEffect(() => {
    prevRef.current = target
  }, [target])

  return current
}

export default function ShipDetailAnimation({ ship, onClose, onViewDetail }: ShipDetailAnimationProps) {
  const currentTEU = ship.currentLoadTEU ?? 0
  const maxCapacity = ship.maxCapacityTEU ?? 21413
  const revenue = ship.deliveredRevenue ?? 0
  const utilization = maxCapacity > 0 ? (currentTEU / maxCapacity) * 100 : 0

  const animatedTEU = useAnimatedNumber(currentTEU)
  const animatedRevenue = useAnimatedNumber(revenue)
  const prevRevenueRef = useRef(revenue)
  const [revenueFlash, setRevenueFlash] = useState(false)

  useEffect(() => {
    if (revenue > prevRevenueRef.current) {
      setRevenueFlash(true)
      const t = setTimeout(() => setRevenueFlash(false), 800)
      prevRevenueRef.current = revenue
      return () => clearTimeout(t)
    }
    prevRevenueRef.current = revenue
  }, [revenue])

  const barColor = utilization > 90 ? '#f97316' : utilization > 70 ? '#3b82f6' : '#22c55e'

  return (
    <Panel
      title={ship.name}
      icon={
        <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 10V3L4 14h7v7l9-11h-7z" />
        </svg>
      }
      collapsible
      headerActions={
        onClose && (
          <button
            type="button"
            onClick={onClose}
            className="p-1 text-gray-400 hover:text-white transition-colors"
            aria-label="关闭"
          >
            <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        )
      }
    >
      <div className="space-y-4">
        <div className="flex items-center justify-between">
          {ship.service && (
            <Badge variant="info">
              {ship.service}
            </Badge>
          )}
          <Badge
            variant={ship.state === 'SAILING' || ship.state === 'sailing' ? 'info' : ship.state === 'WAITING' || ship.state === 'waiting' ? 'danger' : 'success'}
          >
            {STATE_LABELS[ship.state] || ship.state}
          </Badge>
        </div>

        {onViewDetail && (
          <button
            onClick={onViewDetail}
            className="w-full flex items-center justify-center gap-2 px-3 py-2 rounded-lg text-xs font-medium
              bg-marine-500/10 text-marine-400 border border-marine-500/20
              hover:bg-marine-500/20 transition-all duration-200"
          >
            <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 10l4.553-2.276A1 1 0 0121 8.618v6.764a1 1 0 01-1.447.894L15 14M5 18h8a2 2 0 002-2V8a2 2 0 00-2-2H5a2 2 0 00-2 2v8a2 2 0 002 2z" />
            </svg>
            进入详细动画
          </button>
        )}

        {/* 载货状态板块 */}
        <div className="bg-white/5 rounded-lg p-3 space-y-3">
          <div className="flex items-center gap-2 mb-1">
            <svg className="w-4 h-4 text-blue-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M20 7l-8-4-8 4m16 0l-8 4m8-4v10l-8 4m0-10L4 7m8 4v10M4 7v10l8 4" />
            </svg>
            <span className="text-xs font-medium text-gray-300">载货状态</span>
          </div>

          <div className="grid grid-cols-3 gap-3 text-center">
            <div>
              <div className="text-[9px] text-gray-500 mb-0.5">当前 TEU</div>
              <div className="text-sm font-bold text-blue-400 font-mono tabular-nums">
                {animatedTEU.toLocaleString()}
              </div>
            </div>
            <div>
              <div className="text-[9px] text-gray-500 mb-0.5">最大运力</div>
              <div className="text-sm font-bold text-gray-300 font-mono tabular-nums">
                {maxCapacity.toLocaleString()}
              </div>
            </div>
            <div>
              <div className="text-[9px] text-gray-500 mb-0.5">已获收益</div>
              <div className={`text-sm font-bold font-mono tabular-nums transition-colors duration-300 ${
                revenueFlash ? 'text-emerald-300 scale-110' : 'text-emerald-400'
              }`}
              style={{ transform: revenueFlash ? 'scale(1.1)' : 'scale(1)', transition: 'transform 0.3s ease, color 0.3s ease' }}
              >
                ${(animatedRevenue >= 1000000 ? (animatedRevenue / 1000000).toFixed(2) + 'M' : animatedRevenue >= 1000 ? (animatedRevenue / 1000).toFixed(1) + 'K' : animatedRevenue)}
              </div>
            </div>
          </div>

          <div>
            <div className="flex justify-between text-[9px] text-gray-500 mb-1">
              <span>舱容利用率</span>
              <span style={{ color: barColor }}>{utilization.toFixed(1)}%</span>
            </div>
            <div className="h-2.5 bg-white/10 rounded-full overflow-hidden">
              <div
                className="h-full rounded-full transition-all duration-500 ease-out"
                style={{
                  width: `${Math.min(utilization, 100)}%`,
                  backgroundColor: barColor,
                  boxShadow: utilization > 90 ? `0 0 8px ${barColor}80` : 'none',
                }}
              />
            </div>
            <div className="flex justify-between text-[8px] text-gray-600 mt-0.5">
              <span>0</span>
              <span>{maxCapacity.toLocaleString()} TEU</span>
            </div>
          </div>
        </div>

        <div className="grid grid-cols-3 gap-2 text-center text-xs">
          <div>
            <div className="text-gray-400">当前位置</div>
            <div className="text-white font-medium truncate">
              {ship.current_port || 'N/A'}
            </div>
          </div>
          <div>
            <div className="text-gray-400">下一港口</div>
            <div className="text-white font-medium truncate">
              {ship.next_port || 'N/A'}
            </div>
          </div>
          <div>
            <div className="text-gray-400">累计延误</div>
            <div className={`font-medium ${(ship.cumulative_delay || 0) > 24 ? 'text-red-400' : 'text-white'}`}>
              {(ship.cumulative_delay || 0).toFixed(1)}h
            </div>
          </div>
        </div>
      </div>
    </Panel>
  )
}