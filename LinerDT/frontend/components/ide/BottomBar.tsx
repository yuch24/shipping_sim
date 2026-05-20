'use client'

import { ReactNode } from 'react'

interface BottomBarProps {
  left?: ReactNode       // 控制面板/播放按钮
  center?: ReactNode     // 进度条
  right?: ReactNode      // 状态信息
  children?: ReactNode   // 额外内容（如底部分隔线以下）
}

export default function BottomBar({ left, center, right, children }: BottomBarProps) {
  return (
    <div className="shrink-0 border-t border-white/10 bg-[#0d1e30]">
      <div className="flex items-center justify-between px-3 py-1.5 gap-3">
        <div className="flex items-center gap-2">{left}</div>
        <div className="flex-1 flex justify-center">{center}</div>
        <div className="flex items-center gap-2">{right}</div>
      </div>
      {children}
    </div>
  )
}
