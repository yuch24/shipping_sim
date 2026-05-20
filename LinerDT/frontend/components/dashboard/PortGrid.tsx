'use client'

import Badge from '../ui/Badge'

interface PortData {
  unique_id: string
  name: string
  queue_length: number
  available_berths?: number
  berth_count?: number
}

export default function PortGrid({ ports }: { ports: PortData[] }) {
  const totalBerths = (p: PortData) => p.berth_count ?? 4
  const usageRate = (p: PortData) => {
    const total = totalBerths(p)
    const used = total - (p.available_berths ?? total)
    return total > 0 ? (used / total) * 100 : 0
  }

  return (
    <div className="grid grid-cols-3 sm:grid-cols-5 gap-2">
      {ports.map((port) => {
        const rate = usageRate(port)
        return (
          <div
            key={port.unique_id}
            className="bg-white/5 rounded-lg p-2.5 text-center hover:bg-white/10 transition-colors"
          >
            <div className="text-sm font-medium text-white mb-1">{port.name}</div>
            <div className="flex items-center justify-center gap-1.5 mb-0.5">
              <span
                className={`text-lg font-bold ${
                  port.queue_length > 0 ? 'text-red-400' : 'text-green-400'
                }`}
              >
                {port.queue_length}
              </span>
              <span className="text-[10px] text-gray-500">排队</span>
            </div>
            <div className="flex items-center justify-center gap-1 text-xs text-gray-400">
              <span>{port.available_berths ?? totalBerths(port)}</span>
              <span className="text-gray-600">/</span>
              <span>{totalBerths(port)}</span>
              <span className="text-gray-600 ml-1">泊位</span>
            </div>
            {/* Mini utilization bar */}
            <div className="mt-1.5 h-1 bg-gray-700 rounded-full overflow-hidden">
              <div
                className={`h-full rounded-full transition-all ${
                  rate > 60 ? 'bg-red-500' : rate > 30 ? 'bg-yellow-500' : 'bg-green-500'
                }`}
                style={{ width: `${Math.min(rate, 100)}%` }}
              />
            </div>
          </div>
        )
      })}
    </div>
  )
}
