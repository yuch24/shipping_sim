'use client'

import { ReactNode } from 'react'
import { WorkspaceView } from './types'

interface WorkspaceProps {
  views: WorkspaceView[]
  activeViewId?: string
  onViewChange?: (id: string) => void
  onViewClose?: (id: string) => void
}

export default function Workspace({
  views,
  activeViewId,
  onViewChange,
  onViewClose,
}: WorkspaceProps) {
  // 由 AppShell 统一管理标签栏，此组件仅用于渲染视图内容
  // 保留 Props 接口以兼容旧调用方
  return null
}
