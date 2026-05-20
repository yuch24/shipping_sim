'use client'

import { ReactNode, useState } from 'react'
import { LabModule } from './types'

const CATEGORY_LABELS: Record<string, string> = {
  or: '运筹学',
  ml: '机器学习',
  analysis: '数据分析',
  data: '数据浏览',
}

const CATEGORY_COLORS: Record<string, string> = {
  or: 'text-blue-400 border-blue-500/30 bg-blue-500/10',
  ml: 'text-purple-400 border-purple-500/30 bg-purple-500/10',
  analysis: 'text-green-400 border-green-500/30 bg-green-500/10',
  data: 'text-cyan-400 border-cyan-500/30 bg-cyan-500/10',
}

interface ModuleMarketProps {
  modules: LabModule[]
  activeModuleId: string | null
  onSelectModule: (id: string | null) => void
  onOpenResult: (title: string, content: ReactNode) => void
}

export default function ModuleMarket({
  modules,
  activeModuleId,
  onSelectModule,
  onOpenResult,
}: ModuleMarketProps) {
  const [filter, setFilter] = useState<string | null>(null)

  const filtered = filter
    ? modules.filter(m => m.category === filter)
    : modules

  const grouped = filtered.reduce<Record<string, LabModule[]>>((acc, m) => {
    if (!acc[m.category]) acc[m.category] = []
    acc[m.category].push(m)
    return acc
  }, {})

  const activeModule = modules.find(m => m.id === activeModuleId)

  // 如果有激活的模块，显示该模块内容
  if (activeModule && activeModuleId) {
    const ModuleComponent = activeModule.component
    return (
      <div className="h-full flex flex-col">
        {/* 模块标题 + 返回 */}
        <div className="flex items-center gap-2 px-3 py-2 border-b border-white/10 shrink-0">
          <button
            onClick={() => onSelectModule(null)}
            className="p-1 text-gray-500 hover:text-white hover:bg-white/10 rounded transition-colors"
            title="返回模块列表"
          >
            <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
            </svg>
          </button>
          <span className="text-[11px] font-medium text-gray-200">{activeModule.name}</span>
          <span className={`text-[9px] px-1.5 py-0.5 rounded-full border ${CATEGORY_COLORS[activeModule.category]}`}>
            {CATEGORY_LABELS[activeModule.category]}
          </span>
        </div>
        {/* 模块内容 */}
        <div className="flex-1 overflow-y-auto">
          <ModuleComponent onOpenResult={onOpenResult} />
        </div>
      </div>
    )
  }

  // 模块列表（市场视图）
  return (
    <div className="h-full flex flex-col">
      <div className="px-3 py-2 border-b border-white/10 shrink-0">
        <h3 className="text-[11px] font-semibold text-cyan-400 uppercase tracking-wider">模块市场</h3>
      </div>

      {/* 分类筛选 */}
      <div className="flex gap-1 px-3 py-1.5 border-b border-white/10 shrink-0 overflow-x-auto">
        <button
          onClick={() => setFilter(null)}
          className={`text-[10px] px-2 py-0.5 rounded-full transition-colors whitespace-nowrap ${
            filter === null ? 'bg-marine-500/20 text-marine-400' : 'text-gray-500 hover:text-gray-300'
          }`}
        >
          全部
        </button>
        {Object.entries(CATEGORY_LABELS).map(([key, label]) => (
          <button
            key={key}
            onClick={() => setFilter(key)}
            className={`text-[10px] px-2 py-0.5 rounded-full transition-colors whitespace-nowrap ${
              filter === key ? 'bg-marine-500/20 text-marine-400' : 'text-gray-500 hover:text-gray-300'
            }`}
          >
            {label}
          </button>
        ))}
      </div>

      {/* 模块列表 */}
      <div className="flex-1 overflow-y-auto px-2 py-2 space-y-2">
        {Object.entries(grouped).map(([category, mods]) => (
          <div key={category}>
            <div className="text-[9px] text-gray-600 uppercase tracking-wider px-1 py-1">
              {CATEGORY_LABELS[category] || category}
            </div>
            {mods.map(mod => (
              <button
                key={mod.id}
                onClick={() => onSelectModule(mod.id)}
                className="w-full text-left px-2 py-2 rounded-lg hover:bg-white/[0.04] transition-colors group"
              >
                <div className="flex items-center gap-2">
                  <span className="w-5 h-5 flex items-center justify-center text-marine-400 shrink-0">
                    {mod.icon}
                  </span>
                  <div className="min-w-0 flex-1">
                    <div className="text-[11px] font-medium text-gray-200 truncate group-hover:text-white transition-colors">
                      {mod.name}
                    </div>
                    <div className="text-[9px] text-gray-600 truncate">
                      {mod.description}
                    </div>
                  </div>
                </div>
              </button>
            ))}
          </div>
        ))}
      </div>
    </div>
  )
}
