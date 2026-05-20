'use client'

import { useState, useEffect, useCallback } from 'react'

interface ParamDef {
  key: string
  label: string
  type: string
  default?: any
  description?: string
  unit?: string
  min?: number
  max?: number
  step?: number
  options?: { label: string; value: string }[]
  children?: ParamDef[]
  value?: any
}

interface TreeNode {
  name: string
  type: string
  parameters: ParamDef[]
  children: Record<string, TreeNode>
}

interface AgentDetail {
  name: string
  type: string
  path: string
  parent_path: string | null
  parameters: ParamDef[]
  children: Record<string, TreeNode>
  raw_attrs: Record<string, any>
}

function ParamInput({
  paramDef,
  value,
  onChange,
}: {
  paramDef: ParamDef
  value: any
  onChange: (key: string, value: any) => void
}) {
  const currentValue = value ?? paramDef.default

  if (paramDef.type === 'bool') {
    return (
      <label className="relative inline-flex items-center cursor-pointer">
        <input
          type="checkbox"
          checked={!!currentValue}
          onChange={(e) => onChange(paramDef.key, e.target.checked)}
          className="sr-only peer"
        />
        <div className="w-7 h-3.5 rounded-full bg-white/10 peer-checked:bg-cyan-600 transition-colors after:content-[''] after:absolute after:top-0.5 after:left-0.5 after:bg-white after:rounded-full after:h-2.5 after:w-2.5 after:transition-all peer-checked:after:translate-x-3.5" />
      </label>
    )
  }

  if (paramDef.type === 'enum' && paramDef.options?.length) {
    return (
      <select
        value={String(currentValue)}
        onChange={(e) => {
          const opt = (paramDef.options || []).find(o => String(o.value) === e.target.value)
          onChange(paramDef.key, opt?.value ?? e.target.value)
        }}
        className="w-full bg-white/5 border border-white/10 rounded px-1 py-0.5 text-[10px] text-gray-200 font-mono focus:outline-none focus:border-cyan-500/50"
      >
        {paramDef.options.map(opt => (
          <option key={String(opt.value)} value={String(opt.value)}>
            {opt.label}
          </option>
        ))}
      </select>
    )
  }

  if (paramDef.type === 'int' || paramDef.type === 'float' || paramDef.type === 'distribution') {
    return (
      <div className="flex items-center gap-1">
        <input
          type="number"
          value={currentValue ?? ''}
          step={paramDef.step ?? (paramDef.type === 'int' ? 1 : 0.1)}
          min={paramDef.min}
          max={paramDef.max}
          onChange={(e) => {
            const raw = e.target.value
            const val = paramDef.type === 'int' ? parseInt(raw) || 0 : parseFloat(raw) || 0
            onChange(paramDef.key, val)
          }}
          className="w-full bg-white/5 border border-white/10 rounded px-1 py-0.5 text-[10px] text-gray-200 font-mono text-right focus:outline-none focus:border-cyan-500/50"
        />
        {paramDef.unit && (
          <span className="text-[9px] text-gray-600 shrink-0">{paramDef.unit}</span>
        )}
      </div>
    )
  }

  return (
    <input
      type="text"
      value={String(currentValue ?? '')}
      onChange={(e) => onChange(paramDef.key, e.target.value)}
      className="w-full bg-white/5 border border-white/10 rounded px-1 py-0.5 text-[10px] text-gray-200 font-mono focus:outline-none focus:border-cyan-500/50"
    />
  )
}

// ─── 加载骨架屏 ────────────────────────────────

function LoadingSkeleton() {
  return (
    <div className="h-full flex flex-col">
      <div className="flex items-center justify-between px-3 py-2 border-b border-white/5 shrink-0">
        <div className="h-3 w-24 bg-white/5 rounded animate-pulse" />
      </div>
      <div className="flex-1 p-3 space-y-3">
        <div className="h-2.5 w-full bg-white/5 rounded animate-pulse" />
        <div className="h-2.5 w-3/4 bg-white/5 rounded animate-pulse" />
        <div className="h-2.5 w-1/2 bg-white/5 rounded animate-pulse" />
        {[1, 2, 3, 4].map(i => (
          <div key={i} className="flex items-center justify-between py-1">
            <div className="h-2 w-16 bg-white/5 rounded animate-pulse" />
            <div className="h-5 w-20 bg-white/5 rounded animate-pulse" />
          </div>
        ))}
      </div>
    </div>
  )
}

// ─── 空状态 ────────────────────────────────────

function EmptyState() {
  return (
    <div className="h-full flex flex-col items-center justify-center px-6 text-center">
      <svg className="w-8 h-8 text-gray-700 mb-2" fill="none" viewBox="0 0 24 24" stroke="currentColor">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
      </svg>
      <p className="text-[11px] text-gray-600">在 Agent 树面板中选择一个 agent 查看属性</p>
    </div>
  )
}

// ─── Agent 详情面板 ─────────────────────────────

export default function AgentDetailPanel({
  agentPath,
  onClose,
  onRefresh,
}: {
  agentPath: string | null
  onClose: () => void
  onRefresh?: () => void
}) {
  const [detail, setDetail] = useState<AgentDetail | null>(null)
  const [loading, setLoading] = useState(false)
  const [saving, setSaving] = useState(false)

  const fetchDetail = useCallback(async (path: string) => {
    setLoading(true)
    setDetail(null)
    try {
      const res = await fetch(`/api/sim/tree/agent?path=${encodeURIComponent(path)}`)
      const data = await res.json()
      setDetail(data)
    } catch {
      setDetail(null)
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    if (agentPath) {
      fetchDetail(agentPath)
    } else {
      setDetail(null)
    }
  }, [agentPath, fetchDetail])

  const handleParamChange = useCallback(async (key: string, value: any) => {
    if (!agentPath || !detail) return

    // 乐观更新 UI
    setDetail(prev => {
      if (!prev) return prev
      return {
        ...prev,
        parameters: prev.parameters.map(p => ({
          ...p,
          value: p.key === key ? value : p.value,
          children: p.children?.map(c => ({
            ...c,
            value: c.key === key ? value : c.value,
          })),
        })),
      }
    })

    // 直接保存到后端
    setSaving(true)
    try {
      await fetch('/api/sim/tree/parameters', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ path: agentPath, params: { [key]: value } }),
      })
    } catch {
      // 失败时刷新以恢复正确值
      fetchDetail(agentPath)
    } finally {
      setSaving(false)
    }
  }, [agentPath, detail, fetchDetail])

  if (!agentPath) return <EmptyState />
  if (loading) return <LoadingSkeleton />
  if (!detail) return <EmptyState />

  const params = detail.parameters || []
  const children = detail.children || {}
  const leafParams = params.filter(p => !p.children || p.children.length === 0)
  const groups = params.filter(p => p.children && p.children.length > 0)
  const childCount = Object.keys(children).length

  return (
    <div className="h-full flex flex-col">
      {/* 头部 */}
      <div className="flex items-center justify-between px-3 py-2 border-b border-white/5 shrink-0">
        <div className="flex items-center gap-1.5 min-w-0">
          <span className="text-[11px] font-medium text-gray-200 truncate">{detail.name}</span>
          <span className="text-[9px] text-gray-600 truncate">{detail.type}</span>
        </div>
        <div className="flex items-center gap-1">
          {saving && (
            <div className="w-2.5 h-2.5 border border-cyan-500 border-t-transparent rounded-full animate-spin" />
          )}
          <button
            onClick={() => { agentPath && fetchDetail(agentPath); onRefresh?.() }}
            className="p-1 text-gray-500 hover:text-white rounded transition-colors"
            title="刷新"
          >
            <svg className="w-3 h-3" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
            </svg>
          </button>
          <button
            onClick={onClose}
            className="p-1 text-gray-500 hover:text-white rounded transition-colors"
          >
            <svg className="w-3 h-3" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>
      </div>

      <div className="flex-1 overflow-y-auto space-y-2 p-3">
        {/* 路径 */}
        <div className="text-[9px] text-gray-600 font-mono bg-white/[0.02] rounded px-1.5 py-0.5 truncate break-all">
          {detail.path}
        </div>

        {/* 参数组 */}
        {groups.map(group => (
          <div key={group.key}>
            <div className="text-[8px] font-medium text-gray-500 uppercase tracking-wider mb-1 px-0.5">
              {group.label}
            </div>
            <div className="space-y-1">
              {(group.children || []).map(child => (
                <div key={child.key}
                  className="flex items-center justify-between gap-2 py-1 px-1.5 rounded hover:bg-white/[0.04]"
                >
                  <span className="text-[10px] text-gray-400 truncate flex-1">{child.label}</span>
                  <div className="shrink-0" style={{ width: 100 }}>
                    <ParamInput
                      paramDef={child}
                      value={child.value}
                      onChange={(key, val) => handleParamChange(key, val)}
                    />
                  </div>
                </div>
              ))}
            </div>
          </div>
        ))}

        {/* 叶参数 */}
        {leafParams.length > 0 && (
          <div>
            <div className="text-[8px] font-medium text-gray-500 uppercase tracking-wider mb-1 px-0.5">
              参数
            </div>
            <div className="space-y-1">
              {leafParams.map(p => (
                <div key={p.key}
                  className="flex items-center justify-between gap-2 py-1 px-1.5 rounded hover:bg-white/[0.04]"
                >
                  <span className="text-[10px] text-gray-400 truncate flex-1">{p.label}</span>
                  <div className="shrink-0" style={{ width: 100 }}>
                    <ParamInput
                      paramDef={p}
                      value={p.value}
                      onChange={(key, val) => handleParamChange(key, val)}
                    />
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* 运行时属性 */}
        {detail.raw_attrs && Object.keys(detail.raw_attrs).length > 0 && (
          <div>
            <div className="text-[8px] font-medium text-gray-500 uppercase tracking-wider mb-1 px-0.5">
              运行时状态 (只读)
            </div>
            <div className="space-y-0.5">
              {Object.entries(detail.raw_attrs).map(([key, val]) => (
                <div key={key}
                  className="flex items-center justify-between py-0.5 px-1.5 rounded"
                >
                  <span className="text-[9px] text-gray-500 truncate flex-1">{key}</span>
                  <span className="text-[9px] text-gray-400 font-mono shrink-0 ml-2 max-w-[120px] truncate text-right">
                    {typeof val === 'object' ? JSON.stringify(val).slice(0, 30) : String(val)}
                  </span>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* 子节点摘要 */}
        {childCount > 0 && (
          <div>
            <div className="text-[8px] font-medium text-gray-500 uppercase tracking-wider mb-1 px-0.5">
              子节点 ({childCount})
            </div>
            <div className="space-y-0.5">
              {Object.entries(children).map(([name, child]) => (
                <div key={name}
                  className="flex items-center gap-1.5 py-0.5 px-1.5 rounded text-[9px]"
                >
                  <span className="text-gray-400 font-mono truncate">{name}</span>
                  <span className="text-gray-600 truncate">{child.type.split('<').pop()?.replace('>', '') || child.type}</span>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
