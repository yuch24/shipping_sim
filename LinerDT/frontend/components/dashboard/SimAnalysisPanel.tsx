'use client'

import ReactECharts from 'echarts-for-react'
import * as echarts from 'echarts'
import { useEffect, useRef, useState } from 'react'

interface SimAnalysisPanelProps {
  totalRevenue: number
  averageUtilization: number
  globalDelayRate: number
  revenueTimeline: { time: number; revenue: number }[]
  shipCount: number
  routeRevenue: Record<string, { total: number; average: number }>
  totalAverageRevenue: number
  routeRevenueTimeline: Record<string, { time: number; revenue: number }[]>
}

const ROUTE_COLORS: Record<string, string> = {
  AEU1: '#22d3ee',
  AEU2: '#fb923c',
  AEU3: '#a78bfa',
}

const ROUTE_LABELS: Record<string, string> = {
  AEU1: 'AEU1 亚欧1线',
  AEU2: 'AEU2 亚欧2线',
  AEU3: 'AEU3 亚欧3线',
}

const ROUTE_WEEKS: Record<string, number> = {
  AEU1: 15,
  AEU2: 15,
  AEU3: 14,
}

export default function SimAnalysisPanel({
  totalRevenue,
  averageUtilization,
  globalDelayRate,
  revenueTimeline,
  shipCount,
  routeRevenue,
  totalAverageRevenue,
  routeRevenueTimeline,
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

  const MAX_POINTS = 60

  const trimTimeline = (arr: { time: number; revenue: number }[]) => {
    if (arr.length <= MAX_POINTS) return arr
    return arr.slice(arr.length - MAX_POINTS)
  }

  const trimmedTotal = trimTimeline(revenueTimeline)
  const windowTimes = trimmedTotal.map(p => p.time)

  const series = Object.entries(routeRevenueTimeline).map(([rid, tl]) => {
    const trimmed = trimTimeline(tl)
    const baseColor = ROUTE_COLORS[rid] || '#fff'
    return {
      name: rid,
      type: 'line' as const,
      data: windowTimes.map(t => {
        const entry = trimmed.find(p => p.time === t)
        return entry ? entry.revenue : null
      }),
      smooth: true,
      symbol: 'none',
      showAllSymbol: false,
      sampling: 'lttb',
      lineStyle: {
        width: 2.5,
        color: new echarts.graphic.LinearGradient(0, 0, 1, 0, [
          { offset: 0, color: baseColor },
          { offset: 1, color: baseColor + 'cc' },
        ]),
      },
      areaStyle: {
        color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
          { offset: 0, color: baseColor + '33' },
          { offset: 1, color: baseColor + '00' },
        ]),
      },
      connectNulls: true,
    }
  })

  const mergedTimeline = revenueTimeline.length > 0 && Object.values(routeRevenueTimeline).some(a => a.length > 0)

  return (
    <div className="flex flex-col h-full bg-[#0a1929] text-white overflow-hidden">
      <div className="px-4 py-2 border-b border-white/10 shrink-0">
        <h2 className="text-sm font-semibold text-marine-400">仿真分析</h2>
      </div>

      <div className="flex-1 overflow-y-auto p-3 space-y-3">
        {/* 总收益 */}
        <div className="bg-gradient-to-r from-emerald-500/10 to-marine-500/10 rounded-lg p-3 border border-emerald-500/20">
          <div className="flex items-center gap-2">
            <div className="w-8 h-8 rounded-full bg-emerald-500/20 flex items-center justify-center text-emerald-400 text-lg">$</div>
            <div>
              <div className="text-[9px] text-gray-500 uppercase tracking-wider">实时总收益</div>
              <div className="text-lg font-bold text-emerald-400 font-mono tabular-nums">{formatMoney(displayRevenue)}</div>
            </div>
          </div>
        </div>

        {/* 航线平均收益卡 */}
        <div className="grid grid-cols-2 gap-2">
          {['AEU1', 'AEU2', 'AEU3'].map(rid => (
            <div key={rid}
              className="rounded-lg p-2 border"
              style={{
                background: `linear-gradient(135deg, ${ROUTE_COLORS[rid]}08, transparent)`,
                borderColor: `${ROUTE_COLORS[rid]}20`,
              }}
            >
              <div className="flex items-center gap-1.5 mb-1">
                <div className="w-2 h-2 rounded-full" style={{ backgroundColor: ROUTE_COLORS[rid] }} />
                <span className="text-[9px] text-gray-400">{rid}</span>
              </div>
              <div className="text-[11px] font-bold font-mono" style={{ color: ROUTE_COLORS[rid] }}>
                {formatMoney(routeRevenue[rid]?.total || 0)}
              </div>
              <div className="text-[8px] text-gray-600 mt-0.5">
                平均每周期 {formatMoney(routeRevenue[rid]?.average || 0)}
              </div>
            </div>
          ))}
          <div className="col-span-2 rounded-lg p-2 border border-marine-400/30"
            style={{ background: 'linear-gradient(135deg, var(--tw-gradient-stops))' }}
          >
            <div className="flex items-center gap-1.5 mb-1">
              <svg className="w-3 h-3 text-marine-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 3l14 9-14 9V3z" />
              </svg>
              <span className="text-[9px] text-gray-400">三航线周均收益合计</span>
            </div>
            <div className="text-lg font-bold text-marine-400 font-mono tabular-nums">
              {formatMoney(totalAverageRevenue)}
            </div>
            <div className="text-[8px] text-gray-600 mt-0.5">AEU1/15w + AEU2/15w + AEU3/14w</div>
          </div>
        </div>

        {/* 三航线收益折线图 */}
        {mergedTimeline && (
          <div className="bg-white/5 rounded-lg p-2 border border-white/10">
            <div className="flex items-center gap-2 mb-1">
              <span className="text-[9px] text-gray-500">分航线收益趋势</span>
              {['AEU1', 'AEU2', 'AEU3'].map(rid => (
                <span key={rid} className="flex items-center gap-1 text-[8px]">
                  <span className="w-1.5 h-1.5 rounded-full" style={{ backgroundColor: ROUTE_COLORS[rid] }} />
                  <span className="text-gray-500">{rid}</span>
                </span>
              ))}
            </div>
            <ReactECharts
              notMerge={false}
              option={{
                grid: { top: 10, right: 14, bottom: 28, left: 44, containLabel: false },
                xAxis: {
                  type: 'category',
                  boundaryGap: false,
                  data: windowTimes.map(t => formatDays(t)),
                  axisLabel: { fontSize: 8, color: '#6b7280', rotate: 0 },
                  axisLine: { lineStyle: { color: '#374151' } },
                  axisTick: { show: false },
                },
                yAxis: {
                  type: 'value',
                  axisLabel: { fontSize: 8, color: '#6b7280', formatter: (v: number) => formatMoney(v) },
                  splitLine: { lineStyle: { type: 'dashed', color: '#1e3a5f30' } },
                },
                series,
                tooltip: {
                  trigger: 'axis',
                  backgroundColor: 'rgba(15, 23, 42, 0.95)',
                  borderColor: '#334155',
                  borderRadius: 6,
                  textStyle: { fontSize: 10, color: '#e5e7eb' },
                  formatter: (params: any[]) => {
                    if (!params || !params.length) return ''
                    const time = formatDays(params[0].axisValue ? parseFloat(params[0].axisValue) : 0)
                    return `<div style="font-size:9px;color:#6b7280;margin-bottom:4px">⏱ ${time}</div>` +
                      params.map(p => `<div style="display:flex;justify-content:space-between;gap:12px"><span style="color:${p.color}">● ${p.seriesName}</span><span style="color:#e5e7eb;font-weight:600">${formatMoney(p.value ?? 0)}</span></div>`).join('')
                  },
                },
                legend: { show: false },
              }}
              style={{ height: '160px' }}
              lazyUpdate
            />
          </div>
        )}

        {/* 舱容利用率 */}
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

        {/* 延误率 */}
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
      </div>
    </div>
  )
}