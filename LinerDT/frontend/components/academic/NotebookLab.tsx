'use client'

import { useState, useEffect, useCallback } from 'react'

interface Props {
  onOpenResult?: (title: string, content: React.ReactNode) => void
}

const DEFAULT_CODE = `# LinerDT 交互式计算脚本
# 使用 sim_context 对象访问仿真状态

# 获取当前仿真时间
current_time = sim_context.get_time()
print(f"当前仿真时间: Day {current_time // 24 + 1}")

# 获取所有船舶数据
ships = sim_context.get_ships()
print(f"在航船舶: {len(ships)} 艘")

# 计算平均航速
avg_speed = sum(s['current_speed'] for s in ships) / len(ships)
print(f"平均航速: {avg_speed:.2f} kn")

# 分析延误分布
delays = [s.get('delay', 0) for s in ships]
print(f"最大延误: {max(delays):.1f} h")
print(f"平均延误: {sum(delays)/len(delays):.1f} h")
`

export default function NotebookLab({ onOpenResult }: Props) {
  const [code, setCode] = useState(DEFAULT_CODE)
  const [output, setOutput] = useState('')
  const [running, setRunning] = useState(false)
  const [templates, setTemplates] = useState<any[]>([])
  const [showTemplates, setShowTemplates] = useState(false)

  useEffect(() => {
    fetch('/api/academic-lab/notebook/templates')
      .then(r => r.json())
      .then(data => setTemplates(data.templates || []))
      .catch(() => {})
  }, [])

  const handleRun = useCallback(async () => {
    setRunning(true)
    setOutput('>>> 执行中...\n')
    try {
      const res = await fetch('/api/academic-lab/notebook/execute', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ script: code }),
      })
      const data = await res.json()
      if (data.status === 'success') {
        setOutput(data.output || '(无输出)')
      } else {
        setOutput(`>>> 错误\n\n${data.error || '执行失败'}`)
      }
    } catch (e) {
      setOutput(`>>> 网络错误: ${e}`)
    }
    setRunning(false)
  }, [code])

  const loadTemplate = useCallback((tmpl: any) => {
    setCode(tmpl.code)
    setShowTemplates(false)
  }, [])

  return (
    <div className="h-full flex flex-col">
      {/* 工具栏 */}
      <div className="flex items-center gap-2 pl-4 pr-2 py-1.5 border-b border-white/10 shrink-0">
        <button
          onClick={handleRun}
          disabled={running}
          className="flex items-center gap-1 px-3 py-1 text-[11px] font-medium bg-green-600 hover:bg-green-500 disabled:bg-gray-700 disabled:text-gray-500 text-white rounded transition-colors"
        >
          <svg className="w-3 h-3" fill="currentColor" viewBox="0 0 24 24">
            <path d="M8 5v14l11-7z" />
          </svg>
          运行
        </button>

        <div className="relative">
          <button
            onClick={() => setShowTemplates(!showTemplates)}
            className="px-2 py-1 text-[10px] text-gray-400 hover:text-white bg-white/5 hover:bg-white/10 rounded transition-colors"
          >
            脚本模板 ▾
          </button>
          {showTemplates && (
            <div className="absolute bottom-full mb-1 left-0 w-56 bg-[#0d1e30] border border-white/10 rounded-lg shadow-xl overflow-hidden z-10">
              {templates.map((t: any) => (
                <button
                  key={t.id}
                  onClick={() => loadTemplate(t)}
                  className="w-full text-left px-3 py-2 text-[11px] text-gray-400 hover:bg-white/5 hover:text-white transition-colors border-b border-white/5 last:border-0"
                >
                  <div className="font-medium">{t.name}</div>
                  <div className="text-[10px] text-gray-600">{t.description}</div>
                </button>
              ))}
              {templates.length === 0 && (
                <div className="px-3 py-2 text-[10px] text-gray-600">加载中...</div>
              )}
            </div>
          )}
        </div>

        <div className="w-px h-3 bg-white/10" />
        <span className="text-[10px] text-gray-600">Python 3 · 后端沙箱执行</span>
        <div className="flex-1" />
        <span className="text-[10px] text-gray-600">可用: sim_context · math · numpy · json</span>
      </div>

      {/* 编辑器 + 输出 */}
      <div className="flex-1 flex justify-center overflow-hidden">
        <div className="w-full max-w-4xl grid grid-cols-2 gap-0 h-full">
          <div className="border-r border-white/10">
            <textarea
              value={code}
              onChange={(e) => setCode(e.target.value)}
              className="w-full h-full bg-transparent text-[12px] font-mono text-gray-300 p-4 resize-none outline-none"
              spellCheck={false}
            />
          </div>
          <div className="p-4 overflow-auto bg-[#080f1a]">
            <pre className="text-[12px] font-mono text-gray-400 whitespace-pre-wrap">
              {output || (
                <span className="text-gray-600">点击「运行」在服务端执行脚本...</span>
              )}
            </pre>
          </div>
        </div>
      </div>
    </div>
  )
}
