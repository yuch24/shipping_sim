'use client'

import { useEffect, useState } from 'react'
import dynamic from 'next/dynamic'
import Panel from '../ui/Panel'
import Badge from '../ui/Badge'

const Port3DView = dynamic(() => import('../three/Port3DView'), {
  ssr: false,
  loading: () => (
    <div className="w-full h-[160px] flex items-center justify-center text-gray-500 text-xs">
      加载 3D 视图...
    </div>
  ),
})

interface PortData {
  unique_id: string
  name: string
  lat: number
  lon: number
  queue_length: number
  available_berths?: number
  berth_count?: number
  waiting_queue?: string[]
  occupied_berths?: Record<string, string>
}

interface PortMicroViewProps {
  port: PortData
  onClose?: () => void
  onViewDetail?: () => void
}

export default function PortMicroView({ port, onClose, onViewDetail }: PortMicroViewProps) {
  const [animationKey, setAnimationKey] = useState(0)

  useEffect(() => {
    const interval = setInterval(() => {
      setAnimationKey(prev => prev + 1)
    }, 2000)
    return () => clearInterval(interval)
  }, [])

  const totalBerths = port.berth_count || 4
  const availableBerths = port.available_berths ?? totalBerths
  const occupiedBerths = totalBerths - availableBerths
  const waitingCount = port.queue_length || 0

  const getBerthColor = (index: number) => {
    if (index < occupiedBerths) return 'bg-red-500'
    if (index < totalBerths) return 'bg-green-500'
    return 'bg-gray-700'
  }

  const getBerthAnimation = (index: number) => {
    if (index < occupiedBerths) return 'animate-pulse'
    return ''
  }

  return (
    <Panel
      title={port.name}
      icon={
        <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 21V5a2 2 0 00-2-2H7a2 2 0 00-2 2v16m14 0h2m-2 0h-5m-9 0H3m2 0h5M9 7h1m-1 4h1m4-4h1m-1 4h1m-5 10v-5a1 1 0 011-1h2a1 1 0 011 1v5m-4 0h4" />
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
        {/* Three.js 3D 港口视图 */}
        <div className="flex justify-center">
          <Port3DView
            queueLength={port.queue_length || 0}
            availableBerths={port.available_berths ?? port.berth_count ?? 4}
            totalBerths={port.berth_count || 4}
            width={240}
            height={160}
          />
        </div>

        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <span className="text-2xl font-bold text-white">{totalBerths}</span>
            <span className="text-sm text-gray-400">总泊位数</span>
          </div>
          <Badge variant={waitingCount > 0 ? 'danger' : 'success'} dot>
            {waitingCount > 0 ? `${waitingCount} 艘排队` : '无排队'}
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

        <div className="space-y-2">
          <div className="text-xs text-gray-400 mb-2">泊位状态</div>
          <div className="grid grid-cols-5 gap-2">
            {Array.from({ length: totalBerths }).map((_, index) => (
              <div
                key={`berth-${animationKey}-${index}`}
                className={`
                  aspect-square rounded-lg flex items-center justify-center text-xs font-medium
                  ${getBerthColor(index)} ${getBerthAnimation(index)}
                  transition-all duration-300
                `}
              >
                {index < occupiedBerths ? (
                  <svg className="w-4 h-4 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                  </svg>
                ) : (
                  <svg className="w-4 h-4 text-gray-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M20 12H4" />
                  </svg>
                )}
              </div>
            ))}
          </div>
        </div>

        <div className="flex items-center gap-4 text-sm">
          <div className="flex items-center gap-2">
            <span className="w-3 h-3 rounded bg-red-500" />
            <span className="text-gray-400">占用中</span>
          </div>
          <div className="flex items-center gap-2">
            <span className="w-3 h-3 rounded bg-green-500" />
            <span className="text-gray-400">可用</span>
          </div>
        </div>

        {waitingCount > 0 && (
          <div className="space-y-2">
            <div className="text-xs text-gray-400">排队船舶</div>
            <div className="space-y-1">
              {(port.waiting_queue || []).slice(0, 5).map((shipId, index) => (
                <div
                  key={`queue-${animationKey}-${index}`}
                  className="flex items-center gap-2 text-sm animate-pulse"
                >
                  <svg className="w-4 h-4 text-yellow-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                  </svg>
                  <span className="text-gray-300">{shipId}</span>
                </div>
              ))}
            </div>
          </div>
        )}

        <div className="grid grid-cols-2 gap-3 pt-2 border-t border-white/10">
          <div className="text-center">
            <div className="text-lg font-bold text-green-400">{availableBerths}</div>
            <div className="text-xs text-gray-400">可用泊位</div>
          </div>
          <div className="text-center">
            <div className="text-lg font-bold text-red-400">{occupiedBerths}</div>
            <div className="text-xs text-gray-400">占用泊位</div>
          </div>
        </div>
      </div>
    </Panel>
  )
}