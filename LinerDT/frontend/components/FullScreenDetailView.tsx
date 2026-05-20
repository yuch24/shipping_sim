'use client'

import { useEffect, useRef } from 'react'
import dynamic from 'next/dynamic'

const Ship3DView = dynamic(() => import('./three/Ship3DView'), {
  ssr: false,
  loading: () => (
    <div className="flex items-center justify-center text-gray-500 text-sm">
      加载 3D 场景...
    </div>
  ),
})

const Port3DView = dynamic(() => import('./three/Port3DView'), {
  ssr: false,
  loading: () => (
    <div className="flex items-center justify-center text-gray-500 text-sm">
      加载 3D 场景...
    </div>
  ),
})

interface ShipDetail {
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
  cumulative_delay?: number
  capacity_teu?: number
  load_factor?: number
}

interface PortDetail {
  unique_id: string
  name: string
  lat: number
  lon: number
  queue_length: number
  available_berths?: number
  berth_count?: number
  waiting_queue?: string[]
}

interface FullScreenDetailViewProps {
  type: 'ship' | 'port'
  data: ShipDetail | PortDetail
  onClose: () => void
}

const STATE_LABELS: Record<string, string> = {
  IDLE: '空闲',
  SAILING: '航行中',
  ARRIVING: '到港',
  BERTHING: '在港',
  WAITING: '等待',
  LOADING: '装卸中',
  DEPARTING: '离港',
}

export default function FullScreenDetailView({ type, data, onClose }: FullScreenDetailViewProps) {
  const containerRef = useRef<HTMLDivElement>(null)

  // ESC 键关闭
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose()
    }
    window.addEventListener('keydown', handleKeyDown)
    return () => window.removeEventListener('keydown', handleKeyDown)
  }, [onClose])

  const ship = type === 'ship' ? (data as ShipDetail) : null
  const port = type === 'port' ? (data as PortDetail) : null

  return (
    <div className="fixed inset-0 z-50 flex flex-col bg-[#0a1929]">
      {/* 顶部栏 */}
      <div className="flex items-center justify-between px-6 py-3 border-b border-white/10">
        <div className="flex items-center gap-3">
          <div className="w-8 h-8 rounded-lg bg-marine-500/20 flex items-center justify-center">
            {type === 'ship' ? (
              <svg className="w-5 h-5 text-marine-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 10V3L4 14h7v7l9-11h-7z" />
              </svg>
            ) : (
              <svg className="w-5 h-5 text-marine-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 21V5a2 2 0 00-2-2H7a2 2 0 00-2 2v16m14 0h2m-2 0h-5m-9 0H3m2 0h5M9 7h1m-1 4h1m4-4h1m-1 4h1m-5 10v-5a1 1 0 011-1h2a1 1 0 011 1v5m-4 0h4" />
              </svg>
            )}
          </div>
          <div>
            <h2 className="text-lg font-bold text-white">{ship?.name || port?.name || ''}</h2>
            <p className="text-xs text-gray-500">
              {type === 'ship' ? '船舶详细动画' : '港口详细动画'}
              <span className="ml-2 text-gray-600">预览版 · 后续将升级为精细 3D 场景</span>
            </p>
          </div>
        </div>
        <button
          onClick={onClose}
          className="p-2 text-gray-400 hover:text-white hover:bg-white/10 rounded-lg transition-colors"
          aria-label="关闭"
        >
          <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
          </svg>
        </button>
      </div>

      {/* 3D 场景占用主要区域 */}
      <div className="flex-1 relative">
        <div ref={containerRef} className="absolute inset-0 flex items-center justify-center">
          {type === 'ship' && ship && (
            <Ship3DView
              state={ship.state}
              currentSpeed={ship.current_speed}
              ciiRating={ship.cii_rating}
              width={800}
              height={600}
            />
          )}
          {type === 'port' && port && (
            <Port3DView
              queueLength={port.queue_length || 0}
              availableBerths={port.available_berths ?? port.berth_count ?? 4}
              totalBerths={port.berth_count || 4}
              width={800}
              height={600}
            />
          )}
        </div>

        {/* 右下角信息面板 */}
        <div className="absolute bottom-6 right-6 glass-panel p-4 min-w-[220px] max-w-[280px]">
          {type === 'ship' && ship && (
            <div className="space-y-3">
              <div className="flex items-center justify-between">
                <span className="text-xs text-gray-400">状态</span>
                <span className="text-xs px-2 py-0.5 rounded-full bg-blue-500/10 text-blue-400 border border-blue-500/20">
                  {STATE_LABELS[ship.state] || ship.state}
                </span>
              </div>
              <div className="grid grid-cols-2 gap-2 text-xs">
                <div>
                  <span className="text-gray-500">航速</span>
                  <p className="text-white font-medium">{ship.current_speed} 节</p>
                </div>
                <div>
                  <span className="text-gray-500">经济航速</span>
                  <p className="text-green-400 font-medium">{ship.economic_speed || 18} 节</p>
                </div>
                <div>
                  <span className="text-gray-500">CII 评级</span>
                  <p className="text-white font-medium">{ship.cii_rating || 'N/A'}</p>
                </div>
                <div>
                  <span className="text-gray-500">延误</span>
                  <p className={(ship.cumulative_delay || 0) > 24 ? 'text-red-400 font-medium' : 'text-white font-medium'}>
                    {(ship.cumulative_delay || 0).toFixed(1)}h
                  </p>
                </div>
              </div>
              <div className="pt-2 border-t border-white/10 grid grid-cols-2 gap-2 text-xs">
                <div>
                  <span className="text-gray-500">当前位置</span>
                  <p className="text-white truncate">{ship.current_port || 'N/A'}</p>
                </div>
                <div>
                  <span className="text-gray-500">下一港口</span>
                  <p className="text-white truncate">{ship.next_port || 'N/A'}</p>
                </div>
              </div>
            </div>
          )}
          {type === 'port' && port && (
            <div className="space-y-3">
              <div className="flex items-center justify-between">
                <span className="text-xs text-gray-400">拥堵状态</span>
                <span className={`text-xs px-2 py-0.5 rounded-full ${
                  (port.queue_length || 0) > 0
                    ? 'bg-red-500/10 text-red-400 border border-red-500/20'
                    : 'bg-green-500/10 text-green-400 border border-green-500/20'
                }`}>
                  {(port.queue_length || 0) > 0 ? `${port.queue_length} 艘排队` : '通畅'}
                </span>
              </div>
              <div className="grid grid-cols-2 gap-2 text-xs">
                <div>
                  <span className="text-gray-500">总泊位</span>
                  <p className="text-white font-medium">{port.berth_count || 4}</p>
                </div>
                <div>
                  <span className="text-gray-500">可用泊位</span>
                  <p className="text-green-400 font-medium">{port.available_berths ?? port.berth_count ?? 4}</p>
                </div>
              </div>
              {port.waiting_queue && port.waiting_queue.length > 0 && (
                <div className="pt-2 border-t border-white/10">
                  <span className="text-xs text-gray-500">排队船舶</span>
                  <div className="mt-1 space-y-1">
                    {port.waiting_queue.slice(0, 6).map((sid) => (
                      <div key={sid} className="flex items-center gap-2 text-xs text-gray-400">
                        <span className="w-1.5 h-1.5 rounded-full bg-yellow-500" />
                        {sid}
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
