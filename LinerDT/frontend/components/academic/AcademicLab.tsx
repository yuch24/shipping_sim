'use client'

import { useState, useRef, useCallback, useEffect, ReactNode } from 'react'
import DataLab from './DataLab'
import ORLab from './ORLab'
import MLLab from './MLLab'
import NotebookLab from './NotebookLab'
import ReportLab from './ReportLab'

type TabId = 'data' | 'or' | 'ml' | 'notebook' | 'report'

interface TabDef {
  id: TabId
  label: string
  icon: ReactNode
}

const TABS: TabDef[] = [
  {
    id: 'data',
    label: 'Data Lab',
    icon: (
      <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 7v10c0 2.21 3.582 4 8 4s8-1.79 8-4V7M4 7c0 2.21 3.582 4 8 4s8-1.79 8-4M4 7c0-2.21 3.582-4 8-4s8 1.79 8 4m0 5c0 2.21-3.582 4-8 4s-8-1.79-8-4" />
      </svg>
    ),
  },
  {
    id: 'or',
    label: 'OR Lab',
    icon: (
      <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
      </svg>
    ),
  },
  {
    id: 'ml',
    label: 'ML Lab',
    icon: (
      <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9.75 17L9 20l-1 1h8l-1-1-.75-3M3 13h18M5 17h14a2 2 0 002-2V5a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z" />
      </svg>
    ),
  },
  {
    id: 'notebook',
    label: 'Notebook',
    icon: (
      <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 20l4-16m4 4l4 4-4 4M6 16l-4-4 4-4" />
      </svg>
    ),
  },
  {
    id: 'report',
    label: 'Report',
    icon: (
      <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
      </svg>
    ),
  },
]

// ── 浮动结果窗口 ──────────────────────────────────────────

interface FloatingWindow {
  id: string
  title: string
  content: ReactNode
  x: number
  y: number
  width: number
  height: number
}

interface ResultWindowProps {
  win: FloatingWindow
  onClose: (id: string) => void
  onFocus: (id: string) => void
  focusedId: string | null
}

function ResultWindow({ win, onClose, onFocus, focusedId }: ResultWindowProps) {
  const dragRef = useRef<{ startX: number; startY: number; startLeft: number; startTop: number } | null>(null)

  const handleMouseDown = useCallback((e: React.MouseEvent) => {
    onFocus(win.id)
    dragRef.current = {
      startX: e.clientX,
      startY: e.clientY,
      startLeft: win.x,
      startTop: win.y,
    }
  }, [win.id, win.x, win.y, onFocus])

  useEffect(() => {
    if (!dragRef.current) return
    const handleMove = (e: MouseEvent) => {
      if (!dragRef.current) return
      win.x = dragRef.current.startLeft + (e.clientX - dragRef.current.startX)
      win.y = dragRef.current.startTop + (e.clientY - dragRef.current.startY)
    }
    const handleUp = () => { dragRef.current = null }
    document.addEventListener('mousemove', handleMove)
    document.addEventListener('mouseup', handleUp)
    return () => {
      document.removeEventListener('mousemove', handleMove)
      document.removeEventListener('mouseup', handleUp)
    }
  }, [dragRef.current])

  const isFocused = focusedId === win.id

  return (
    <div
      className={`fixed rounded-lg border shadow-2xl flex flex-col transition-shadow ${
        isFocused ? 'border-marine-500/30 shadow-marine-500/10 z-50' : 'border-white/10 z-40'
      }`}
      style={{
        left: win.x,
        top: win.y,
        width: win.width,
        height: win.height,
        backgroundColor: 'rgba(13, 30, 48, 0.97)',
        backdropFilter: 'blur(12px)',
      }}
      onMouseDown={() => onFocus(win.id)}
    >
      {/* 标题栏 */}
      <div
        className="flex items-center justify-between px-3 py-1.5 cursor-move shrink-0 border-b border-white/10 select-none"
        onMouseDown={handleMouseDown}
      >
        <span className="text-[11px] font-medium text-gray-300">{win.title}</span>
        <button
          onClick={() => onClose(win.id)}
          className="p-0.5 text-gray-500 hover:text-white transition-colors rounded hover:bg-white/10"
        >
          <svg className="w-3 h-3" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
          </svg>
        </button>
      </div>

      {/* 内容 */}
      <div className="flex-1 overflow-auto p-3 text-[12px]">
        {win.content}
      </div>
    </div>
  )
}

// ── 主面板 ────────────────────────────────────────────────

interface AcademicLabProps {
  isOpen: boolean
  onToggle: (open: boolean) => void
}

export default function AcademicLab({ isOpen, onToggle }: AcademicLabProps) {
  const [activeTab, setActiveTab] = useState<TabId>('data')
  const [panelHeight, setPanelHeight] = useState(340)
  const [windows, setWindows] = useState<FloatingWindow[]>([])
  const [focusedWindowId, setFocusedWindowId] = useState<string | null>(null)
  const dragRef = useRef<{ startY: number; startHeight: number } | null>(null)
  const windowCounterRef = useRef(0)

  const handleOpenResult = useCallback((title: string, content: ReactNode) => {
    windowCounterRef.current += 1
    const id = `result-${windowCounterRef.current}`
    // 错开位置
    const offset = (windowCounterRef.current % 5) * 30
    const newWin: FloatingWindow = {
      id,
      title,
      content,
      x: 60 + offset,
      y: 60 + offset,
      width: 520,
      height: 380,
    }
    setWindows(prev => [...prev, newWin])
    setFocusedWindowId(id)
  }, [])

  const handleCloseWindow = useCallback((id: string) => {
    setWindows(prev => prev.filter(w => w.id !== id))
  }, [])

  const handleFocusWindow = useCallback((id: string) => {
    setFocusedWindowId(id)
    // 移到最前
    setWindows(prev => {
      const idx = prev.findIndex(w => w.id === id)
      if (idx < 0) return prev
      const item = prev[idx]
      const rest = prev.filter((_, i) => i !== idx)
      return [...rest, item]
    })
  }, [])

  const handleMouseDown = useCallback((e: React.MouseEvent) => {
    e.preventDefault()
    dragRef.current = { startY: e.clientY, startHeight: panelHeight }
  }, [panelHeight])

  const handleMouseMove = useCallback((e: MouseEvent) => {
    if (!dragRef.current) return
    const delta = dragRef.current.startY - e.clientY
    setPanelHeight(Math.max(180, Math.min(700, dragRef.current.startHeight + delta)))
  }, [])

  const handleMouseUp = useCallback(() => {
    dragRef.current = null
  }, [])

  useEffect(() => {
    if (dragRef.current) {
      document.addEventListener('mousemove', handleMouseMove)
      document.addEventListener('mouseup', handleMouseUp)
      return () => {
        document.removeEventListener('mousemove', handleMouseMove)
        document.removeEventListener('mouseup', handleMouseUp)
      }
    }
  }, [handleMouseMove, handleMouseUp, dragRef.current])

  function renderTabContent() {
    const commonProps = { onOpenResult: handleOpenResult }
    switch (activeTab) {
      case 'data': return <DataLab {...commonProps} />
      case 'or': return <ORLab {...commonProps} />
      case 'ml': return <MLLab {...commonProps} />
      case 'notebook': return <NotebookLab {...commonProps} />
      case 'report': return <ReportLab {...commonProps} />
      default: return null
    }
  }

  return (
    <>
      {/* 浮动结果窗口 — 渲染在 map 上方 */}
      {windows.map((win) => (
        <ResultWindow
          key={win.id}
          win={win}
          onClose={handleCloseWindow}
          onFocus={handleFocusWindow}
          focusedId={focusedWindowId}
        />
      ))}

      {/* 底部面板 — 展开时才渲染面板 */}
      {isOpen ? (
        <div
          className="bg-[#0d1e30] border-t border-white/10 flex flex-col"
          style={{ height: panelHeight }}
        >
          {/* 拖拽手柄 */}
          <div
            onMouseDown={handleMouseDown}
            className="h-2 shrink-0 cursor-row-resize relative group"
          >
            <div className="absolute left-1/2 top-1/2 -translate-x-1/2 -translate-y-1/2 w-8 h-0.5 rounded-full bg-white/10 group-hover:bg-marine-400/50 transition-colors" />
          </div>

          {/* 标签栏 */}
          <div className="flex items-center shrink-0 border-b border-white/10 px-2">
            {TABS.map((tab) => (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id)}
                className={`
                  flex-1 flex items-center justify-center gap-1.5 px-1 py-2 text-[11px] font-medium transition-all border-b-2 -mb-[1px] text-center
                  ${activeTab === tab.id
                    ? 'text-marine-400 border-marine-400 bg-marine-500/5'
                    : 'text-gray-500 border-transparent hover:text-gray-300 hover:border-gray-600'
                  }
                `}
              >
                <span className={activeTab === tab.id ? 'text-marine-400' : 'text-gray-500'}>
                  {tab.icon}
                </span>
                {tab.label}
              </button>
            ))}
            <div className="flex-1" />
          </div>

          {/* Tab 内容 */}
          <div className="flex-1 overflow-hidden">
            {renderTabContent()}
          </div>
        </div>
      ) : null}
    </>
  )
}
