'use client'

import { useState, useEffect } from 'react'

interface Props {
  onOpenResult?: (title: string, content: React.ReactNode) => void
}

const TASKS = [
  { id: 'eta', name: 'ETA 预测', desc: '基于航行历史预测船舶到港时间' },
  { id: 'congestion', name: '港口拥堵预测', desc: '预测港口队列长度与等待时间' },
  { id: 'fuel', name: '燃油消耗预测', desc: '基于航速/载重/海况预测油耗' },
  { id: 'cii', name: 'CII 评级预测', desc: '预测船舶年度 CII 评级变化趋势' },
]

export default function MLLab({ onOpenResult }: Props) {
  const [selectedTask, setSelectedTask] = useState<string | null>(null)
  const [training, setTraining] = useState(false)
  const [taskInfo, setTaskInfo] = useState<any[]>([])

  useEffect(() => {
    fetch('/api/academic-lab/ml/tasks')
      .then(r => r.json())
      .then(data => setTaskInfo(data.tasks || []))
      .catch(() => {})
  }, [])

  const handleTrain = async () => {
    if (!selectedTask) return
    setTraining(true)
    try {
      const res = await fetch('/api/academic-lab/ml/train', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ task_id: selectedTask }),
      })
      const data = await res.json()

      if (onOpenResult) {
        onOpenResult(`${TASKS.find(t => t.id === selectedTask)?.name} — 训练结果`, (
          <div className="space-y-3">
            <div className="grid grid-cols-2 gap-2">
              <div className="bg-white/5 rounded px-3 py-2">
                <div className="text-[10px] text-gray-500">模型</div>
                <div className="text-xs text-gray-300 mt-0.5">{data.model_type || 'RandomForest'}</div>
              </div>
              <div className="bg-white/5 rounded px-3 py-2">
                <div className="text-[10px] text-gray-500">样本数</div>
                <div className="text-xs text-gray-300 mt-0.5">{data.metrics?.samples ?? '-'}</div>
              </div>
              {data.metrics?.r2_score !== undefined && (
                <div className="bg-white/5 rounded px-3 py-2">
                  <div className="text-[10px] text-gray-500">R² Score</div>
                  <div className="text-xs text-green-400 mt-0.5">{data.metrics.r2_score}</div>
                </div>
              )}
              {data.metrics?.mae !== undefined && (
                <div className="bg-white/5 rounded px-3 py-2">
                  <div className="text-[10px] text-gray-500">MAE</div>
                  <div className="text-xs text-amber-400 mt-0.5">{data.metrics.mae}</div>
                </div>
              )}
              {data.metrics?.accuracy !== undefined && (
                <div className="bg-white/5 rounded px-3 py-2">
                  <div className="text-[10px] text-gray-500">准确率</div>
                  <div className="text-xs text-green-400 mt-0.5">{(data.metrics.accuracy * 100).toFixed(1)}%</div>
                </div>
              )}
            </div>

            {/* 特征重要性 */}
            {data.feature_importance && data.feature_importance.length > 0 && (
              <div>
                <div className="text-xs text-gray-500 mb-1.5">特征重要性</div>
                <div className="space-y-1">
                  {data.feature_importance.map((f: any, i: number) => (
                    <div key={i} className="flex items-center gap-2">
                      <span className="text-[10px] text-gray-400 w-20 shrink-0">{f.name}</span>
                      <div className="flex-1 h-3 bg-white/5 rounded-full overflow-hidden">
                        <div
                          className="h-full rounded-full bg-gradient-to-r from-marine-500 to-marine-400"
                          style={{ width: `${Math.min(100, f.importance * 100)}%` }}
                        />
                      </div>
                      <span className="text-[10px] text-gray-500 w-10 text-right">{f.importance.toFixed(2)}</span>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {data.metrics?.note && (
              <div className="text-[10px] text-gray-600 bg-amber-500/5 rounded px-3 py-2 border border-amber-500/20">
                ⚡ {data.metrics.note}
              </div>
            )}
          </div>
        ))
      }
    } catch { /* ignore */ }
    setTraining(false)
  }

  return (
    <div className="h-full overflow-auto p-4">
      <div className="max-w-4xl mx-auto space-y-4">
        <div>
          <h3 className="text-xs font-medium text-gray-400 mb-2 flex items-center gap-1.5">
            <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9.75 17L9 20l-1 1h8l-1-1-.75-3M3 13h18M5 17h14a2 2 0 002-2V5a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z" />
            </svg>
            预测任务
          </h3>
          <div className="grid grid-cols-4 gap-2">
            {TASKS.map((t) => (
              <button
                key={t.id}
                onClick={() => setSelectedTask(t.id)}
                className={`p-3 rounded-lg border transition-all text-left ${
                  selectedTask === t.id
                    ? 'bg-marine-500/10 border-marine-500/30'
                    : 'bg-white/5 border-white/10 hover:border-white/20'
                }`}
              >
                <p className="text-xs font-medium text-gray-300">{t.name}</p>
                <p className="text-[10px] text-gray-500 mt-0.5">{t.desc}</p>
                <p className="text-[9px] text-gray-600 mt-1">
                  样本: {taskInfo.find((ti: any) => ti.id === t.id)?.sample_count ?? '-'}
                </p>
              </button>
            ))}
          </div>
        </div>

        {selectedTask && (
          <>
            {/* 特征选择 */}
            <div className="bg-white/5 rounded-lg border border-white/10 p-4">
              <h3 className="text-xs font-medium text-gray-400 mb-3">特征配置</h3>
              <div className="flex flex-wrap gap-2">
                {(taskInfo.find((ti: any) => ti.id === selectedTask)?.features ?? [
                  '航速', '载重率', '距下港距离', '历史延误', '港口拥堵度', 'CII评级', '燃油类型'
                ]).map((f: string) => (
                  <label key={f} className="flex items-center gap-1.5 px-2 py-1 bg-white/5 rounded text-[10px] text-gray-400 cursor-pointer hover:bg-white/10 transition-colors">
                    <input type="checkbox" defaultChecked className="w-3 h-3 accent-marine-500" />
                    {f}
                  </label>
                ))}
              </div>
            </div>

            {/* 训练按钮 */}
            <div className="flex items-center gap-2">
              <button
                onClick={handleTrain}
                disabled={training}
                className="px-4 py-1.5 text-xs font-medium bg-marine-500 hover:bg-marine-400 disabled:bg-gray-700 disabled:text-gray-500 text-white rounded-lg transition-colors"
              >
                {training ? (
                  <span className="flex items-center gap-1.5">
                    <svg className="w-3 h-3 animate-spin" viewBox="0 0 24 24" fill="none">
                      <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                      <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
                    </svg>
                    训练中...
                  </span>
                ) : '▶ 训练模型'}
              </button>
              <span className="text-[10px] text-gray-600">算法: Random Forest · sklearn</span>
            </div>

            {/* 提示 */}
            <div className="bg-white/5 rounded-lg border border-white/10 p-4">
              <h3 className="text-xs font-medium text-gray-400 mb-2">模型评估</h3>
              <div className="flex items-center justify-center h-12 text-[11px] text-gray-500">
                训练完成后结果将弹出浮动窗口
              </div>
            </div>
          </>
        )}
      </div>
    </div>
  )
}
