'use client'

import { useCallback } from 'react'
import DistributionEditor from './DistributionEditor'

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
}

interface ParameterEditorProps {
  paramDef: ParamDef
  value: any
  onChange: (key: string, value: any) => void
}

export default function ParameterEditor({ paramDef, value, onChange }: ParameterEditorProps) {
  const handleChange = useCallback(
    (newVal: any) => onChange(paramDef.key, newVal),
    [paramDef.key, onChange]
  )

  const currentValue = value ?? paramDef.default ?? ''

  switch (paramDef.type) {
    case 'float':
    case 'int': {
      const step = paramDef.step ?? (paramDef.type === 'int' ? 1 : 0.1)
      const displayVal = currentValue !== '' && currentValue != null ? currentValue : ''
      return (
        <div className="flex items-center gap-1.5">
          <input
            type="number"
            step={step}
            min={paramDef.min}
            max={paramDef.max}
            value={displayVal}
            onChange={e => {
              const v = paramDef.type === 'int' ? parseInt(e.target.value, 10) : parseFloat(e.target.value)
              handleChange(isNaN(v) ? 0 : v)
            }}
            className="flex-1 px-1.5 py-0.5 text-[10px] font-mono bg-white/5 border border-white/10 rounded text-gray-300 outline-none focus:border-marine-500/40 w-0 min-w-0"
          />
          {paramDef.unit && <span className="text-[10px] text-gray-500 shrink-0">{paramDef.unit}</span>}
        </div>
      )
    }

    case 'bool':
      return (
        <label className="flex items-center gap-2 cursor-pointer">
          <input
            type="checkbox"
            checked={!!currentValue}
            onChange={e => handleChange(e.target.checked)}
            className="accent-marine-500 w-3 h-3"
          />
          <span className="text-[10px] text-gray-400">{paramDef.label}</span>
        </label>
      )

    case 'enum':
      return (
        <select
          value={String(currentValue)}
          onChange={e => handleChange(e.target.value)}
          className="w-full px-2 py-1 text-[10px] bg-white/5 border border-white/10 rounded text-gray-300 outline-none focus:border-marine-500/40"
        >
          {paramDef.options?.map(opt => (
            <option key={opt.value} value={opt.value}>{opt.label}</option>
          ))}
        </select>
      )

    case 'string':
      return (
        <input
          type="text"
          value={String(currentValue)}
          onChange={e => handleChange(e.target.value)}
          className="w-full px-1.5 py-0.5 text-[10px] font-mono bg-white/5 border border-white/10 rounded text-gray-300 outline-none focus:border-marine-500/40"
        />
      )

    case 'distribution':
      return (
        <DistributionEditor
          value={typeof currentValue === 'object' ? currentValue : { type: 'normal', mean: 0, std: 1 }}
          onChange={handleChange}
        />
      )

    default:
      return <span className="text-[10px] text-gray-500">{JSON.stringify(currentValue)}</span>
  }
}
