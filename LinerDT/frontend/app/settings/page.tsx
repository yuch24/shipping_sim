'use client'

import { useState, useEffect } from 'react'

interface LLMConfig {
  apiKey: string
  baseUrl: string
  model: string
}

export default function SettingsPage() {
  const [config, setConfig] = useState<LLMConfig>({
    apiKey: '',
    baseUrl: 'https://api.openai.com/v1',
    model: 'gpt-4',
  })
  const [status, setStatus] = useState<string>('')
  const [isConfigured, setIsConfigured] = useState(false)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    const checkConfig = async () => {
      try {
        const res = await fetch('/api/ai/config')
        const data = await res.json()
        setIsConfigured(data.configured || false)
      } catch {
        setIsConfigured(false)
      } finally {
        setLoading(false)
      }
    }
    checkConfig()
  }, [])

  const handleSave = async () => {
    setStatus('保存中...')
    try {
      const res = await fetch('/api/ai/config', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(config),
      })
      const data = await res.json()
      setIsConfigured(data.configured || false)
      setStatus(data.configured ? '✅ 配置已保存' : '❌ 配置保存失败')
    } catch (e: unknown) {
      setStatus(`❌ 错误: ${e instanceof Error ? e.message : String(e)}`)
    }
  }

  if (loading) {
    return (
      <div className="min-h-screen bg-gray-950 text-white p-8">
        <div className="max-w-2xl mx-auto">
          <div className="text-gray-400">加载中...</div>
        </div>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-gray-950 text-white p-8">
      <div className="max-w-2xl mx-auto">
        <div className="flex items-center justify-between mb-8">
          <div>
            <h1 className="text-2xl font-bold">设置</h1>
            <p className="text-gray-400 text-sm mt-1">配置 LLM 和系统参数</p>
          </div>
          <div className={`px-3 py-1 rounded text-sm ${isConfigured ? 'bg-green-500/20 text-green-400' : 'bg-yellow-500/20 text-yellow-400'}`}>
            {isConfigured ? '✅ AI 已配置' : '⚠️ AI 未配置'}
          </div>
        </div>

        <div className="space-y-6">
          <div className="bg-gray-900 border border-gray-800 rounded-lg p-6">
            <h2 className="text-lg font-medium mb-4">🤖 AI 助手设置</h2>

            <div className="space-y-4">
              <div>
                <label className="block text-sm text-gray-400 mb-2">API Key</label>
                <input
                  type="password"
                  value={config.apiKey}
                  onChange={(e) => setConfig({ ...config, apiKey: e.target.value })}
                  placeholder="sk-..."
                  className="w-full px-4 py-2 bg-gray-800 border border-gray-700 rounded-lg text-white focus:outline-none focus:border-blue-500"
                />
                <p className="text-xs text-gray-500 mt-1">支持 OpenAI API Key 或兼容接口（如 Groq, DeepSeek 等）</p>
              </div>

              <div>
                <label className="block text-sm text-gray-400 mb-2">Base URL</label>
                <input
                  type="text"
                  value={config.baseUrl}
                  onChange={(e) => setConfig({ ...config, baseUrl: e.target.value })}
                  placeholder="https://api.openai.com/v1"
                  className="w-full px-4 py-2 bg-gray-800 border border-gray-700 rounded-lg text-white focus:outline-none focus:border-blue-500"
                />
                <p className="text-xs text-gray-500 mt-1">OpenAI API 或兼容接口地址</p>
              </div>

              <div>
                <label className="block text-sm text-gray-400 mb-2">模型</label>
                <input
                  type="text"
                  value={config.model}
                  onChange={(e) => setConfig({ ...config, model: e.target.value })}
                  placeholder="gpt-4"
                  className="w-full px-4 py-2 bg-gray-800 border border-gray-700 rounded-lg text-white focus:outline-none focus:border-blue-500"
                />
                <p className="text-xs text-gray-500 mt-1">例如: gpt-4, gpt-3.5-turbo, mixtral-8x7b-32768</p>
              </div>

              {status && (
                <div className={`text-sm ${status.includes('✅') ? 'text-green-400' : 'text-red-400'}`}>
                  {status}
                </div>
              )}

              <button
                onClick={handleSave}
                className="w-full py-2.5 bg-blue-600 hover:bg-blue-700 text-white rounded-lg transition-colors"
              >
                保存配置
              </button>
            </div>
          </div>

          <div className="bg-gray-900 border border-gray-800 rounded-lg p-6">
            <h2 className="text-lg font-medium mb-4">💬 AI 助手功能</h2>
            <div className="space-y-2 text-sm text-gray-400">
              <div className="flex items-start gap-2">
                <span className="text-blue-400">•</span>
                <span>查询船舶状态（位置、航速、延误情况）</span>
              </div>
              <div className="flex items-start gap-2">
                <span className="text-blue-400">•</span>
                <span>查询港口状态（泊位占用、排队情况）</span>
              </div>
              <div className="flex items-start gap-2">
                <span className="text-blue-400">•</span>
                <span>查询全局运营概览</span>
              </div>
              <div className="flex items-start gap-2">
                <span className="text-blue-400">•</span>
                <span>分析 KPI 趋势（准班率、碳排放）</span>
              </div>
              <div className="flex items-start gap-2">
                <span className="text-blue-400">•</span>
                <span>解释 AI Agent 的决策逻辑</span>
              </div>
            </div>
          </div>

          <div className="bg-gray-900 border border-gray-800 rounded-lg p-6">
            <h2 className="text-lg font-medium mb-4">⌨️ 快捷命令示例</h2>
            <div className="space-y-3 font-mono text-sm">
              <div className="bg-gray-800 p-3 rounded">
                <div className="text-gray-400 mb-1">查询船舶状态</div>
                <div className="text-green-400">"s001 现在在哪里？"</div>
              </div>
              <div className="bg-gray-800 p-3 rounded">
                <div className="text-gray-400 mb-1">查询港口状态</div>
                <div className="text-green-400">"新加坡港的排队情况如何？"</div>
              </div>
              <div className="bg-gray-800 p-3 rounded">
                <div className="text-gray-400 mb-1">查询 KPI</div>
                <div className="text-green-400">"最近12小时的准班率是多少？"</div>
              </div>
              <div className="bg-gray-800 p-3 rounded">
                <div className="text-gray-400 mb-1">查询碳排放</div>
                <div className="text-green-400">"显示各船舶的碳排放排名"</div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
