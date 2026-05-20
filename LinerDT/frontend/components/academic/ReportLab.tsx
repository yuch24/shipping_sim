'use client'

import { useState, useEffect } from 'react'

interface Props {
  onOpenResult?: (title: string, content: React.ReactNode) => void
}

const TEMPLATES = [
  { id: 'ieee', name: 'IEEE 会议', desc: '双栏排版, 适合技术论文' },
  { id: 'transport', name: 'Transportation Science', desc: 'INFORMS 期刊格式' },
  { id: 'mel', name: 'Maritime Economics & Logistics', desc: 'Springer 期刊格式' },
  { id: 'simple', name: '简明报告', desc: '单栏 Markdown 格式' },
]

const SECTIONS = [
  { id: 'abstract', label: '包含摘要', desc: '自动生成论文摘要' },
  { id: 'method', label: '包含方法描述', desc: 'DES 建模方法与参数设置' },
  { id: 'results', label: '包含实验结果', desc: 'KPI 图表与统计检验结果' },
  { id: 'sensitivity', label: '包含敏感性分析', desc: 'Tornado 图与 Morris 方法' },
  { id: 'conclusion', label: '包含结论', desc: '研究发现与未来工作' },
]

export default function ReportLab({ onOpenResult }: Props) {
  const [selectedTemplate, setSelectedTemplate] = useState('simple')
  const [selectedSections, setSelectedSections] = useState<string[]>(SECTIONS.map(s => s.id))
  const [generating, setGenerating] = useState(false)
  const [lastResult, setLastResult] = useState<any>(null)

  const toggleSection = (id: string) => {
    setSelectedSections(prev =>
      prev.includes(id) ? prev.filter(s => s !== id) : [...prev, id]
    )
  }

  const handleGenerate = async () => {
    setGenerating(true)
    try {
      const res = await fetch('/api/academic-lab/report/generate', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          template_id: selectedTemplate,
          sections: selectedSections,
        }),
      })
      const data = await res.json()
      setLastResult(data)

      if (onOpenResult) {
        const isLatex = data.format === 'latex'
        onOpenResult(`报告生成 — ${TEMPLATES.find(t => t.id === selectedTemplate)?.name}`, (
          <div className="space-y-3">
            <div className="flex items-center gap-2">
              <span className="text-[10px] bg-marine-500/10 text-marine-400 px-2 py-0.5 rounded">
                {data.format?.toUpperCase()}
              </span>
              {data.filename && (
                <span className="text-[10px] text-gray-500">{data.filename}</span>
              )}
            </div>
            <div className="bg-[#0a1929] rounded p-3 text-[11px] font-mono text-gray-400 leading-relaxed max-h-64 overflow-auto border border-white/5">
              {isLatex ? (
                <LatexPreview content={data.content} />
              ) : (
                data.content?.split('\n').map((line: string, i: number) => (
                  <div key={i} className="whitespace-pre-wrap">{line}</div>
                ))
              )}
            </div>
            <div className="text-[10px] text-gray-500">
              {isLatex
                ? '💡 复制 .tex 内容到 Overleaf 或本地 LaTeX 编译为 PDF'
                : '💡 Markdown 可直接复制到论文/报告中'}
            </div>
          </div>
        ))
      }
    } catch { /* ignore */ }
    setGenerating(false)
  }

  return (
    <div className="h-full overflow-auto p-4">
      <div className="max-w-4xl mx-auto space-y-4">
        {/* 模板选择 */}
        <div>
          <h3 className="text-xs font-medium text-gray-400 mb-2 flex items-center gap-1.5">
            <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
            </svg>
            报告模板
          </h3>
          <div className="grid grid-cols-4 gap-2">
            {TEMPLATES.map((t) => (
              <button
                key={t.id}
                onClick={() => setSelectedTemplate(t.id)}
                className={`p-3 rounded-lg border transition-all text-left ${
                  selectedTemplate === t.id
                    ? 'bg-marine-500/10 border-marine-500/30'
                    : 'bg-white/5 border-white/10 hover:border-white/20'
                }`}
              >
                <p className="text-xs font-medium text-gray-300">{t.name}</p>
                <p className="text-[10px] text-gray-500 mt-0.5">{t.desc}</p>
              </button>
            ))}
          </div>
        </div>

        {/* 章节配置 */}
        <div className="bg-white/5 rounded-lg border border-white/10 p-4">
          <h3 className="text-xs font-medium text-gray-400 mb-3">报告章节</h3>
          <div className="space-y-2">
            {SECTIONS.map((s) => (
              <label key={s.id} className="flex items-center gap-2 cursor-pointer group">
                <input
                  type="checkbox"
                  checked={selectedSections.includes(s.id)}
                  onChange={() => toggleSection(s.id)}
                  className="w-3 h-3 accent-marine-500"
                />
                <div>
                  <span className="text-[11px] text-gray-300 group-hover:text-white transition-colors">{s.label}</span>
                  <span className="text-[10px] text-gray-600 ml-2">{s.desc}</span>
                </div>
              </label>
            ))}
          </div>
        </div>

        {/* 生成按钮 */}
        <div className="flex items-center gap-3">
          <button
            onClick={handleGenerate}
            disabled={generating}
            className="px-4 py-1.5 text-xs font-medium bg-marine-500 hover:bg-marine-400 disabled:bg-gray-700 disabled:text-gray-500 text-white rounded-lg transition-colors"
          >
            {generating ? (
              <span className="flex items-center gap-1.5">
                <svg className="w-3 h-3 animate-spin" viewBox="0 0 24 24" fill="none">
                  <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                  <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
                </svg>
                生成中...
              </span>
            ) : '📄 生成报告'}
          </button>
          <span className="text-[10px] text-gray-600">
            输出格式: <span className="text-gray-500">LaTeX · Markdown</span>
          </span>
        </div>

        {/* 预览 */}
        <div className="bg-white/5 rounded-lg border border-white/10 p-4">
          <h3 className="text-xs font-medium text-gray-400 mb-2">LaTeX 预览</h3>
          <div className="bg-[#0a1929] rounded p-4 text-[11px] font-mono text-gray-400 leading-relaxed overflow-auto max-h-40">
            <span className="text-purple-400">\documentclass</span>{'{article}'}{'\n'}
            <span className="text-purple-400">\usepackage</span>{'{amsmath, amssymb}'}{'\n'}
            <span className="text-purple-400">\title</span>{'{LinerDT 仿真实验报告}'}{'\n'}
            <span className="text-purple-400">\begin</span>{'{document}'}{'\n'}
            {'  '}<span className="text-purple-400">\maketitle</span>{'\n'}
            {'  '}<span className="text-purple-400">\section</span>{'{实验配置}'}{'\n'}
            {'  '}<span className="text-purple-400">\section</span>{'{仿真结果}'}{'\n'}
            {'    '}<span className="text-purple-400">\subsection</span>{'{KPI 分析}'}{'\n'}
            {'      '}准班率: 92.3\%{'\n'}
            {'    '}<span className="text-purple-400">\subsection</span>{'{统计检验}'}{'\n'}
            {'      '}$t = 3.24, p &lt; 0.01${'\n'}
            <span className="text-purple-400">\end</span>{'{document}'}
          </div>
        </div>
      </div>
    </div>
  )
}

function LatexPreview({ content }: { content: string }) {
  const lines = content.split('\n')
  return (
    <>
      {lines.map((line, i) => {
        // 简单语法高亮
        if (line.startsWith('\\')) {
          const cmdMatch = line.match(/\\(\w+)/)
          return (
            <div key={i} className="whitespace-pre-wrap">
              {cmdMatch ? (
                <>
                  <span className="text-purple-400">\{cmdMatch[1]}</span>
                  <span className="text-gray-400">{line.slice(cmdMatch[1].length + 1)}</span>
                </>
              ) : (
                <span className="text-gray-400">{line}</span>
              )}
            </div>
          )
        }
        return <div key={i} className="whitespace-pre-wrap text-gray-400">{line}</div>
      })}
    </>
  )
}
