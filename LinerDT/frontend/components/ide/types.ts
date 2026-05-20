import { ReactNode } from 'react'

// 左侧 Activity Bar 图标项
export interface ActivityBarItem {
  id: string
  icon: ReactNode
  label: string
}

// 侧边栏面板
export interface SidebarPanel {
  id: string
  label: string
  icon: ReactNode
  component: ReactNode
}

// 工作区视图（标签页）
export interface WorkspaceView {
  id: string
  label: string
  icon?: ReactNode
  component: ReactNode
  closable?: boolean
}

// Lab 模块（左侧侧边栏中的学术模块）
export interface LabModule {
  id: string
  name: string
  description: string
  category: 'or' | 'ml' | 'analysis' | 'data'
  icon: ReactNode
  component: React.ComponentType<LabModuleProps>
}

export interface LabModuleProps {
  onOpenResult: (title: string, content: ReactNode) => void
}
