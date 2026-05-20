'use client'

import { useState, useEffect } from 'react'

interface DistParam {
  name: string
  label: string
  type: string
  default?: number
  min?: number
  max?: number
  optional?: boolean
}

interface DistSchema {
  type: string
  label: string
  params: DistParam[]
}

interface DistributionEditorProps {
  value: Record<string, any>
  onChange: (dist: Record<string, any>) => void
}

const FALLBACK_SCHEMA: DistSchema[] = [
  { type: 'normal', label: '正态分布 N(μ, σ²)', params: [
    { name: 'mean', label: '均值 μ', type: 'float', default: 0 },
    { name: 'std', label: '标准差 σ', type: 'float', default: 1, min: 0 },
    { name: 'min', label: '下限', type: 'float', optional: true },
    { name: 'max', label: '上限', type: 'float', optional: true },
  ]},
  { type: 'uniform', label: '均匀分布 U(min, max)', params: [
    { name: 'low', label: '下限', type: 'float', default: 0 },
    { name: 'high', label: '上限', type: 'float', default: 1 },
  ]},
  { type: 'exponential', label: '指数分布 Exp(λ)', params: [
    { name: 'lambd', label: '率 λ', type: 'float', default: 1.0, min: 0 },
  ]},
  { type: 'triangular', label: '三角分布 T(min, mode, max)', params: [
    { name: 'low', label: '下限', type: 'float', default: 0 },
    { name: 'mode', label: '众数', type: 'float', default: 0.5 },
    { name: 'high', label: '上限', type: 'float', default: 1 },
  ]},
  { type: 'lognormal', label: '对数正态 LogN(μ, σ²)', params: [
    { name: 'mu', label: '均值 μ', type: 'float', default: 0 },
    { name: 'sigma', label: '标准差 σ', type: 'float', default: 1, min: 0 },
  ]},
  { type: 'weibull', label: '威布尔分布 W(shape, scale)', params: [
    { name: 'shape', label: '形状 k', type: 'float', default: 1.0, min: 0 },
    { name: 'scale', label: '尺度 λ', type: 'float', default: 1.0, min: 0 },
  ]},
  { type: 'bernoulli', label: '伯努利分布 B(p)', params: [
    { name: 'prob', label: '概率 p', type: 'float', default: 0.5, min: 0, max: 1 },
  ]},
  { type: 'constant', label: '常数 Constant(v)', params: [
    { name: 'value', label: '常数值', type: 'float', default: 0 },
  ]},
]

export default function DistributionEditor({ value, onChange }: DistributionEditorProps) {
  const [schema, setSchema] = useState<DistSchema[]>(FALLBACK_SCHEMA)
  const distType = value?.type || 'normal'
  const currentSchema = schema.find(s => s.type === distType) || schema[0]

  useEffect(() => {
    fetch('/api/sim/config/distributions-schema')
      .then(r => r.json())
      .then(setSchema)
      .catch(() => {})  // fallback to built-in
  }, [])

  const handleTypeChange = (newType: string) => {
    const newSchema = schema.find(s => s.type === newType)
    if (!newSchema) return
    const newDist: Record<string, any> = { type: newType }
    newSchema.params.forEach(p => {
      const existingVal = newType === distType ? value[p.name] : undefined
      newDist[p.name] = existingVal ?? p.default ?? 0
    })
    onChange(newDist)
  }

  const handleParamChange = (name: string, val: string) => {
    const parsed = val === '' ? 0 : parseFloat(val)
    onChange({ ...value, [name]: isNaN(parsed) ? 0 : parsed })
  }

  return (
    <div className="space-y-1.5">
      {/* 分布类型选择 */}
      <select
        value={distType}
        onChange={e => handleTypeChange(e.target.value)}
        className="w-full px-2 py-1 text-[10px] bg-white/5 border border-white/10 rounded text-gray-300 outline-none focus:border-marine-500/40"
      >
        {schema.map(s => (
          <option key={s.type} value={s.type}>{s.label}</option>
        ))}
      </select>

      {/* 分布参数 */}
      <div className="grid grid-cols-2 gap-x-2 gap-y-1">
        {currentSchema.params.map(p => {
          const currentVal = value[p.name] ?? p.default ?? 0
          return (
            <div key={p.name} className="flex items-center gap-1.5">
              <span className="text-[10px] text-gray-400 whitespace-nowrap min-w-[32px]">{p.label}</span>
              <input
                type="number"
                step={p.type === 'int' ? 1 : 0.01}
                min={p.min}
                max={p.max}
                value={currentVal}
                onChange={e => handleParamChange(p.name, e.target.value)}
                className="flex-1 px-1.5 py-0.5 text-[10px] font-mono bg-white/5 border border-white/10 rounded text-gray-300 outline-none focus:border-marine-500/40 w-0"
              />
            </div>
          )
        })}
      </div>
    </div>
  )
}
