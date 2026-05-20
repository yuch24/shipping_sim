'use client'

import { useMemo } from 'react'

interface ShipData {
  unique_id: string
  name: string
  state: string
  current_speed: number
  lat: number | null
  lon: number | null
  cii_rating?: string
}

interface PortData {
  unique_id: string
  name: string
  queue_length: number
  available_berths?: number
  berth_count?: number
}

interface RealTimeMonitorProps {
  ships: ShipData[]
  ports: Record<string, PortData>
  currentTime: number
  aisSourceMode?: string
  onSetAisSource?: (source: string) => void
}

export default function RealTimeMonitor({ ships, ports, currentTime, aisSourceMode = 'mock', onSetAisSource }: RealTimeMonitorProps) {
  const stats = useMemo(() => {
    const sailing = ships.filter(s => s.state === 'SAILING').length
    const berthed = ships.filter(s => s.state === 'BERTHING' || s.state === 'LOADING' || s.state === 'UNLOADING').length
    const waiting = ships.filter(s => s.state === 'WAITING' || s.state === 'ARRIVING').length
    const idle = ships.filter(s => s.state === 'IDLE').length
    const avgSpeed = ships.filter(s => s.state === 'SAILING').reduce((sum, s) => sum + (s.current_speed || 0), 0) / Math.max(sailing, 1)
    const congestedPorts = Object.values(ports).filter(p => p.queue_length > 0).length
    return { sailing, berthed, waiting, idle, avgSpeed: avgSpeed.toFixed(1), congestedPorts }
  }, [ships, ports])

  const topCongested = useMemo(() => {
    return Object.values(ports)
      .filter(p => p.queue_length > 0)
      .sort((a, b) => b.queue_length - a.queue_length)
      .slice(0, 5)
  }, [ports])

  return (
    <div className="glass-panel p-3 min-w-[200px]">
      <div className="flex items-center gap-2 mb-3">
        <span className="w-2 h-2 rounded-full bg-green-400 animate-pulse" />
        <span className="text-xs font-medium text-green-400 tracking-wider">实时监测</span>
        <span className="text-[10px] text-gray-600 ml-auto">
          T+{Math.floor(currentTime)}s
        </span>
      </div>

      <div className="grid grid-cols-2 gap-2 mb-3">
        <div className="bg-white/5 rounded p-2">
          <div className="text-[10px] text-gray-500">在航</div>
          <div className="text-sm font-bold text-blue-400">{stats.sailing}</div>
        </div>
        <div className="bg-white/5 rounded p-2">
          <div className="text-[10px] text-gray-500">在港</div>
          <div className="text-sm font-bold text-green-400">{stats.berthed}</div>
        </div>
        <div className="bg-white/5 rounded p-2">
          <div className="text-[10px] text-gray-500">等待</div>
          <div className="text-sm font-bold text-yellow-400">{stats.waiting}</div>
        </div>
        <div className="bg-white/5 rounded p-2">
          <div className="text-[10px] text-gray-500">均速</div>
          <div className="text-sm font-bold text-cyan-400">{stats.avgSpeed} kn</div>
        </div>
      </div>

      {topCongested.length > 0 && (
        <div>
          <div className="text-[10px] text-gray-500 mb-2">拥堵港口排行</div>
          <div className="space-y-1.5">
            {topCongested.map(p => {
              const util = p.berth_count ? Math.round(((p.berth_count - (p.available_berths ?? p.berth_count)) / p.berth_count) * 100) : 0
              return (
                <div key={p.unique_id} className="flex items-center justify-between text-xs">
                  <span className="text-gray-300">{p.name}</span>
                  <div className="flex items-center gap-2">
                    <div className="w-16 h-1.5 bg-white/10 rounded-full overflow-hidden">
                      <div
                        className="h-full rounded-full"
                        style={{
                          width: `${Math.min(util, 100)}%`,
                          backgroundColor: util > 75 ? '#EF4444' : util > 50 ? '#F59E0B' : '#3B82F6',
                        }}
                      />
                    </div>
                    <span className="text-gray-400 w-4 text-right">{p.queue_length}</span>
                  </div>
                </div>
              )
            })}
          </div>
        </div>
      )}

      <div className="mt-3 pt-2 border-t border-white/10">
        <div className="flex items-center justify-between">
          <div className="text-[10px] text-gray-600">
            更新频率: 1Hz
          </div>
          {onSetAisSource && (
            <div className="flex items-center gap-1">
              <button
                onClick={() => onSetAisSource('mock')}
                className={`px-2 py-0.5 text-[10px] rounded transition-all ${
                  aisSourceMode === 'mock'
                    ? 'bg-amber-500/20 text-amber-400'
                    : 'text-gray-600 hover:text-gray-400'
                }`}
              >
                Mock
              </button>
              <button
                onClick={() => onSetAisSource('real')}
                className={`px-2 py-0.5 text-[10px] rounded transition-all ${
                  aisSourceMode === 'real'
                    ? 'bg-green-500/20 text-green-400'
                    : 'text-gray-600 hover:text-gray-400'
                }`}
              >
                Live
              </button>
            </div>
          )}
        </div>
        <div className="text-[10px] text-gray-600 mt-1">
          {aisSourceMode === 'real' ? '数据源: AIS Stream (真实)' : '数据源: AIS Mock (模拟)'}
        </div>
      </div>
    </div>
  )
}
