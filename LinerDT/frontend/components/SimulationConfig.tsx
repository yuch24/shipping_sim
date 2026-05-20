'use client'

import { useState, useCallback } from 'react'

interface SimConfig {
  port_defaults: {
    berth_count: number
    crane_count: number
    handling_rate: number
  }
  fuel: {
    vlsfo_price: number
    mgo_price: number
    lng_price: number
    carbon_tax: number
    cii_rating_a: number
    cii_rating_b: number
    cii_rating_c: number
    cii_rating_d: number
  }
}

const DEFAULT_CONFIG: SimConfig = {
  port_defaults: {
    berth_count: 4,
    crane_count: 8,
    handling_rate: 120,
  },
  fuel: {
    vlsfo_price: 500,
    mgo_price: 650,
    lng_price: 350,
    carbon_tax: 0,
    cii_rating_a: 0.85,
    cii_rating_b: 1.00,
    cii_rating_c: 1.15,
    cii_rating_d: 1.35,
  },
}

interface SimulationConfigProps {
  connected: boolean
  isRunning: boolean
  speed: number
  onReset: () => void
  onApplyConfig: (config: SimConfig) => Promise<void>
}

export type { SimConfig }
export { DEFAULT_CONFIG }

export default function SimulationConfig({
  connected,
  isRunning,
  speed,
  onReset,
  onApplyConfig,
}: SimulationConfigProps) {
  const [config, setConfig] = useState<SimConfig>(() => {
    try {
      const saved = sessionStorage.getItem('sim_config')
      if (saved) return JSON.parse(saved) as SimConfig
    } catch {}
    return structuredClone(DEFAULT_CONFIG)
  })
  const [saving, setSaving] = useState(false)
  const [expandedSections, setExpandedSections] = useState<Record<string, boolean>>({
    ports: true,
    fuel: false,
  })

  const updateConfig = useCallback((updater: (prev: SimConfig) => SimConfig) => {
    setConfig(prev => {
      const next = updater(prev)
      try { sessionStorage.setItem('sim_config', JSON.stringify(next)) } catch {}
      return next
    })
  }, [])

  const toggleSection = (key: string) => {
    setExpandedSections(prev => ({ ...prev, [key]: !prev[key] }))
  }

  const handleSave = async () => {
    setSaving(true)
    try {
      await onApplyConfig(config)
    } catch (e) {
      console.error('应用配置失败:', e)
    }
    setSaving(false)
  }

  const handleReset = () => {
    setConfig(structuredClone(DEFAULT_CONFIG))
    sessionStorage.removeItem('sim_config')
    onReset()
  }

  const handleExport = () => {
    const blob = new Blob([JSON.stringify(config, null, 2)], { type: 'application/json' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `sim_config_${Date.now()}.json`
    a.click()
    URL.revokeObjectURL(url)
  }

  const handleImport = () => {
    const input = document.createElement('input')
    input.type = 'file'
    input.accept = '.json'
    input.onchange = async (e) => {
      const file = (e.target as HTMLInputElement).files?.[0]
      if (!file) return
      const text = await file.text()
      try {
        const imported = JSON.parse(text) as SimConfig
        updateConfig(() => imported)
      } catch {
        alert('配置文件格式错误')
      }
    }
    input.click()
  }

  const { port_defaults: portDef, fuel } = config

  return (
    <div className="h-full flex flex-col bg-[#0a1929]">
      <div className="shrink-0 flex items-center justify-between px-3 py-2 border-b border-white/10">
        <div className="flex items-center gap-2">
          <svg className="w-4 h-4 text-marine-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z" />
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
          </svg>
          <span className="font-medium text-gray-200 text-xs">仿真配置</span>
        </div>
        <div className="flex gap-1">
          <button onClick={handleImport} className="p-1 text-gray-500 hover:text-gray-300 rounded" title="导入配置">
            <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-8l-4-4m0 0L8 8m4-4v12" />
            </svg>
          </button>
          <button onClick={handleExport} className="p-1 text-gray-500 hover:text-gray-300 rounded" title="导出配置">
            <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" />
            </svg>
          </button>
        </div>
      </div>

      <div className="flex-1 overflow-auto p-3 space-y-2 text-[11px]">
        {/* 港口参数 */}
        <CollapsibleSection
          label="港口参数"
          badge="全局默认值"
          expanded={expandedSections.ports}
          onToggle={() => toggleSection('ports')}
        >
          <div className="text-[10px] text-gray-500 mb-2 border-l-2 border-green-500/30 pl-2">
            港口 Agent 全局默认参数，可单独在场景中覆盖。
          </div>

          <SliderField label="默认泊位数" value={portDef.berth_count} min={1} max={12} step={1} unit="个" onChange={(v) => updateConfig(c => ({ ...c, port_defaults: { ...c.port_defaults, berth_count: v } }))} />
          <SliderField label="默认岸桥数" value={portDef.crane_count} min={2} max={20} step={1} unit="台" onChange={(v) => updateConfig(c => ({ ...c, port_defaults: { ...c.port_defaults, crane_count: v } }))} />
          <SliderField label="装卸效率" value={portDef.handling_rate} min={30} max={300} step={10} unit="m/h" onChange={(v) => updateConfig(c => ({ ...c, port_defaults: { ...c.port_defaults, handling_rate: v } }))} />

          <InfoRow label="排队规则" value="FIFO（先到先服务）" />
          <InfoRow label="泊位分配" value="可用泊位优先分配，无泊位则入队等待" />
        </CollapsibleSection>

        {/* 燃油与排放 */}
        <CollapsibleSection
          label="燃油与排放"
          badge="环境合规"
          expanded={expandedSections.fuel}
          onToggle={() => toggleSection('fuel')}
        >
          <SubSection label="燃油价格（$/吨）">
            <SliderField label="VLSFO" value={fuel.vlsfo_price} min={200} max={1200} step={10} unit="$" onChange={(v) => updateConfig(c => ({ ...c, fuel: { ...c.fuel, vlsfo_price: v } }))} />
            <SliderField label="MGO" value={fuel.mgo_price} min={300} max={1500} step={10} unit="$" onChange={(v) => updateConfig(c => ({ ...c, fuel: { ...c.fuel, mgo_price: v } }))} />
            <SliderField label="LNG" value={fuel.lng_price} min={100} max={800} step={10} unit="$" onChange={(v) => updateConfig(c => ({ ...c, fuel: { ...c.fuel, lng_price: v } }))} />
          </SubSection>

          <SubSection label="排放因子（kg CO₂ / kg fuel）">
            <InfoRow label="VLSFO" value="3.151" />
            <InfoRow label="MGO" value="3.206" />
            <InfoRow label="LNG" value="2.750" />
          </SubSection>

          <SubSection label="碳税">
            <SliderField label="碳税税率" value={fuel.carbon_tax} min={0} max={200} step={5} unit="$/t" onChange={(v) => updateConfig(c => ({ ...c, fuel: { ...c.fuel, carbon_tax: v } }))} />
          </SubSection>

          <SubSection label="CII 评级阈值（×R）">
            <SliderField label="A 级 ≤" value={fuel.cii_rating_a} min={0.5} max={0.95} step={0.01} unit="×R" displayValue={`${(fuel.cii_rating_a * 100).toFixed(0)}%R`} onChange={(v) => updateConfig(c => ({ ...c, fuel: { ...c.fuel, cii_rating_a: v } }))} />
            <SliderField label="B 级 ≤" value={fuel.cii_rating_b} min={0.85} max={1.1} step={0.01} unit="×R" displayValue={`${(fuel.cii_rating_b * 100).toFixed(0)}%R`} onChange={(v) => updateConfig(c => ({ ...c, fuel: { ...c.fuel, cii_rating_b: v } }))} />
            <SliderField label="C 级 ≤" value={fuel.cii_rating_c} min={1.0} max={1.25} step={0.01} unit="×R" displayValue={`${(fuel.cii_rating_c * 100).toFixed(0)}%R`} onChange={(v) => updateConfig(c => ({ ...c, fuel: { ...c.fuel, cii_rating_c: v } }))} />
            <SliderField label="D 级 ≤" value={fuel.cii_rating_d} min={1.2} max={1.5} step={0.01} unit="×R" displayValue={`${(fuel.cii_rating_d * 100).toFixed(0)}%R`} onChange={(v) => updateConfig(c => ({ ...c, fuel: { ...c.fuel, cii_rating_d: v } }))} />
          </SubSection>
        </CollapsibleSection>

        {/* 系统状态 */}
        <Section label="系统状态">
          <div className="space-y-1 text-[10px]">
            <div className="flex justify-between">
              <span className="text-gray-500">连接状态</span>
              <span className={connected ? 'text-green-400' : 'text-red-400'}>
                {connected ? '已连接' : '断开'}
              </span>
            </div>
            <div className="flex justify-between">
              <span className="text-gray-500">运行状态</span>
              <span className={isRunning ? 'text-green-400' : 'text-gray-400'}>
                {isRunning ? '运行中' : '已停止'}
              </span>
            </div>
            <div className="flex justify-between">
              <span className="text-gray-500">运行速度</span>
              <span className="text-gray-300 font-mono">{speed}×</span>
            </div>
          </div>
        </Section>

        <div className="h-2" />
      </div>

      <div className="shrink-0 border-t border-white/10 p-3 space-y-1.5">
        <button
          onClick={handleSave}
          disabled={saving}
          className="w-full px-3 py-1.5 text-xs font-medium bg-marine-500 hover:bg-marine-400 disabled:bg-gray-700 disabled:text-gray-500 text-white rounded-lg transition-colors"
        >
          {saving ? '应用配置中...' : '应用配置并重启仿真'}
        </button>
        <div className="flex gap-2">
          <button
            onClick={handleReset}
            disabled={isRunning}
            className="flex-1 px-2 py-1 text-[10px] font-medium bg-white/5 hover:bg-red-500/20 hover:text-red-400 disabled:text-gray-600 disabled:bg-transparent text-gray-400 rounded-lg transition-colors"
          >
            恢复默认
          </button>
          <button
            onClick={handleExport}
            className="flex-1 px-2 py-1 text-[10px] font-medium bg-white/5 hover:bg-white/10 text-gray-400 rounded-lg transition-colors"
          >
            导出配置
          </button>
        </div>
      </div>
    </div>
  )
}

function CollapsibleSection({
  label,
  badge,
  expanded,
  onToggle,
  children,
}: {
  label: string
  badge?: string
  expanded: boolean
  onToggle: () => void
  children: React.ReactNode
}) {
  return (
    <div className="border border-white/10 rounded-lg overflow-hidden">
      <button
        onClick={onToggle}
        className="w-full flex items-center justify-between px-2.5 py-1.5 bg-white/[0.03] hover:bg-white/[0.06] transition-colors text-left"
      >
        <div className="flex items-center gap-2">
          <svg
            className={`w-3 h-3 text-gray-500 transition-transform ${expanded ? 'rotate-90' : ''}`}
            fill="none" viewBox="0 0 24 24" stroke="currentColor"
          >
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
          </svg>
          <span className="text-[10px] font-medium text-gray-300 uppercase tracking-wider">{label}</span>
        </div>
        {badge && (
          <span className="text-[9px] text-gray-500 font-mono">{badge}</span>
        )}
      </button>
      {expanded && (
        <div className="px-2.5 py-2 space-y-0.5 border-t border-white/5">
          {children}
        </div>
      )}
    </div>
  )
}

function Section({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div className="border border-white/10 rounded-lg overflow-hidden">
      <div className="px-2.5 py-1.5 bg-white/[0.03]">
        <span className="text-[10px] font-medium text-gray-500 uppercase tracking-wider">{label}</span>
      </div>
      <div className="px-2.5 py-2">
        {children}
      </div>
    </div>
  )
}

function SubSection({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div className="mb-2 pt-1 first:pt-0">
      <div className="text-[10px] text-gray-600 mb-1 font-medium">{label}</div>
      {children}
    </div>
  )
}

function InfoRow({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex justify-between items-center mb-1">
      <span className="text-[10px] text-gray-500">{label}</span>
      <span className="text-[10px] text-gray-400 text-right max-w-[60%]">{value}</span>
    </div>
  )
}

function SliderField({
  label,
  value,
  min,
  max,
  step,
  unit,
  displayValue,
  onChange,
}: {
  label: string
  value: number
  min: number
  max: number
  step: number
  unit: string
  displayValue?: string
  onChange: (v: number) => void
}) {
  return (
    <div className="mb-1.5">
      <div className="flex justify-between items-center mb-0.5">
        <span className="text-[10px] text-gray-400">{label}</span>
        <span className="text-[10px] font-mono text-marine-400 tabular-nums">
          {displayValue ?? `${value}${unit}`}
        </span>
      </div>
      <input
        type="range"
        min={min}
        max={max}
        step={step}
        value={value}
        onChange={(e) => onChange(parseFloat(e.target.value))}
        className="w-full h-1 appearance-none bg-white/10 rounded-full outline-none cursor-pointer
          [&::-webkit-slider-thumb]:appearance-none [&::-webkit-slider-thumb]:w-2.5 [&::-webkit-slider-thumb]:h-2.5
          [&::-webkit-slider-thumb]:rounded-full [&::-webkit-slider-thumb]:bg-marine-400
          [&::-webkit-slider-thumb]:cursor-pointer [&::-webkit-slider-thumb]:shadow-sm"
      />
    </div>
  )
}