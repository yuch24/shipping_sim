'use client'

import { ReactNode, useState } from 'react'
import ActivityBar from './ActivityBar'
import Sidebar from './Sidebar'
import Workspace from './Workspace'
import { ActivityBarItem, WorkspaceView } from './types'

interface AppShellProps {
  // Activity Bar: 左侧图标栏
  activityItems: ActivityBarItem[]
  // 左侧侧边栏内容（keyed by activity id）
  sidebarPanels: Record<string, ReactNode>
  // 工作区视图
  workspaceViews: WorkspaceView[]
  // 右侧侧边栏内容（AI 对话等）
  rightSidebar?: ReactNode
  rightSidebarOpen?: boolean
  onRightSidebarClose?: () => void
  // 标题栏插槽
  headerCenter?: ReactNode
  headerRight?: ReactNode
}

export default function AppShell({
  activityItems,
  sidebarPanels,
  workspaceViews,
  rightSidebar,
  rightSidebarOpen = false,
  onRightSidebarClose,
  headerCenter,
  headerRight,
}: AppShellProps) {
  const [activeActivityId, setActiveActivityId] = useState<string | null>(null)
  const [activeViewId, setActiveViewId] = useState<string | undefined>(undefined)

  const currentSidebarContent = activeActivityId ? sidebarPanels[activeActivityId] : null
  const resolvedViewId = activeViewId ?? workspaceViews[0]?.id
  const activeView = workspaceViews.find(v => v.id === resolvedViewId)

  return (
    <div className="h-screen flex flex-col bg-[#0a1929]">
      {/* 顶部标题栏（贯穿左右，三栏 grid 确保中间始终居中） */}
      <div className="grid grid-cols-[1fr_auto_1fr] items-start shrink-0 bg-[#0d1e30] border-b border-white/10 z-10 h-8">
        {/* 左侧：标签页 */}
        <div className="flex items-center overflow-hidden">
          {workspaceViews.length > 1 && workspaceViews.map((view) => {
            const isActive = view.id === resolvedViewId
            return (
              <div
                key={view.id}
                className={`group flex items-center gap-1.5 px-3 py-1.5 text-[11px] cursor-pointer border-r border-white/5 transition-colors shrink-0 ${
                  isActive
                    ? 'bg-[#0a1929] text-white border-b-2 border-b-marine-400 mb-[-1px]'
                    : 'text-gray-500 hover:text-gray-300 hover:bg-white/[0.02]'
                }`}
                onClick={() => setActiveViewId(view.id)}
              >
                {view.icon && <span className="w-3.5 h-3.5">{view.icon}</span>}
                <span className="whitespace-nowrap">{view.label}</span>
              </div>
            )
          })}
        </div>

        {/* 中间：控制面板（grid 天然居中） */}
        {headerCenter && (
          <div>{headerCenter}</div>
        )}

        {/* 右侧：AI 按钮 */}
        {headerRight && (
          <div className="flex items-center justify-end px-1">
            {headerRight}
          </div>
        )}
      </div>

      {/* 主区域：ActivityBar + Sidebar + Workspace + RightSidebar */}
      <div className="flex-1 flex overflow-hidden">
        <ActivityBar
          items={activityItems}
          activeId={activeActivityId}
          onSelect={setActiveActivityId}
        />

        <Sidebar
          isOpen={!!currentSidebarContent}
          side="left"
          onClose={() => setActiveActivityId(null)}
        >
          {currentSidebarContent ?? null}
        </Sidebar>

        {/* 工作区内容 */}
        <div className="flex-1 relative overflow-hidden">
          {activeView?.component}
        </div>

        {rightSidebar && (
          <Sidebar
            isOpen={rightSidebarOpen}
            side="right"
            onClose={onRightSidebarClose}
            hideTitle
          >
            {rightSidebar}
          </Sidebar>
        )}
      </div>
    </div>
  )
}
