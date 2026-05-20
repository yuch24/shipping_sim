'use client'

import { useState, useRef, useEffect } from 'react'

interface ControlPanelProps {
  isRunning: boolean
  currentTime: number
  speed: number
  simulationMode?: string
  mapType?: '3d' | '2d'
  onMapTypeChange?: (type: '3d' | '2d') => void
  showAnalysis?: boolean
  onToggleAnalysis?: () => void
  showTeaching?: boolean
  onToggleTeaching?: () => void
  connected?: boolean
  onSetMode?: (mode: string) => void
  onStart: () => void
  onPause: () => void
  onReset: () => void
  onSpeedChange: (speed: number) => void
  hideProgress?: boolean
  hideAnalysis?: boolean
}

const SPEED_PRESETS = [
  { value: 60, label: '1分/秒', desc: '1分钟仿真/1秒现实' },
  { value: 1440, label: '1天/秒', desc: '1天仿真/1秒现实' },
  { value: 3600, label: '1时/秒', desc: '1小时仿真/1秒现实' },
  { value: 7200, label: '2时/秒', desc: '2小时仿真/1秒现实' },
]

export default function ControlPanel({
  isRunning,
  currentTime,
  speed,
  simulationMode = 'academic',
  mapType = '3d',
  onMapTypeChange,
  showAnalysis = false,
  onToggleAnalysis,
  showTeaching = false,
  onToggleTeaching,
  connected = false,
  onSetMode,
  onStart,
  onPause,
  onReset,
  onSpeedChange,
  hideProgress = false,
  hideAnalysis = false,
}: ControlPanelProps) {
  const [showSpeedMenu, setShowSpeedMenu] = useState(false)
  const [showSimConfirm, setShowSimConfirm] = useState(false)
  const [pendingMode, setPendingMode] = useState<string | null>(null)
  const isRealTime = simulationMode === 'real_time'

  const [smoothTime, setSmoothTime] = useState(currentTime)
  const lastBackendTimeRef = useRef(currentTime)
  const lastBackendWallRef = useRef(Date.now())

  useEffect(() => {
    if (!isRunning) {
      setSmoothTime(currentTime)
      lastBackendTimeRef.current = currentTime
      lastBackendWallRef.current = Date.now()
      return
    }
    lastBackendTimeRef.current = currentTime
    lastBackendWallRef.current = Date.now()
  }, [currentTime, isRunning])

  useEffect(() => {
    if (!isRunning) { setSmoothTime(currentTime); return }
    const interval = setInterval(() => {
      const elapsed = (Date.now() - lastBackendWallRef.current) / 1000
      const simHoursPerSec = speed / 3600.0
      const interpolated = lastBackendTimeRef.current + elapsed * simHoursPerSec
      if (interpolated >= 0) setSmoothTime(interpolated)
    }, 50)
    return () => clearInterval(interval)
  }, [isRunning, speed])

  const formatTime = (hours: number): string => {
    const totalHours = Math.max(0, hours)
    const days = Math.floor(totalHours / 24)
    const h = Math.floor(totalHours % 24)
    const m = Math.floor((totalHours % 1) * 60)
    return `D${days + 1} ${h.toString().padStart(2, '0')}:${m.toString().padStart(2, '0')}`
  }

  const formatSimDate = (hours: number): string => {
    const baseDate = new Date(2024, 0, 1)
    const totalMs = hours * 3600 * 1000
    const simDate = new Date(baseDate.getTime() + totalMs)
    return simDate.toLocaleDateString('zh-CN', { year: 'numeric', month: '2-digit', day: '2-digit' })
  }

  const handleSimModeToggle = () => {
    const targetMode = isRealTime ? 'academic' : 'real_time'
    if (isRunning) {
      setPendingMode(targetMode)
      setShowSimConfirm(true)
    } else {
      onSetMode?.(targetMode)
    }
  }

  const confirmSimSwitch = () => {
    if (pendingMode) {
      onSetMode?.(pendingMode)
    }
    setShowSimConfirm(false)
    setPendingMode(null)
  }

  const currentPreset = SPEED_PRESETS.find(p => p.value === speed) || SPEED_PRESETS[0]

  return (
    <div className="flex flex-col items-center gap-1.5">
      <div className="flex items-center gap-1.5 glass-panel px-2 py-1.5 shadow-lg shadow-black/30">
        {/* 仿真日期 */}
        <span className="text-[10px] font-mono text-emerald-400 font-medium mr-0.5 min-w-[68px]">
          {formatSimDate(isRunning ? smoothTime : currentTime)}
        </span>
        <span className="text-[10px] font-mono text-marine-400 font-medium tabular-nums min-w-[56px]">
          {isRealTime ? (
            <span className="text-green-400">LIVE</span>
          ) : (
            formatTime(isRunning ? smoothTime : currentTime)
          )}
        </span>

        <div className="w-px h-3.5 bg-white/8" />

        {/* 播放/暂停 */}
        {!isRealTime && (
          <>
            {!isRunning ? (
              <button onClick={onStart} className="p-1.5 text-gray-300 hover:text-white hover:bg-white/10 rounded-md transition-all active:scale-90" title="启动">
                <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 24 24">
                  <path d="M8 5v14l11-7z" />
                </svg>
              </button>
            ) : (
              <button onClick={onPause} className="p-1.5 text-gray-300 hover:text-white hover:bg-white/10 rounded-md transition-all active:scale-90" title="暂停">
                <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 24 24">
                  <path d="M6 19h4V5H6v14zm8-14v14h4V5h-4z" />
                </svg>
              </button>
            )}

            <button onClick={onReset} className="p-1.5 text-gray-500 hover:text-red-400 hover:bg-red-500/10 rounded-md transition-all active:scale-90" title="重置">
              <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
              </svg>
            </button>

            <div className="w-px h-3.5 bg-white/8" />
          </>
        )}

        {isRealTime && (
          <button onClick={onReset} className="p-1.5 text-gray-500 hover:text-red-400 hover:bg-red-500/10 rounded-md transition-all active:scale-90" title="重置">
            <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
            </svg>
          </button>
        )}

        {/* 速度选择 */}
        {!isRealTime && (
          <div className="relative">
            <button
              onClick={() => setShowSpeedMenu(!showSpeedMenu)}
              className="flex items-center gap-1 px-2 py-1 text-[10px] font-mono text-gray-400 hover:text-white hover:bg-white/10 rounded-md transition-all"
              title={currentPreset.desc}
            >
              <span className="tabular-nums text-marine-400">{currentPreset.label}</span>
              <svg className="w-2.5 h-2.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
              </svg>
            </button>

            {showSpeedMenu && (
              <>
                <div className="fixed inset-0 z-10" onClick={() => setShowSpeedMenu(false)} />
                <div className="absolute top-full left-0 mt-1 z-20 glass-panel py-0.5 shadow-xl shadow-black/40 min-w-[90px]">
                  {SPEED_PRESETS.map((p) => (
                    <button
                      key={p.value}
                      onClick={() => { onSpeedChange(p.value); setShowSpeedMenu(false) }}
                      className={`w-full text-left px-3 py-1 text-[10px] font-mono transition-colors ${
                        speed === p.value
                          ? 'text-marine-400 bg-marine-500/10'
                          : 'text-gray-400 hover:text-white hover:bg-white/5'
                      }`}
                    >
                      {p.label}
                    </button>
                  ))}
                </div>
              </>
            )}
          </div>
        )}

        <div className="w-px h-3.5 bg-white/8" />

        {/* 2D/3D */}
        <button
          onClick={() => onMapTypeChange?.(mapType === '3d' ? '2d' : '3d')}
          className={`p-1.5 rounded-md transition-all active:scale-90 ${
            mapType === '3d' ? 'text-marine-400 hover:text-marine-300 hover:bg-white/10' : 'text-gray-400 hover:text-white hover:bg-white/10'
          }`}
          title={mapType === '3d' ? '2D地图' : '3D地球'}
        >
          {mapType === '3d' ? (
            <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 15a4 4 0 004 4h9a5 5 0 10-.1-9.999 5.002 5.002 0 10-9.78 2.096A4.001 4.001 0 003 15z" />
            </svg>
          ) : (
            <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 20l-5.447-2.724A1 1 0 013 16.382V5.618a1 1 0 011.447-.894L9 7m0 13l6-3m-6 3V7m6 10l4.553 2.276A1 1 0 0021 18.382V7.618a1 1 0 00-.553-.894L15 4m0 13V4m0 0L9 7" />
            </svg>
          )}
        </button>

        <div className="w-px h-3.5 bg-white/8" />

        {!hideAnalysis && (
          <button
            onClick={onToggleAnalysis}
            className={`p-1.5 rounded-md transition-all active:scale-90 ${
              showAnalysis ? 'text-marine-400 hover:text-marine-300 hover:bg-white/10' : 'text-gray-400 hover:text-white hover:bg-white/10'
            }`}
            title={showAnalysis ? '地图' : '分析'}
          >
            <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
            </svg>
          </button>
        )}

        {onToggleTeaching && (
          <button
            onClick={onToggleTeaching}
            className={`p-1.5 rounded-md transition-all active:scale-90 ${
              showTeaching ? 'text-marine-400 hover:text-marine-300 hover:bg-white/10' : 'text-gray-400 hover:text-white hover:bg-white/10'
            }`}
            title={showTeaching ? '监控' : '教学'}
          >
            <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 6.253v13m0-13C10.832 5.477 9.246 5 7.5 5S4.168 5.477 3 6.253v13C4.168 18.477 5.754 18 7.5 18s3.332.477 4.5 1.253m0-13C13.168 5.477 14.754 5 16.5 5c1.747 0 3.332.477 4.5 1.253v13C19.832 18.477 18.247 18 16.5 18c-1.746 0-3.332.477-4.5 1.253" />
            </svg>
          </button>
        )}

        <div className="w-px h-3.5 bg-white/8" />

        {onSetMode && (
          <div className="relative">
            <button
              onClick={handleSimModeToggle}
              className={`flex items-center gap-1 px-2 py-1 rounded-md text-[10px] font-medium transition-all ${
                isRealTime ? 'text-green-400 hover:bg-green-500/10' : 'text-blue-400 hover:bg-blue-500/10'
              }`}
              title={isRealTime ? '学术仿真' : '实时孪生'}
            >
              <span className={`w-1.5 h-1.5 rounded-full ${isRealTime ? 'bg-green-400 animate-pulse' : 'bg-blue-400'}`} />
              <span>{isRealTime ? '实时' : '学术'}</span>
            </button>

            {showSimConfirm && (
              <>
                <div className="fixed inset-0 z-10" onClick={() => setShowSimConfirm(false)} />
                <div className="absolute bottom-full right-0 mb-1 z-20 glass-panel p-3 shadow-xl shadow-black/40 min-w-[180px]">
                  <p className="text-[11px] text-gray-300 mb-2">
                    {pendingMode === 'real_time'
                      ? '切换到实时孪生将停止当前仿真并重置状态。'
                      : '切换到学术仿真将停止实时数据流并重置仿真。'}
                  </p>
                  <div className="flex gap-2 justify-end">
                    <button onClick={() => setShowSimConfirm(false)} className="px-2 py-1 text-[10px] text-gray-400 hover:text-white bg-white/5 rounded">取消</button>
                    <button onClick={confirmSimSwitch} className="px-2 py-1 text-[10px] text-white bg-marine-500 hover:bg-marine-400 rounded">确认切换</button>
                  </div>
                </div>
              </>
            )}
          </div>
        )}

        <span className={`w-1.5 h-1.5 rounded-full ${connected ? 'bg-green-500' : 'bg-red-500'}`} title={connected ? '系统正常' : '连接断开'} />
      </div>
    </div>
  )
}