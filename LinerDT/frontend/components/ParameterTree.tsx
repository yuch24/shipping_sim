'use client'

import { useState } from 'react'
import ParameterEditor from './ParameterEditor'

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

interface AgentTypeSchema {
  label: string
  parameters: ParamDef[]
}

interface ParameterTreeProps {
  schema: Record<string, AgentTypeSchema> | null
  values: Record<string, any>
  onChange: (agentType: string, key: string, value: any) => void
}

function ParamNode({
  paramDef,
  depth,
  value,
  onChange,
}: {
  paramDef: ParamDef
  depth: number
  value: any
  onChange: (key: string, value: any) => void
}) {
  const [expanded, setExpanded] = useState(depth < 1)
  const hasChildren = paramDef.children && paramDef.children.length > 0

  if (hasChildren) {
    return (
      <div>
        <button
          onClick={() => setExpanded(!expanded)}
          className="flex items-center gap-1 py-0.5 w-full text-left hover:bg-white/5 rounded px-1"
        >
          <svg
            className={`w-2.5 h-2.5 text-gray-500 transition-transform ${expanded ? 'rotate-90' : ''}`}
            fill="none" viewBox="0 0 24 24" stroke="currentColor"
          >
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
          </svg>
          <span className="text-[10px] font-medium text-gray-300">{paramDef.label}</span>
        </button>
        {expanded && (
          <div className="ml-3 border-l border-white/5 pl-2 space-y-0.5">
            {(paramDef.children || []).map(child => (
              <ParamNode
                key={child.key}
                paramDef={child}
                depth={depth + 1}
                value={value}
                onChange={onChange}
              />
            ))}
          </div>
        )}
      </div>
    )
  }

  return (
    <div className="flex items-center justify-between gap-2 py-0.5 px-1 hover:bg-white/5 rounded">
      <div className="flex items-center gap-1 min-w-0">
        <span className="text-[10px] text-gray-400 truncate">{paramDef.label}</span>
        {paramDef.description && (
          <span
            className="text-[9px] text-gray-600 cursor-help"
            title={paramDef.description}
          >ⓘ</span>
        )}
      </div>
      <div className="shrink-0 min-w-0" style={{ width: 80 }}>
        <ParameterEditor paramDef={paramDef} value={value} onChange={onChange} />
      </div>
    </div>
  )
}

export default function ParameterTree({ schema, values, onChange }: ParameterTreeProps) {
  const [expandedTypes, setExpandedTypes] = useState<Record<string, boolean>>({})

  if (!schema) {
    return (
      <div className="flex items-center justify-center py-8">
        <div className="animate-spin w-4 h-4 border-2 border-marine-500 border-t-transparent rounded-full" />
        <span className="ml-2 text-[10px] text-gray-500">加载参数定义...</span>
      </div>
    )
  }

  return (
    <div className="space-y-1">
      {Object.entries(schema).map(([typeKey, typeSchema]) => {
        const isExpanded = expandedTypes[typeKey] ?? true
        return (
          <div key={typeKey} className="border border-white/5 rounded overflow-hidden">
            <button
              onClick={() => setExpandedTypes(prev => ({ ...prev, [typeKey]: !isExpanded }))}
              className="w-full flex items-center justify-between px-2 py-1.5 bg-white/[0.03] hover:bg-white/[0.06] text-left"
            >
              <span className="text-[11px] font-medium text-gray-200">{typeSchema.label}</span>
              <svg
                className={`w-3 h-3 text-gray-500 transition-transform ${isExpanded ? 'rotate-180' : ''}`}
                fill="none" viewBox="0 0 24 24" stroke="currentColor"
              >
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
              </svg>
            </button>
            {isExpanded && (
              <div className="p-2 space-y-0.5">
                {typeSchema.parameters.map(param => (
                  <ParamNode
                    key={param.key}
                    paramDef={param}
                    depth={0}
                    value={values[param.key]}
                    onChange={(key, val) => onChange(typeKey, key, val)}
                  />
                ))}
              </div>
            )}
          </div>
        )
      })}
    </div>
  )
}
