'use client'

import { useState, useEffect } from 'react'
import { Card, Badge } from '@/components/ui'
import ReactECharts from 'echarts-for-react'
import type { StatsData, HistogramBin } from '@/types/simulation'

interface AcademicStatsProps {
  autoRefresh?: boolean
}

export default function AcademicStatsPanel({ autoRefresh = true }: AcademicStatsProps) {
  const [stats, setStats] = useState<StatsData | null>(null)
  const [loading, setLoading] = useState(false)
  const [activeTab, setActiveTab] = useState<'distribution' | 'validation' | 'sensitivity'>('distribution')

  useEffect(() => {
    fetchStats()
    if (!autoRefresh) return
    const interval = setInterval(fetchStats, 10000)
    return () => clearInterval(interval)
  }, [autoRefresh])

  const fetchStats = async () => {
    try {
      setLoading(true)
      const res = await fetch('/api/academic/kpi-statistics')
      if (res.ok) {
        const data = await res.json()
        setStats(data)
      }
    } catch (e) {
      console.error('Failed to fetch academic stats:', e)
    }
    setLoading(false)
  }

  if (!stats) {
    return (
      <Card className="p-4">
        <div className="flex items-center justify-center h-32 text-gray-500 text-sm">
          等待统计数据...
        </div>
      </Card>
    )
  }

  // 延迟分布直方图
  const delayHistogramOption = stats.delay_analysis?.per_ship?.histogram ? {
    tooltip: {
      trigger: 'axis' as const,
      backgroundColor: 'rgba(10, 25, 47, 0.9)',
      textStyle: { color: '#fff', fontSize: 11 },
    },
    grid: { top: 24, right: 12, bottom: 20, left: 50 },
    xAxis: {
      type: 'category' as const,
      data: (stats.delay_analysis.per_ship.histogram as HistogramBin[]).map(
        (b: HistogramBin) => `${(b.bin_start as number).toFixed(0)}-${(b.bin_end as number).toFixed(0)}`
      ),
      axisLabel: { color: '#9CA3AF', fontSize: 9, rotate: 30 },
      axisLine: { lineStyle: { color: '#4B5563' } },
    },
    yAxis: {
      type: 'value' as const,
      name: '船舶数',
      nameTextStyle: { color: '#9CA3AF', fontSize: 10 },
      axisLabel: { color: '#9CA3AF', fontSize: 10 },
      splitLine: { lineStyle: { color: '#374151' } },
    },
    series: [{
      type: 'bar',
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      data: (stats.delay_analysis.per_ship.histogram as any[]).map((b: HistogramBin) => b.count),
      itemStyle: {
        color: { type: 'linear', x: 0, y: 0, x2: 0, y2: 1, colorStops: [
          { offset: 0, color: '#F59E0B' },
          { offset: 1, color: 'rgba(245,158,11,0.2)' },
        ]} as any,
        borderRadius: [3, 3, 0, 0],
      },
    }],
  } : null

  // 延迟箱线图
  const delayBoxplotOption = stats.delay_analysis?.per_ship?.boxplot ? {
    tooltip: {
      trigger: 'item' as const,
      backgroundColor: 'rgba(10, 25, 47, 0.9)',
      textStyle: { color: '#fff', fontSize: 11 },
    },
    grid: { top: 24, right: 12, bottom: 20, left: 50 },
    xAxis: {
      type: 'category' as const,
      data: ['延误分布'],
      axisLabel: { color: '#9CA3AF', fontSize: 10 },
      axisLine: { lineStyle: { color: '#4B5563' } },
    },
    yAxis: {
      type: 'value' as const,
      name: '小时',
      nameTextStyle: { color: '#9CA3AF', fontSize: 10 },
      axisLabel: { color: '#9CA3AF', fontSize: 10 },
      splitLine: { lineStyle: { color: '#374151' } },
    },
    series: [{
      type: 'boxplot',
      data: [[
        stats.delay_analysis.per_ship.boxplot.min,
        stats.delay_analysis.per_ship.boxplot.q1,
        stats.delay_analysis.per_ship.boxplot.median,
        stats.delay_analysis.per_ship.boxplot.q3,
        stats.delay_analysis.per_ship.boxplot.max,
      ]],
      itemStyle: { color: '#3B82F6' },
      lineStyle: { color: '#60A5FA' },
    }],
  } : null

  return (
    <div className="space-y-3">
      {/* 选项卡 */}
      <div className="flex gap-1 border-b border-white/10 pb-2">
        {[
          { id: 'distribution', label: '分布分析' },
          { id: 'validation', label: '统计推断' },
          { id: 'sensitivity', label: '敏感性' },
        ].map(tab => (
          <button
            key={tab.id}
            onClick={() => setActiveTab(tab.id as any)}
            className={`px-3 py-1.5 text-xs rounded-t transition-colors ${
              activeTab === tab.id
                ? 'text-marine-400 border-b-2 border-marine-500 bg-marine-500/10'
                : 'text-gray-500 hover:text-gray-300'
            }`}
          >
            {tab.label}
          </button>
        ))}
      </div>

      {/* 分布分析 */}
      {activeTab === 'distribution' && (
        <div className="grid grid-cols-2 gap-3">
          <div>
            <h4 className="text-xs text-gray-400 mb-2 flex items-center gap-1">
              <span className="w-1.5 h-1.5 rounded-full bg-yellow-400" />
              延误分布直方图
            </h4>
            <div className="h-40">
              {delayHistogramOption && (
                <ReactECharts option={delayHistogramOption} style={{ width: '100%', height: '100%' }} />
              )}
            </div>
          </div>
          <div>
            <h4 className="text-xs text-gray-400 mb-2 flex items-center gap-1">
              <span className="w-1.5 h-1.5 rounded-full bg-blue-400" />
              延误箱线图
            </h4>
            <div className="h-40">
              {delayBoxplotOption && (
                <ReactECharts option={delayBoxplotOption} style={{ width: '100%', height: '100%' }} />
              )}
            </div>
          </div>
          {/* 统计摘要 */}
          <div className="col-span-2 grid grid-cols-4 gap-2">
            <div className="bg-white/5 rounded p-2">
              <div className="text-[10px] text-gray-500">延误均值</div>
              <div className="text-sm font-bold text-white">{stats.delay_analysis.descriptive.mean}h</div>
            </div>
            <div className="bg-white/5 rounded p-2">
              <div className="text-[10px] text-gray-500">最大延误</div>
              <div className="text-sm font-bold text-red-400">{stats.delay_analysis.descriptive.max}h</div>
            </div>
            <div className="bg-white/5 rounded p-2">
              <div className="text-[10px] text-gray-500">延误方差</div>
              <div className="text-sm font-bold text-yellow-400">{stats.delay_analysis.descriptive.variance}</div>
            </div>
            <div className="bg-white/5 rounded p-2">
              <div className="text-[10px] text-gray-500">正态性(p)</div>
              <div className="text-sm font-bold text-cyan-400">
                {stats.normality?.delays?.p_value?.toFixed(3) ?? '-'}
              </div>
            </div>
          </div>
        </div>
      )}

      {/* 统计推断 */}
      {activeTab === 'validation' && (
        <div className="space-y-2">
          {/* 置信区间 */}
          <div>
            <h4 className="text-xs text-gray-400 mb-1">延误均值 95% 置信区间</h4>
            <div className="bg-white/5 rounded p-3">
              <div className="flex items-center justify-between mb-1">
                <span className="text-xs text-gray-400">准班率趋势</span>
                <span className="text-xs text-gray-400">
                  [{stats.on_time_rate_trend?.descriptive?.ci_lower_95?.toFixed(1) ?? '-'}%,
                  {stats.on_time_rate_trend?.descriptive?.ci_upper_95?.toFixed(1) ?? '-'}%]
                </span>
              </div>
              {/* CI 可视化条 */}
              {stats.on_time_rate_trend?.descriptive && (() => {
                const d = stats.on_time_rate_trend!.descriptive!
                const low95 = d.ci_lower_95 ?? 0
                const high95 = d.ci_upper_95 ?? 1
                const divisor = high95 * 1.2
                return (
                  <div className="h-2 bg-gray-700 rounded-full overflow-hidden relative">
                    <div
                      className="h-full bg-gradient-to-r from-blue-500 to-cyan-400 rounded-full absolute"
                      style={{
                        left: `${Math.max(0, low95 / divisor * 100)}%`,
                        width: `${Math.min(100, (high95 - low95) / divisor * 100)}%`,
                      }}
                    />
                    <div
                      className="h-full w-1 bg-white rounded-full absolute"
                      style={{
                        left: `${(d.mean / divisor * 100)}%`,
                      }}
                    />
                  </div>
                )
              })()}
            </div>
          </div>
          {/* 状态分布 */}
          <div>
            <h4 className="text-xs text-gray-400 mb-1">船舶状态分布</h4>
            <div className="flex gap-1">
              {Object.entries(stats.state_distribution || {}).map(([state, count]: [string, any]) => {
                const colorMap: Record<string, string> = {
                  SAILING: '#3B82F6',
                  WAITING: '#EF4444',
                  BERTHING: '#10B981',
                  ARRIVING: '#F59E0B',
                  IDLE: '#9CA3AF',
                  DEPARTING: '#8B5CF6',
                }
                const total = Object.values(stats.state_distribution as Record<string, number>).reduce((a: number, b: number) => a + b, 0)
                return (
                  <div
                    key={state}
                    className="flex-1 h-8 rounded flex items-center justify-center text-xs font-medium text-white relative overflow-hidden"
                    style={{ backgroundColor: colorMap[state] || '#6B7280' }}
                  >
                    <span className="relative z-10">{count as number}</span>
                    {total > 0 && (
                      <div
                        className="absolute inset-0 bg-black/20"
                        style={{ width: `${(1 - (count as number) / total) * 100}%`, marginLeft: 'auto' }}
                      />
                    )}
                  </div>
                )
              })}
            </div>
          </div>
        </div>
      )}

      {/* 敏感性 */}
      {activeTab === 'sensitivity' && (
        <div className="space-y-2">
          <div className="flex gap-1 flex-wrap">
            {stats.port_queues && Object.entries(stats.port_queues).map(([portId, queue]: [string, any]) => (
              <Badge
                key={portId}
                variant={(queue as number) > 2 ? 'warning' : 'info'}
                size="sm"
              >
                {portId}: {(queue as number)}艘
              </Badge>
            ))}
          </div>
          <div className="text-xs text-gray-500">
            <div>跟踪船舶: {stats.ships_tracked} 艘</div>
            <div>快照数: {stats.snapshots_count}</div>
            <div>碳排放总量: {stats.carbon_analysis?.total?.toFixed(0) ?? '-'} t</div>
          </div>
        </div>
      )}
    </div>
  )
}
