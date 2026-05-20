'use client'

import { ReactNode, useState } from 'react'
import { LabModule } from './types'

interface WorkbenchProps {
  modules: LabModule[]
  onOpenResult: (title: string, content: ReactNode) => void
}

const TAB_DEFS: { id: string; label: string; icon: ReactNode }[] = [
  {
    id: 'or',
    label: '运筹',
    icon: (
      <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
      </svg>
    ),
  },
  {
    id: 'ml',
    label: '预测',
    icon: (
      <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z" />
      </svg>
    ),
  },
  {
    id: 'data',
    label: '数据',
    icon: (
      <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 7v10c0 2.21 3.582 4 8 4s8-1.79 8-4V7M4 7c0 2.21 3.582 4 8 4s8-1.79 8-4M4 7c0-2.21 3.582-4 8-4s8 1.79 8 4m0 5c0 2.21-3.582 4-8 4s-8-1.79-8-4" />
      </svg>
    ),
  },
  {
    id: 'experiment',
    label: '实验',
    icon: (
      <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19.428 15.428a2 2 0 00-1.022-.547l-2.387-.477a6 6 0 00-3.86.517l-.318.158a6 6 0 01-3.86.517L6.05 15.21a2 2 0 00-1.806.547M8 4h8l-1 1v5.172a2 2 0 00.586 1.414l5 5c1.26 1.26.367 3.414-1.415 3.414H4.828c-1.782 0-2.674-2.154-1.414-3.414l5-5A2 2 0 009 10.172V5L8 4z" />
      </svg>
    ),
  },
  {
    id: 'report',
    label: '报告',
    icon: (
      <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
      </svg>
    ),
  },
]

// tab id → 对应的 module id 映射
const TAB_MODULE_MAP: Record<string, string | null> = {
  or: 'or-lab',
  ml: 'ml-lab',
  data: 'data-lab',
  experiment: 'notebook-lab',
  report: 'report-lab',
}

export default function Workbench({
  modules,
  onOpenResult,
}: WorkbenchProps) {
  const [activeTab, setActiveTab] = useState('or')

  const moduleId = TAB_MODULE_MAP[activeTab]
  const activeModule = moduleId ? modules.find(m => m.id === moduleId) : null

  return (
    <div className="h-full flex flex-col">
      {/* 标题 + tab 导航 */}
      <div className="shrink-0 border-b border-white/10">
        <div className="flex items-center gap-2 px-3 pt-2 pb-1.5">
          <div className="w-5 h-5 rounded-md bg-gradient-to-br from-cyan-500 to-blue-500 flex items-center justify-center shrink-0">
            <svg className="w-3 h-3 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19.428 15.428a2 2 0 00-1.022-.547l-2.387-.477a6 6 0 00-3.86.517l-.318.158a6 6 0 01-3.86.517L6.05 15.21a2 2 0 00-1.806.547M8 4h8l-1 1v5.172a2 2 0 00.586 1.414l5 5c1.26 1.26.367 3.414-1.415 3.414H4.828c-1.782 0-2.674-2.154-1.414-3.414l5-5A2 2 0 009 10.172V5L8 4z" />
            </svg>
          </div>
          <span className="text-[11px] font-semibold text-cyan-400 uppercase tracking-wider">实验台</span>
        </div>
        <div className="flex px-2 gap-0.5 pb-0.5">
          {TAB_DEFS.map((tab) => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={`flex items-center gap-1 px-2.5 py-1 text-[10px] rounded-t-md transition-all ${
                activeTab === tab.id
                  ? 'bg-[#0a1929] text-cyan-400 font-medium'
                  : 'text-gray-500 hover:text-gray-300 hover:bg-white/[0.03]'
              }`}
            >
              <span className="w-3.5 h-3.5">{tab.icon}</span>
              {tab.label}
            </button>
          ))}
        </div>
      </div>

      {/* 内容区 */}
      <div className="flex-1 overflow-y-auto">
        {activeModule ? (
          <div className="p-3">
            <div className="text-[10px] text-gray-500 mb-3">{activeModule.description}</div>
            <activeModule.component onOpenResult={onOpenResult} />
          </div>
        ) : (
          <div className="flex items-center justify-center h-full text-gray-600 text-xs">
            选择一个分析视角开始
          </div>
        )}
      </div>
    </div>
  )
}
