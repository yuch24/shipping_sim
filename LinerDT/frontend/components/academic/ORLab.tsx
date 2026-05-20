'use client'

import { useState, useEffect } from 'react'

interface Props {
  onOpenResult?: (title: string, content: React.ReactNode) => void
}

const MODELS = [
  { id: 'fleet', name: '航线配船 (Fleet Deployment)', desc: '给定航线需求，优化船队配置与航速，最小化总运营成本' },
  { id: 'bap', name: '泊位分配 (Berth Allocation)', desc: '优化船舶到港后的泊位分配，最小化等待时间与操作成本' },
  { id: 'speed', name: '航速优化 (Slow Steaming)', desc: '在CII约束下优化各航段航速，平衡燃油成本与准班率' },
]

export default function ORLab({ onOpenResult }: Props) {
  const [selectedModel, setSelectedModel] = useState<string | null>(null)
  const [solving, setSolving] = useState(false)
  const [solverInfo, setSolverInfo] = useState('')
  const [solved, setSolved] = useState(false)

  useEffect(() => {
    fetch('/api/academic-lab/or/models')
      .then(r => r.json())
      .then(data => setSolverInfo(data.solver || ''))
      .catch(() => setSolverInfo('unknown'))
  }, [])

  const handleSolve = async () => {
    if (!selectedModel) return
    setSolving(true)
    try {
      const res = await fetch('/api/academic-lab/or/solve', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          model_id: selectedModel,
          params: {
            speed_range: [12, 22],
            fuel_price: 580,
            cii_target: 'C',
            delay_penalty: 500,
            time_horizon: 30,
            time_limit: 60,
          },
        }),
      })
      const data = await res.json()
      setSolved(true)

      // 浮动窗口显示求解结果
      if (onOpenResult) {
        onOpenResult(`${MODELS.find(m => m.id === selectedModel)?.name} — 求解结果`, (
          <div className="space-y-3">
            <div className="grid grid-cols-2 gap-2">
              <ResultBadge label="状态" value={data.status} color="purple" />
              <ResultBadge label="求解器" value={data.solver || 'scipy'} color="blue" />
              <ResultBadge label="最优航速" value={`${data.optimal_speed ?? '-'} kn`} color="green" />
              <ResultBadge label="总成本" value={`$${(data.total_cost ?? 0).toLocaleString()}`} color="amber" />
              <ResultBadge label="燃油成本" value={`$${(data.fuel_cost ?? 0).toLocaleString()}`} color="orange" />
              <ResultBadge label="延误成本" value={`$${(data.delay_cost ?? 0).toLocaleString()}`} color="red" />
            </div>
            {data.segments && (
              <div>
                <div className="text-xs text-gray-500 mb-1">各航段航速分布</div>
                <div className="flex gap-0.5 h-16 items-end">
                  {data.segments.map((s: number, i: number) => (
                    <div key={i} className="flex-1 flex flex-col items-center gap-0.5">
                      <div
                        className="w-full rounded-t bg-marine-500/60 transition-all"
                        style={{ height: `${(s - 10) / 15 * 100}%`, minHeight: 4 }}
                        title={`Seg ${i+1}: ${s} kn`}
                      />
                      <span className="text-[8px] text-gray-600">S{i+1}</span>
                    </div>
                  ))}
                </div>
              </div>
            )}
            {data.schedule && (
              <div className="text-xs text-gray-400">
                <div>总船舶: {data.total_ships} · 完工时间: {data.makespan}h</div>
                <div>总等待: {data.total_waiting}h · 泊位利用率: {data.berth_utilization?.join(', ')}%</div>
              </div>
            )}
          </div>
        ))
      }
    } catch { /* ignore */ }
    setSolving(false)
  }

  return (
    <div className="h-full overflow-auto p-4">
      <div className="max-w-4xl mx-auto space-y-4">
        <div>
          <h3 className="text-xs font-medium text-gray-400 mb-2 flex items-center gap-1.5">
            <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19.428 15.428a2 2 0 00-1.022-.547l-2.387-.477a6 6 0 00-3.86.517l-.318.158a6 6 0 01-3.86.517L6.05 15.21a2 2 0 00-1.806.547M8 4h8l-1 1v5.172a2 2 0 00.586 1.414l5 5c1.26 1.26.367 3.414-1.415 3.414H4.828c-1.782 0-2.674-2.154-1.414-3.414l5-5A2 2 0 009 10.172V5L8 4z" />
            </svg>
            运筹学模型库
          </h3>
          <div className="grid grid-cols-3 gap-2">
            {MODELS.map((m) => (
              <button
                key={m.id}
                onClick={() => { setSelectedModel(m.id); setSolved(false) }}
                className={`text-left p-3 rounded-lg border transition-all ${
                  selectedModel === m.id
                    ? 'bg-marine-500/10 border-marine-500/30'
                    : 'bg-white/5 border-white/10 hover:border-white/20'
                }`}
              >
                <p className="text-xs font-medium text-gray-300">{m.name}</p>
                <p className="text-[10px] text-gray-500 mt-1">{m.desc}</p>
              </button>
            ))}
          </div>
        </div>

        {selectedModel && (
          <>
            <div className="bg-white/5 rounded-lg border border-white/10 p-4 space-y-3">
              <h3 className="text-xs font-medium text-gray-400">参数配置</h3>
              <div className="grid grid-cols-3 gap-2">
                {[
                  { label: '航速范围 (kn)', value: '12 — 22' },
                  { label: '燃油价格 ($/t)', value: '580' },
                  { label: '延误惩罚 ($/h)', value: '500' },
                  { label: 'CII 目标', value: 'A 级' },
                  { label: '时间范围 (天)', value: '30' },
                  { label: '求解时限 (s)', value: '60' },
                ].map((p) => (
                  <div key={p.label} className="flex items-center justify-between bg-white/5 rounded px-3 py-1.5">
                    <span className="text-[10px] text-gray-500">{p.label}</span>
                    <span className="text-[11px] text-gray-300 font-mono">{p.value}</span>
                  </div>
                ))}
              </div>
              <div className="flex items-center gap-3 pt-1">
                <button
                  onClick={handleSolve}
                  disabled={solving}
                  className="px-4 py-1.5 text-xs font-medium bg-marine-500 hover:bg-marine-400 disabled:bg-gray-700 disabled:text-gray-500 text-white rounded-lg transition-colors"
                >
                  {solving ? (
                    <span className="flex items-center gap-1.5">
                      <svg className="w-3 h-3 animate-spin" viewBox="0 0 24 24" fill="none">
                        <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                        <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
                      </svg>
                      求解中...
                    </span>
                  ) : '▶ 求解'}
                </button>
                <span className="text-[10px] text-gray-600">
                  求解器: <span className="text-gray-500">{solverInfo || '检测中...'}</span>
                </span>
              </div>
            </div>

            {solved && (
              <div className="bg-white/5 rounded-lg border border-white/10 p-4">
                <h3 className="text-xs font-medium text-gray-400 mb-2">求解结果</h3>
                <div className="flex items-center justify-center h-12 text-[11px] text-gray-500">
                  结果已弹出浮动窗口
                  <svg className="w-3.5 h-3.5 ml-1.5 text-marine-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" />
                  </svg>
                </div>
              </div>
            )}
          </>
        )}
      </div>
    </div>
  )
}

function ResultBadge({ label, value, color }: { label: string; value: string; color: string }) {
  const colorMap: Record<string, string> = {
    purple: 'bg-purple-500/10 text-purple-400',
    blue: 'bg-blue-500/10 text-blue-400',
    green: 'bg-green-500/10 text-green-400',
    amber: 'bg-amber-500/10 text-amber-400',
    orange: 'bg-orange-500/10 text-orange-400',
    red: 'bg-red-500/10 text-red-400',
  }
  return (
    <div className="bg-white/5 rounded px-3 py-2">
      <div className="text-[10px] text-gray-500">{label}</div>
      <div className={`text-xs font-mono font-medium mt-0.5 ${colorMap[color] || 'text-gray-300'}`}>{value}</div>
    </div>
  )
}
