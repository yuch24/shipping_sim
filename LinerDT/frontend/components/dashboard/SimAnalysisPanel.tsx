'use client'

import ReactECharts from 'echarts-for-react'
import { useEffect, useRef, useState } from 'react'

interface SimAnalysisPanelProps {
  totalRevenue: number
  averageUtilization: number
  globalDelayRate: number
  revenueTimeline: { time: number; revenue: number }[]
  shipCount: number
}

export default function SimAnalysisPanel({
  totalRevenue,
  averageUtilization,
  globalDelayRate,
  revenueTimeline,
  shipCount,
}: SimAnalysisPanelProps) {
  const [displayRevenue, setDisplayRevenue] = useState(0)
  const prevRevenue = useRef(0)

  useEffect(() => {
    const diff = totalRevenue - prevRevenue.current
    if (diff === 0) return
    const steps = 20
    const increment = diff / steps
    let current = prevRevenue.current
    const interval = setInterval(() => {
      current += increment
      if (current >= totalRevenue) {
        current = totalRevenue
        clearInterval(interval)
        prevRevenue.current = totalRevenue
      }
      setDisplayRevenue(Math.round(current))
    }, 50)
    return () => clearInterval(interval)
  }, [totalRevenue])

  const formatMoney = (v: number) => {
    if (v >= 1e6) return `$${(v / 1e6).toFixed(2)}M`
    if (v >= 1e3) return `$${(v / 1e3).toFixed(1)}K`
    return `$${v}`
  }

  const formatDays = (h: number) => `${Math.floor(h / 24)}d ${Math.floor(h % 24)}h`

  return (
    <div className="flex flex-col h-full bg-[#0a1929] text-white overflow-hidden">
      <div className="px-4 py-2 border-b border-white/10 shrink-0">
        <h2 className="text-sm font-semibold text-marine-400">仿真分析</h2>
      </div>

      <div className="flex-1 overflow-y-auto p-3 space-y-3">
        {/* Revenue card */}
        <div className="bg-gradient-to-r from-emerald-500/10 to-marine-500/10 rounded-lg p-3 border border-emerald-500/20">
          <div className="flex items-center gap-2">
            <div className="w-8 h-8 rounded-full bg-emerald-500/20 flex items-center justify-center text-emerald-400 text-lg">$</div>
            <div>
              <div className="text-[9px] text-gray-500 uppercase tracking-wider">实时总收益</div>
              <div className="text-lg font-bold text-emerald-400 font-mono tabular-nums">{formatMoney(displayRevenue)}</div>
            </div>
          </div>
        </div>

        {/* Utilization card */}
        <div className="bg-gradient-to-r from-blue-500/10 to-marine-500/10 rounded-lg p-3 border border-blue-500/20">
          <div className="flex items-center justify-between mb-1">
            <div className="flex items-center gap-2">
              <div className="w-6 h-6 rounded bg-blue-500/20 flex items-center justify-center">
                <svg className="w-3.5 h-3.5 text-blue-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
                </svg>
              </div>
              <div className="text-[9px] text-gray-500 uppercase tracking-wider">平均舱容利用率</div>
            </div>
            <div className="text-sm font-bold text-blue-400 font-mono tabular-nums">{averageUtilization.toFixed(1)}%</div>
          </div>
          <div className="w-full h-2 bg-white/10 rounded-full overflow-hidden">
            <div
              className="h-full rounded-full transition-all duration-300"
              style={{
                width: `${Math.min(100, averageUtilization)}%`,
                background: averageUtilization > 80 ? '#ef4444' : averageUtilization > 50 ? '#3b82f6' : '#22c55e',
              }}
            />
          </div>
          <div className="text-[8px] text-gray-600 mt-0.5">{shipCount} 船平均</div>
        </div>

        {/* Delay rate card */}
        <div className="bg-gradient-to-r from-amber-500/10 to-marine-500/10 rounded-lg p-3 border border-amber-500/20">
          <div className="flex items-center gap-2">
            <div className="w-6 h-6 rounded bg-amber-500/20 flex items-center justify-center">
              <svg className="w-3.5 h-3.5 text-amber-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
            </div>
            <div>
              <div className="text-[9px] text-gray-500 uppercase tracking-wider">全局延误率</div>
              <div className="text-sm font-bold text-amber-400 font-mono tabular-nums">{globalDelayRate.toFixed(1)}%</div>
            </div>
          </div>
        </div>

        {/* Revenue trend chart */}
        {revenueTimeline.length > 1 && (
          <div className="bg-white/5 rounded-lg p-2 border border-white/10">
            <div className="text-[9px] text-gray-500 mb-1">收益趋势</div>
            <ReactECharts
              option={{
                grid: { top: 8, right: 12, bottom: 24, left: 36 },
                xAxis: {
                  type: 'category',
                  data: revenueTimeline.map(p => formatDays(p.time)),
                  axisLabel: { fontSize: 8, color: '#6b7280' },
                  axisLine: { lineStyle: { color: '#374151' } },
                },
                yAxis: {
                  type: 'value',
                  axisLabel: { fontSize: 8, color: '#6b7280', formatter: (v: number) => formatMoney(v) },
                  splitLine: { lineStyle: { color: '#1e3a5f' } },
                },
                series: [{
                  type: 'line',
                  data: revenueTimeline.map(p => p.revenue),
                  smooth: true,
                  symbol: 'none',
                  lineStyle: { color: '#10b981', width: 2 },
                  areaStyle: { color: { type: 'linear', x: 0, y: 0, x2: 0, y2: 1, colorStops: [{ offset: 0, color: 'rgba(16,185,129,0.3)' }, { offset: 1, color: 'rgba(16,185,129,0)' }] } },
                }],
                tooltip: { trigger: 'axis', backgroundColor: '#1e293b', textStyle: { fontSize: 10, color: '#e5e7eb' } },
              }}
              style={{ height: '160px' }}
            />
          </div>
        )}
      </div>
    </div>
  )
}