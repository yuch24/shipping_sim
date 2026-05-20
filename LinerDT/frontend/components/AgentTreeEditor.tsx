'use client'

import { useState, useEffect, useCallback, useRef } from 'react'

// ─── 类型定义 ─────────────────────────────────────

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

interface AgentTypeInfo {
  type_name: string
  label: string
  description: string
  category: string
  icon: string
  parameters: ParamDef[]
  is_population_compatible: boolean
}

// ─── 参数编辑器 ───────────────────────────────────

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

// ─── 创建 Agent 对话框 ────────────────────────────

function CreateAgentDialog({
  isOpen,
  onClose,
  parentPath,
  parentType,
  agentTypes,
  onCreate,
}: {
  isOpen: boolean
  onClose: () => void
  parentPath: string
  parentType: string
  agentTypes: AgentTypeInfo[]
  onCreate: (payload: {
    parent_path: string
    agent_type: string
    name: string
    display_name?: string
    params: Record<string, any>
  }) => void
}) {
  const [step, setStep] = useState<'type' | 'params'>('type')
  const [selectedType, setSelectedType] = useState<AgentTypeInfo | null>(null)
  const [name, setName] = useState('')
  const [displayName, setDisplayName] = useState('')
  const [paramOverrides, setParamOverrides] = useState<Record<string, any>>({})
  const [creating, setCreating] = useState(false)

  useEffect(() => {
    if (isOpen) {
      setStep('type')
      setSelectedType(null)
      setName('')
      setDisplayName('')
      setParamOverrides({})
      setCreating(false)
    }
  }, [isOpen])

  if (!isOpen) return null

  const leafParams = (selectedType?.parameters || [])
    .filter(p => !p.children || p.children.length === 0)

  const handleCreate = async () => {
    if (!selectedType || !name.trim()) return
    setCreating(true)
    const payload = {
      parent_path: parentPath,
      agent_type: selectedType.type_name,
      name: name.trim(),
      display_name: displayName.trim() || undefined,
      params: paramOverrides,
    }
    await onCreate(payload)
    onClose()
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm">
      <div className="bg-[#0d1e30] border border-white/10 rounded-xl shadow-2xl shadow-black/50 w-[380px] max-h-[560px] flex flex-col">
        {/* 标题栏 */}
        <div className="flex items-center justify-between px-4 py-3 border-b border-white/10 shrink-0">
          <h3 className="text-sm font-medium text-gray-200">
            {step === 'type' ? '选择 Agent 类型' : '配置参数'}
          </h3>
          <button
            onClick={onClose}
            className="p-1 text-gray-500 hover:text-white hover:bg-white/10 rounded transition-colors"
          >
            <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>

        <div className="flex-1 overflow-y-auto p-4 space-y-3">
          {/* 目标位置 */}
          <div className="text-[10px] text-gray-500 bg-white/5 rounded px-2 py-1">
            创建位置: <span className="text-cyan-400 font-mono">{parentPath}</span>
            <span className="text-gray-600 ml-1">({parentType})</span>
          </div>

          {step === 'type' ? (
            /* ─── Step 1: 选择类型 ─── */
            <div className="space-y-1.5">
              {agentTypes.map(at => (
                <button
                  key={at.type_name}
                  onClick={() => { setSelectedType(at); setStep('params') }}
                  className="w-full flex items-center gap-3 px-3 py-2.5 rounded-lg text-left transition-all
                    bg-white/5 hover:bg-white/10 border border-white/5 hover:border-white/10"
                >
                  <span className="text-lg">{at.icon}</span>
                  <div>
                    <div className="text-xs font-medium text-gray-200">{at.label}</div>
                    <div className="text-[10px] text-gray-500">{at.description}</div>
                  </div>
                  <span className="text-[9px] text-gray-600 ml-auto">{at.type_name}</span>
                </button>
              ))}
            </div>
          ) : (
            /* ─── Step 2: 设置名称和参数 ─── */
            <div className="space-y-3">
              <button
                onClick={() => setStep('type')}
                className="flex items-center gap-1 text-[10px] text-gray-500 hover:text-gray-300 transition-colors"
              >
                <svg className="w-3 h-3" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
                </svg>
                返回选择类型
              </button>

              <div className="flex items-center gap-2 pb-2 border-b border-white/5">
                <span className="text-lg">{selectedType?.icon}</span>
                <span className="text-xs font-medium text-gray-200">{selectedType?.label}</span>
              </div>

              {/* Agent 名称 */}
              <div>
                <label className="text-[10px] text-gray-400 mb-1 block">唯一标识 (unique_id)</label>
                <input
                  type="text"
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                  placeholder="例如: s010"
                  className="w-full bg-white/5 border border-white/10 rounded px-2 py-1 text-xs text-gray-200 font-mono focus:outline-none focus:border-cyan-500/50"
                />
              </div>

              <div>
                <label className="text-[10px] text-gray-400 mb-1 block">显示名称 (可选)</label>
                <input
                  type="text"
                  value={displayName}
                  onChange={(e) => setDisplayName(e.target.value)}
                  placeholder="例如: COSCO 星海号"
                  className="w-full bg-white/5 border border-white/10 rounded px-2 py-1 text-xs text-gray-200 focus:outline-none focus:border-cyan-500/50"
                />
              </div>

              {/* 参数覆盖 */}
              {leafParams.length > 0 && (
                <div>
                  <label className="text-[10px] text-gray-400 mb-1 block">参数 (留空使用默认值)</label>
                  <div className="space-y-1.5 max-h-[200px] overflow-y-auto">
                    {leafParams.map(p => (
                      <div key={p.key} className="flex items-center justify-between gap-2 py-0.5">
                        <span className="text-[9px] text-gray-400 truncate flex-1">{p.label}</span>
                        <div className="shrink-0" style={{ width: 100 }}>
                          <ParamInput
                            paramDef={p}
                            value={paramOverrides[p.key]}
                            onChange={(key, val) =>
                              setParamOverrides(prev => ({ ...prev, [key]: val }))
                            }
                          />
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          )}
        </div>

        {/* 底部按钮 */}
        {step === 'params' && (
          <div className="px-4 py-3 border-t border-white/10 shrink-0">
            <button
              onClick={handleCreate}
              disabled={!name.trim() || creating}
              className={`w-full py-2 rounded-lg text-xs font-medium transition-all ${
                name.trim()
                  ? 'bg-cyan-600 hover:bg-cyan-500 text-white'
                  : 'bg-white/5 text-gray-600 cursor-not-allowed'
              }`}
            >
              {creating ? '创建中...' : `创建 ${selectedType?.label || ''}`}
            </button>
          </div>
        )}
      </div>
    </div>
  )
}

// ─── 删除确认对话框 ──────────────────────────────

function DeleteConfirmDialog({
  isOpen,
  onClose,
  agentPath,
  agentName,
  agentType,
  onDelete,
}: {
  isOpen: boolean
  onClose: () => void
  agentPath: string
  agentName: string
  agentType: string
  onDelete: (path: string) => void
}) {
  const [deleting, setDeleting] = useState(false)

  if (!isOpen) return null

  const handleDelete = async () => {
    setDeleting(true)
    await onDelete(agentPath)
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm">
      <div className="bg-[#0d1e30] border border-white/10 rounded-xl shadow-2xl shadow-black/50 w-[360px]">
        <div className="p-4 space-y-3">
          <div className="flex items-center gap-2">
            <div className="w-8 h-8 rounded-full bg-red-500/10 flex items-center justify-center">
              <svg className="w-4 h-4 text-red-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-2.5L13.732 4c-.77-.833-1.964-.833-2.732 0L3.34 16.5c-.77.833.192 2.5 1.732 2.5z" />
              </svg>
            </div>
            <div>
              <h3 className="text-sm font-medium text-gray-200">确认删除</h3>
              <p className="text-[10px] text-gray-500">此操作不可撤销</p>
            </div>
          </div>

          <div className="bg-white/5 rounded-lg px-3 py-2 space-y-1">
            <div className="text-[10px] text-gray-400">
              名称: <span className="text-gray-200 font-mono">{agentName}</span>
            </div>
            <div className="text-[10px] text-gray-400">
              类型: <span className="text-gray-200">{agentType}</span>
            </div>
            <div className="text-[10px] text-gray-400">
              路径: <span className="text-gray-200 font-mono">{agentPath}</span>
            </div>
          </div>

          <p className="text-[10px] text-red-400/80">
            该 agent 的所有子节点（内嵌 agent、population 等）也会被一并删除。
          </p>

          <div className="flex gap-2 pt-1">
            <button
              onClick={onClose}
              disabled={deleting}
              className="flex-1 py-1.5 rounded-lg text-xs font-medium border border-white/10 text-gray-400 hover:text-white transition-colors"
            >
              取消
            </button>
            <button
              onClick={handleDelete}
              disabled={deleting}
              className="flex-1 py-1.5 rounded-lg text-xs font-medium bg-red-600 hover:bg-red-500 text-white transition-colors"
            >
              {deleting ? '删除中...' : '确认删除'}
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}

// ─── 树节点组件 ───────────────────────────────────

function TreeNodeView({
  node,
  nodeValue,
  depth,
  expandedNodes,
  toggleExpand,
  onParamChange,
  onAddAgent,
  onDeleteAgent,
  onSelectAgent,
  selectedPath,
}: {
  node: TreeNode
  nodeValue: Record<string, any>
  depth: number
  expandedNodes: Set<string>
  toggleExpand: (path: string) => void
  onParamChange: (path: string, key: string, value: any) => void
  onAddAgent?: (parentPath: string, parentType: string) => void
  onDeleteAgent?: (path: string, name: string, type: string) => void
  onSelectAgent?: (path: string) => void
  selectedPath?: string | null
}) {
  const leafParams = node.parameters.filter(p => !p.children || p.children.length === 0)
  const groups = node.parameters.filter(p => p.children && p.children.length > 0)
  const hasChildren = Object.keys(node.children).length > 0
  const isExpanded = expandedNodes.has(node.name)
  const isEmpty = leafParams.length === 0 && groups.length === 0 && !hasChildren
  const isPopulation = node.type.startsWith('Population<')
  const isModel = node.type === 'SimulationModel'
  const isEngine = node.type === 'Engine'
  const isSelected = selectedPath?.endsWith(node.name) || selectedPath === node.name

  const typeLabel = isPopulation
    ? `📦 ${node.type}`
    : node.type

  return (
    <div className="group">
      {/* 节点头部 */}
      <div
        className={`flex items-center gap-1 py-1 px-1.5 rounded group/hover cursor-pointer transition-colors
          ${isSelected ? 'bg-cyan-500/10 border-l-2 border-l-cyan-400' : 'hover:bg-white/[0.04] border-l-2 border-l-transparent'}
        `}
      >
        {/* 展开/折叠箭头 */}
        {(hasChildren || groups.length > 0) ? (
          <button
            className={`w-2.5 h-2.5 text-gray-500 transition-transform shrink-0 ${isExpanded ? 'rotate-90' : ''}`}
            onClick={(e) => { e.stopPropagation(); toggleExpand(node.name) }}
            title={isExpanded ? '折叠' : '展开'}
          >
            <svg fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
            </svg>
          </button>
        ) : (
          <span className="w-2.5 shrink-0" />
        )}

        {/* 类型图标 */}
        <span className="text-[10px] shrink-0">
          {node.type.includes('ShipAgent') ? '🚢' :
           node.type.includes('PortAgent') ? '⚓' :
           node.type.includes('CraneAgent') ? '🏗️' :
           node.type.includes('SimulationModel') ? '🧩' :
           node.type.includes('Population') ? '📋' :
           node.type.includes('Engine') ? '⚙️' : '📄'}
        </span>

        {/* 名称（点击选中） */}
        <span
          className={`text-[10px] font-medium truncate ${isSelected ? 'text-cyan-300' : 'text-gray-200'}`}
          onClick={(e) => {
            e.stopPropagation()
            if (!isPopulation && !isModel && !isEngine) {
              onSelectAgent?.(node.name)
            }
          }}
        >
          {node.name}
        </span>

        {/* 类型标签 */}
        <span className="text-[8px] text-gray-600 shrink-0 hidden group-hover:inline">
          {typeLabel.split('.').pop()}
        </span>

        {/* 操作按钮 — hover 显示 */}
        <span className="ml-auto flex items-center gap-0.5 opacity-0 group-hover:opacity-100 transition-opacity">
          {/* 添加按钮 — 仅 Population 或 Model 显示 */}
          {(isPopulation || isModel) && (
            <button
              onClick={(e) => {
                e.stopPropagation()
                onAddAgent?.(node.name, isPopulation ? node.type : node.type)
              }}
              className="w-4 h-4 flex items-center justify-center rounded text-[10px] text-gray-500 hover:text-cyan-400 hover:bg-white/10 transition-colors"
              title="添加 Agent"
            >
              ＋
            </button>
          )}

          {/* 删除按钮 — 不显示在 Engine/Model/Population */}
          {!isPopulation && !isModel && !isEngine && (
            <button
              onClick={(e) => {
                e.stopPropagation()
                onDeleteAgent?.(node.name, node.name, node.type)
              }}
              className="w-4 h-4 flex items-center justify-center rounded text-[10px] text-gray-500 hover:text-red-400 hover:bg-white/10 transition-colors"
              title="删除 Agent"
            >
              <svg className="w-2.5 h-2.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
              </svg>
            </button>
          )}
        </span>

        {/* Agent 数量（Population） */}
        {isPopulation && (
          <span className="text-[9px] px-1.5 py-0.5 rounded-full bg-white/5 text-gray-500">
            {Object.keys(node.children).length}
          </span>
        )}
      </div>

      {/* 展开的子内容 */}
      {isExpanded && (
        <div className="ml-2.5 border-l border-white/[0.06] pl-2">
          {/* 叶参数 — 行内编辑 */}
          {leafParams.length > 0 && (
            <div className="space-y-0.5 py-0.5">
              {leafParams.map(param => (
                <div key={param.key}
                  className="flex items-center justify-between gap-2 py-0.5 px-1 hover:bg-white/5 rounded group/row"
                >
                  <div className="flex items-center gap-1 min-w-0">
                    <span className="text-[9px] text-gray-400 truncate">{param.label}</span>
                    {param.description && (
                      <span className="text-[8px] text-gray-600 cursor-help shrink-0" title={param.description}>
                        ?
                      </span>
                    )}
                  </div>
                  <div className="shrink-0" style={{ width: 90 }}>
                    <ParamInput
                      paramDef={param}
                      value={nodeValue[param.key]}
                      onChange={(key, val) => onParamChange(node.name, key, val)}
                    />
                  </div>
                </div>
              ))}
            </div>
          )}

          {/* 参数组 — 递归 */}
          {groups.map(group => (
            <div key={group.key} className="py-0.5">
              <div className="text-[9px] font-medium text-gray-500 uppercase tracking-wider px-1 mb-0.5">
                {group.label}
              </div>
              <div className="space-y-0.5">
                {(group.children || []).map(child => (
                  <div key={child.key}
                    className="flex items-center justify-between gap-2 py-0.5 px-1 hover:bg-white/5 rounded"
                  >
                    <span className="text-[9px] text-gray-400 truncate">{child.label}</span>
                    <div className="shrink-0" style={{ width: 90 }}>
                      <ParamInput
                        paramDef={child}
                        value={nodeValue[child.key]}
                        onChange={(key, val) => onParamChange(node.name, key, val)}
                      />
                    </div>
                  </div>
                ))}
              </div>
            </div>
          ))}

          {/* 子节点 */}
          {hasChildren && (
            <div className="space-y-0.5 pt-0.5">
              {Object.entries(node.children).map(([childName, childNode]) => (
                <TreeNodeView
                  key={childName}
                  node={childNode}
                  nodeValue={{}}
                  depth={depth + 1}
                  expandedNodes={expandedNodes}
                  toggleExpand={toggleExpand}
                  onParamChange={onParamChange}
                  onAddAgent={onAddAgent}
                  onDeleteAgent={onDeleteAgent}
                  onSelectAgent={onSelectAgent}
                  selectedPath={selectedPath}
                />
              ))}
            </div>
          )}

          {/* 空状态 */}
          {isEmpty && (
            <div className="text-[9px] text-gray-600 italic px-1 py-1">
              无参数和子节点
            </div>
          )}
        </div>
      )}
    </div>
  )
}

// ─── 主组件 ───────────────────────────────────────

export default function AgentTreeEditor({
  selectedAgentPath,
  onSelectAgent,
}: {
  selectedAgentPath?: string | null
  onSelectAgent?: (path: string | null) => void
}) {
  const [tree, setTree] = useState<TreeNode | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [expandedNodes, setExpandedNodes] = useState<Set<string>>(new Set(['engine', 'model']))
  const [dirtyParams, setDirtyParams] = useState<Record<string, Record<string, any>>>({})
  const [saving, setSaving] = useState(false)

  const [agentTypes, setAgentTypes] = useState<AgentTypeInfo[]>([])

  // 对话框状态
  const [showCreateDialog, setShowCreateDialog] = useState(false)
  const [createContext, setCreateContext] = useState<{
    parentPath: string; parentType: string
  } | null>(null)
  const [showDeleteDialog, setShowDeleteDialog] = useState(false)
  const [deleteContext, setDeleteContext] = useState<{
    path: string; name: string; type: string
  } | null>(null)

  // 跟踪树节点路径映射（name → full_path）
  const pathMapRef = useRef<Record<string, string>>({})

  // ─── 数据获取 ──────────────────────────────────

  const buildPathMap = useCallback((node: TreeNode, prefix = '') => {
    const currentPath = prefix ? `${prefix}.${node.name}` : node.name
    pathMapRef.current[node.name] = currentPath
    for (const child of Object.values(node.children)) {
      buildPathMap(child, currentPath)
    }
  }, [])

  const fetchTree = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const res = await fetch('/api/sim/tree')
      const data = await res.json()
      setTree(data)
      // 构建路径映射
      pathMapRef.current = {}
      buildPathMap(data)
    } catch {
      setError('加载 Agent 树失败')
    } finally {
      setLoading(false)
    }
  }, [buildPathMap])

  const fetchAgentTypes = useCallback(async () => {
    try {
      const res = await fetch('/api/sim/tree/types')
      const data = await res.json()
      setAgentTypes(data.types || [])
    } catch {
      // 静默失败
    }
  }, [])

  useEffect(() => {
    fetchTree()
    fetchAgentTypes()
  }, [fetchTree, fetchAgentTypes])

  // ─── 节点操作 ──────────────────────────────────

  const toggleExpand = useCallback((path: string) => {
    setExpandedNodes(prev => {
      const next = new Set(prev)
      if (next.has(path)) next.delete(path)
      else next.add(path)
      return next
    })
  }, [])

  const handleParamChange = useCallback((path: string, key: string, value: any) => {
    setDirtyParams(prev => ({
      ...prev,
      [path]: { ...(prev[path] || {}), [key]: value },
    }))
  }, [])

  const handleSelectAgent = useCallback((name: string) => {
    const fullPath = pathMapRef.current[name] || name
    if (selectedAgentPath === fullPath) {
      // 取消选择
      onSelectAgent?.(null)
    } else {
      onSelectAgent?.(fullPath)
    }
  }, [selectedAgentPath, onSelectAgent])

  // ─── 创建 Agent ────────────────────────────────

  const handleAddAgent = useCallback((parentName: string, parentType: string) => {
    const parentPath = pathMapRef.current[parentName] || parentName
    setCreateContext({ parentPath, parentType })
    setShowCreateDialog(true)
  }, [])

  const handleCreateAgent = useCallback(async (payload: {
    parent_path: string
    agent_type: string
    name: string
    display_name?: string
    params: Record<string, any>
  }) => {
    try {
      const res = await fetch('/api/sim/tree/agent', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      })
      if (!res.ok) {
        const err = await res.json().catch(() => ({ detail: '创建失败' }))
        throw new Error(err.detail || '创建失败')
      }
      await fetchTree()
      setError(null)
    } catch (e: any) {
      setError(e.message || '创建 Agent 失败')
    }
  }, [fetchTree])

  // ─── 删除 Agent ────────────────────────────────

  const handleDeleteClick = useCallback((agentName: string, displayName: string, type: string) => {
    const path = pathMapRef.current[agentName] || agentName
    setDeleteContext({ path, name: displayName, type })
    setShowDeleteDialog(true)
  }, [])

  const handleDeleteAgent = useCallback(async (path: string) => {
    try {
      const res = await fetch(
        `/api/sim/tree/agent?path=${encodeURIComponent(path)}`,
        { method: 'DELETE' }
      )
      if (!res.ok) {
        const err = await res.json().catch(() => ({ detail: '删除失败' }))
        throw new Error(err.detail || '删除失败')
      }
      setShowDeleteDialog(false)
      // 如果删除的是当前选中的 agent，清除选择
      if (selectedAgentPath === path) {
        onSelectAgent?.(null)
      }
      await fetchTree()
      setError(null)
    } catch (e: any) {
      setError(e.message || '删除 Agent 失败')
    }
  }, [fetchTree, selectedAgentPath])

  // ─── 保存变更 ──────────────────────────────────

  const handleSave = useCallback(async () => {
    setSaving(true)
    setError(null)
    try {
      const promises = Object.entries(dirtyParams).map(([path, params]) =>
        fetch('/api/sim/tree/parameters', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ path, params }),
        })
      )
      await Promise.all(promises)
      setDirtyParams({})
      await fetchTree()
    } catch {
      setError('保存参数失败')
    } finally {
      setSaving(false)
    }
  }, [dirtyParams, fetchTree])

  const dirtyCount = Object.keys(dirtyParams).length

  return (
    <div className="space-y-2 px-4 py-3">
      {/* 标题栏 */}
      <div className="flex items-center justify-between mb-2">
        <h3 className="text-xs font-semibold text-cyan-400 uppercase tracking-wider">
          Agent 树配置
        </h3>
        <div className="flex gap-1.5">
          <button
            onClick={fetchTree}
            disabled={loading}
            className="px-2 py-1 rounded text-[10px] font-medium border border-white/10 text-gray-400 hover:text-white transition-colors disabled:opacity-50"
          >
            刷新
          </button>
        </div>
      </div>

      {error && (
        <div className="bg-red-500/10 border border-red-500/30 rounded-lg px-3 py-2 text-xs text-red-400 flex items-center justify-between">
          <span>{error}</span>
          <button onClick={() => setError(null)} className="text-gray-500 hover:text-white ml-2">✕</button>
        </div>
      )}

      {loading ? (
        <div className="flex items-center justify-center py-8">
          <div className="w-5 h-5 border-2 border-cyan-500 border-t-transparent rounded-full animate-spin" />
          <span className="ml-2 text-xs text-gray-500">加载 Agent 树...</span>
        </div>
      ) : tree ? (
        <>
          {/* Agent 树形结构 */}
          <div className="max-h-[520px] overflow-y-auto border border-white/5 rounded-lg p-2 bg-white/[0.01]">
            <TreeNodeView
              node={tree}
              nodeValue={dirtyParams[tree.name] || {}}
              depth={0}
              expandedNodes={expandedNodes}
              toggleExpand={toggleExpand}
              onParamChange={handleParamChange}
              onAddAgent={handleAddAgent}
              onDeleteAgent={handleDeleteClick}
              onSelectAgent={handleSelectAgent}
              selectedPath={selectedAgentPath}
            />
          </div>

          {/* 保存按钮 */}
          <button
            onClick={handleSave}
            disabled={dirtyCount === 0 || saving}
            className={`w-full py-2 rounded-lg text-xs font-medium transition-all ${
              dirtyCount > 0
                ? 'bg-cyan-600 hover:bg-cyan-500 text-white'
                : 'bg-white/5 text-gray-600 cursor-not-allowed'
            }`}
          >
            {saving ? (
              <span className="flex items-center justify-center gap-2">
                <div className="w-3 h-3 border-2 border-white border-t-transparent rounded-full animate-spin" />
                保存中...
              </span>
            ) : dirtyCount > 0 ? (
              `保存变更 (${dirtyCount} 个节点)`
            ) : (
              '已是最新'
            )}
          </button>
        </>
      ) : null}

      {/* 创建 Agent 对话框 */}
      <CreateAgentDialog
        isOpen={showCreateDialog}
        onClose={() => setShowCreateDialog(false)}
        parentPath={createContext?.parentPath || ''}
        parentType={createContext?.parentType || ''}
        agentTypes={agentTypes}
        onCreate={handleCreateAgent}
      />

      {/* 删除确认对话框 */}
      <DeleteConfirmDialog
        isOpen={showDeleteDialog}
        onClose={() => setShowDeleteDialog(false)}
        agentPath={deleteContext?.path || ''}
        agentName={deleteContext?.name || ''}
        agentType={deleteContext?.type || ''}
        onDelete={handleDeleteAgent}
      />
    </div>
  )
}
