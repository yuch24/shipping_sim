'use client'

import { useState, useEffect, useCallback } from 'react'

interface ToolBinding {
  tool_id: string
  enabled: boolean
  params: Record<string, number>
}

interface AgentConfig {
  id: string
  name: string
  description: string
  category: string
  enabled: boolean
  decision_mode: string
  system_prompt: string
  tools: ToolBinding[]
  parameters: Record<string, number>
}

const CATEGORY_LABELS: Record<string, string> = {
  speed_optimization: '航速优化',
  cii_protection: '排放约束',
}

const CATEGORY_COLORS: Record<string, string> = {
  speed_optimization: 'border-l-blue-500',
  cii_protection: 'border-l-green-500',
}

const DECISION_MODE_LABELS: Record<string, string> = {
  fast: '快速路径（公式）',
  llm: 'LLM 智能决策',
}

const TOOL_LABELS: Record<string, string> = {
  get_cii_status: 'CII 状态查询',
  get_delay_info: '延误信息查询',
  get_port_queue_info: '港口排队查询',
  check_cooldown: '冷却检查',
  calculate_optimal_speed: '最优航速计算',
  evaluate_tradeoff: '多目标权衡评分',
  adjust_speed: '执行航速调整',
}

export default function AgentConfigEditor() {
  const [configs, setConfigs] = useState<AgentConfig[]>([])
  const [localConfigs, setLocalConfigs] = useState<AgentConfig[]>([])
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [dirty, setDirty] = useState(false)
  const [expandedId, setExpandedId] = useState<string | null>(null)

  const fetchConfigs = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const res = await fetch('/api/ai/agents')
      const data = await res.json()
      if (data.agents) {
        setConfigs(data.agents)
        setLocalConfigs(JSON.parse(JSON.stringify(data.agents)))
      }
    } catch {
      setError('加载 Agent 配置失败')
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    fetchConfigs()
  }, [fetchConfigs])

  const updateLocal = (configId: string, updater: (c: AgentConfig) => AgentConfig) => {
    setLocalConfigs(prev =>
      prev.map(c => (c.id === configId ? updater(c) : c))
    )
    setDirty(true)
  }

  const handleSave = async () => {
    setSaving(true)
    setError(null)
    try {
      for (const local of localConfigs) {
        const original = configs.find(c => c.id === local.id)
        if (!original) continue

        // Build patch object
        const patch: Record<string, any> = {}
        if (local.enabled !== original.enabled) patch.enabled = local.enabled
        if (local.decision_mode !== original.decision_mode) patch.decision_mode = local.decision_mode
        if (local.system_prompt !== original.system_prompt) patch.system_prompt = local.system_prompt

        const paramsChanged = Object.keys(local.parameters).some(
          k => local.parameters[k] !== original.parameters[k]
        )
        if (paramsChanged) patch.parameters = { ...local.parameters }

        const toolsChanged = local.tools.some(
          (t, i) => t.enabled !== original.tools[i]?.enabled
        )
        if (toolsChanged) {
          patch.tools = local.tools.map(t => ({ tool_id: t.tool_id, enabled: t.enabled }))
        }

        if (Object.keys(patch).length === 0) continue

        const res = await fetch(`/api/ai/agents/${local.id}`, {
          method: 'PUT',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(patch),
        })
        if (!res.ok) throw new Error(`更新 ${local.name} 失败`)
      }
      setConfigs(JSON.parse(JSON.stringify(localConfigs)))
      setDirty(false)
    } catch (e: any) {
      setError(e.message || '保存失败')
    } finally {
      setSaving(false)
    }
  }

  const handleReset = async () => {
    if (!confirm('确定要重置所有 Agent 配置为默认值吗？')) return
    setSaving(true)
    setError(null)
    try {
      const res = await fetch('/api/ai/agents/reset', { method: 'POST' })
      const data = await res.json()
      if (data.agents) {
        setConfigs(data.agents)
        setLocalConfigs(JSON.parse(JSON.stringify(data.agents)))
        setDirty(false)
      }
    } catch {
      setError('重置失败')
    } finally {
      setSaving(false)
    }
  }

  return (
    <div className="space-y-2 px-4 py-3">
      {/* 标题栏 */}
      <div className="flex items-center justify-between mb-2">
        <h3 className="text-xs font-semibold text-cyan-400 uppercase tracking-wider">
          Agent 配置
        </h3>
        <div className="flex gap-1.5">
          <button
            onClick={handleReset}
            disabled={saving}
            className="px-2 py-1 rounded text-[10px] font-medium border border-white/10 text-gray-400 hover:text-red-400 hover:border-red-500/30 transition-colors disabled:opacity-50"
          >
            重置默认
          </button>
          <button
            onClick={fetchConfigs}
            disabled={loading}
            className="px-2 py-1 rounded text-[10px] font-medium border border-white/10 text-gray-400 hover:text-white transition-colors disabled:opacity-50"
          >
            刷新
          </button>
        </div>
      </div>

      {error && (
        <div className="bg-red-500/10 border border-red-500/30 rounded-lg px-3 py-2 text-xs text-red-400">
          {error}
        </div>
      )}

      {loading ? (
        <div className="flex items-center justify-center py-8">
          <div className="w-5 h-5 border-2 border-cyan-500 border-t-transparent rounded-full animate-spin" />
          <span className="ml-2 text-xs text-gray-500">加载配置...</span>
        </div>
      ) : (
        <>
          {/* Agent 卡片列表 */}
          <div className="space-y-1.5 max-h-[400px] overflow-y-auto">
            {localConfigs.map(config => {
              const isExpanded = expandedId === config.id
              return (
                <div
                  key={config.id}
                  className={`border-l-2 ${CATEGORY_COLORS[config.category] || 'border-l-gray-500'} bg-white/[0.02] rounded-r-lg transition-colors ${
                    !config.enabled ? 'opacity-50' : ''
                  }`}
                >
                  {/* 卡片头 */}
                  <div
                    className="flex items-center justify-between px-3 py-2 cursor-pointer hover:bg-white/[0.04] rounded-r-lg"
                    onClick={() => setExpandedId(isExpanded ? null : config.id)}
                  >
                    <div className="flex items-center gap-2 min-w-0">
                      <span className="text-xs font-medium text-gray-200 truncate">{config.name}</span>
                      <span className="text-[10px] px-1.5 py-0.5 rounded-full bg-white/5 text-gray-500 shrink-0">
                        {CATEGORY_LABELS[config.category] || config.category}
                      </span>
                      <span className={`text-[10px] px-1.5 py-0.5 rounded-full shrink-0 ${
                        config.decision_mode === 'llm'
                          ? 'bg-purple-500/10 text-purple-400'
                          : 'bg-marine-500/10 text-marine-400'
                      }`}>
                        {DECISION_MODE_LABELS[config.decision_mode] || config.decision_mode}
                      </span>
                    </div>
                    <div className="flex items-center gap-2 shrink-0" onClick={e => e.stopPropagation()}>
                      <label className="relative inline-flex items-center cursor-pointer">
                        <input
                          type="checkbox"
                          checked={config.enabled}
                          onChange={() => updateLocal(config.id, c => ({ ...c, enabled: !c.enabled }))}
                          className="sr-only peer"
                          aria-label={`${config.enabled ? '禁用' : '启用'} ${config.name}`}
                        />
                        <div className="w-7 h-3.5 rounded-full bg-white/10 peer-checked:bg-cyan-600 transition-colors after:content-[''] after:absolute after:top-0.5 after:left-0.5 after:bg-white after:rounded-full after:h-2.5 after:w-2.5 after:transition-all peer-checked:after:translate-x-3.5" />
                      </label>
                      <svg
                        className={`w-3.5 h-3.5 text-gray-500 transition-transform ${isExpanded ? 'rotate-180' : ''}`}
                        fill="none" viewBox="0 0 24 24" stroke="currentColor"
                      >
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
                      </svg>
                    </div>
                  </div>

                  {/* 展开详细编辑区 */}
                  {isExpanded && (
                    <div className="px-3 pb-3 space-y-3 border-t border-white/5 pt-2">
                      <p className="text-[10px] text-gray-500 leading-relaxed">{config.description}</p>

                      {/* 决策模式切换 */}
                      <div>
                        <label className="text-[10px] text-gray-400 mb-1 block">决策模式</label>
                        <div className="flex gap-2">
                          {(['fast', 'llm'] as const).map(mode => (
                            <button
                              key={mode}
                              onClick={() => updateLocal(config.id, c => ({ ...c, decision_mode: mode }))}
                              className={`px-3 py-1 rounded text-[10px] font-medium transition-colors ${
                                config.decision_mode === mode
                                  ? mode === 'llm'
                                    ? 'bg-purple-500/20 text-purple-400 border border-purple-500/30'
                                    : 'bg-marine-500/20 text-marine-400 border border-marine-500/30'
                                  : 'bg-white/5 text-gray-500 border border-white/5 hover:text-gray-300'
                              }`}
                            >
                              {DECISION_MODE_LABELS[mode]}
                            </button>
                          ))}
                        </div>
                      </div>

                      {/* System Prompt */}
                      <div>
                        <label className="text-[10px] text-gray-400 mb-1 block">System Prompt</label>
                        <textarea
                          value={config.system_prompt}
                          onChange={e => updateLocal(config.id, c => ({ ...c, system_prompt: e.target.value }))}
                          rows={4}
                          className="w-full bg-white/5 border border-white/10 rounded-lg px-3 py-2 text-[10px] text-gray-200 leading-relaxed font-mono focus:outline-none focus:border-cyan-500/50 resize-y"
                        />
                      </div>

                      {/* 工具列表 */}
                      <div>
                        <label className="text-[10px] text-gray-400 mb-1.5 block">可用工具</label>
                        <div className="space-y-1">
                          {config.tools.map(tool => (
                            <label
                              key={tool.tool_id}
                              className="flex items-center justify-between cursor-pointer hover:bg-white/5 px-2 py-1.5 rounded-md transition-colors"
                            >
                              <span className="text-[10px] text-gray-300">
                                {TOOL_LABELS[tool.tool_id] || tool.tool_id}
                              </span>
                              <input
                                type="checkbox"
                                checked={tool.enabled}
                                onChange={() => updateLocal(config.id, c => ({
                                  ...c,
                                  tools: c.tools.map(t =>
                                    t.tool_id === tool.tool_id ? { ...t, enabled: !t.enabled } : t
                                  ),
                                }))}
                                className="sr-only peer"
                              />
                              <div className="w-7 h-3.5 rounded-full bg-white/10 peer-checked:bg-cyan-600 transition-colors after:content-[''] after:absolute after:top-0.5 after:left-0.5 after:bg-white after:rounded-full after:h-2.5 after:w-2.5 after:transition-all peer-checked:after:translate-x-3.5" />
                            </label>
                          ))}
                        </div>
                      </div>

                      {/* 参数编辑 */}
                      {Object.keys(config.parameters).length > 0 && (
                        <div>
                          <label className="text-[10px] text-gray-400 mb-1.5 block">参数</label>
                          <div className="grid grid-cols-2 gap-1.5">
                            {Object.entries(config.parameters).map(([key, value]) => (
                              <div key={key} className="bg-white/[0.03] rounded-md px-2 py-1.5">
                                <div className="text-[9px] text-gray-600 mb-0.5 truncate">{key}</div>
                                <input
                                  type="number"
                                  value={value}
                                  step="any"
                                  onChange={e => updateLocal(config.id, c => ({
                                    ...c,
                                    parameters: {
                                      ...c.parameters,
                                      [key]: parseFloat(e.target.value) || 0,
                                    },
                                  }))}
                                  className="w-full bg-white/5 border border-white/10 rounded px-1.5 py-0.5 text-[10px] text-gray-200 font-mono text-right focus:outline-none focus:border-cyan-500/50"
                                />
                              </div>
                            ))}
                          </div>
                        </div>
                      )}
                    </div>
                  )}
                </div>
              )
            })}
          </div>

          {/* 保存按钮 */}
          <button
            onClick={handleSave}
            disabled={!dirty || saving}
            className={`w-full py-2 rounded-lg text-xs font-medium transition-all ${
              dirty
                ? 'bg-cyan-600 hover:bg-cyan-500 text-white'
                : 'bg-white/5 text-gray-600 cursor-not-allowed'
            }`}
          >
            {saving ? (
              <span className="flex items-center justify-center gap-2">
                <div className="w-3 h-3 border-2 border-white border-t-transparent rounded-full animate-spin" />
                保存中...
              </span>
            ) : dirty ? (
              '保存变更'
            ) : (
              '已是最新'
            )}
          </button>
        </>
      )}
    </div>
  )
}
