'use client'

import { useState, useEffect, useRef, useCallback } from 'react'
import { useAIChat, ChatMessage } from '@/hooks/useAIChat'
import type { AIDecision } from '@/types/simulation'
import AgentConfigEditor from './AgentConfigEditor'

interface AIChatPanelProps {
  isOpen: boolean
  onClose: () => void
  onNavigate?: (targetType: string, targetId: string) => void
  // AI 决策日志
  aiDecisions?: AIDecision[]
  onClearDecisions?: () => void
  sidebarMode?: boolean // 在侧边栏中使用时启用，避免 fixed 定位遮住顶部栏
}

type PanelMode = 'chat' | 'agent'

const DECISION_TYPE_LABELS: Record<string, string> = {
  ai_speed_decision: '航速决策',
  speed_decision: '航速调整',
  fuel_switch: '燃油切换',
  arrive_port: '到港',
  depart_port: '离港',
  request_berth: '申请泊位',
  berth_granted: '获分配泊位',
  berth_released: '释放泊位',
}

const DECISION_TYPE_COLORS: Record<string, string> = {
  ai_speed_decision: 'border-l-blue-500',
  speed_decision: 'border-l-blue-400',
  fuel_switch: 'border-l-green-500',
  arrive_port: 'border-l-yellow-500',
  depart_port: 'border-l-yellow-400',
  request_berth: 'border-l-purple-500',
  berth_granted: 'border-l-purple-400',
  berth_released: 'border-l-gray-500',
}

export default function AIChatPanel({
  isOpen, onClose, onNavigate,
  aiDecisions = [],
  onClearDecisions,
  sidebarMode = false,
}: AIChatPanelProps) {
  const [mode, setMode] = useState<PanelMode>('chat')
  const [input, setInput] = useState('')
  const [showSettings, setShowSettings] = useState(false)
  const [showQuickActions, setShowQuickActions] = useState(false)
  const [settings, setSettings] = useState({
    apiKey: '',
    baseUrl: 'https://api.openai.com/v1',
    model: 'gpt-4',
  })
  const messagesEndRef = useRef<HTMLDivElement>(null)
  const inputRef = useRef<HTMLInputElement>(null)
  const [expandedDecision, setExpandedDecision] = useState<string | null>(null)
  const [decisionFilter, setDecisionFilter] = useState<string>('all')

  const {
    messages,
    isLoading,
    error,
    isConfigured,
    sendMessage,
    clearMessages,
    checkConfig,
    updateConfig,
    currentToolCall,
  } = useAIChat()

  useEffect(() => {
    checkConfig()
  }, [checkConfig])

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  useEffect(() => {
    if (isOpen && isConfigured && mode === 'chat') {
      inputRef.current?.focus()
    }
  }, [isOpen, isConfigured, mode])

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!input.trim() || isLoading) return
    const msg = input
    setInput('')
    await sendMessage(msg)
  }

  const handleSaveSettings = async () => {
    await updateConfig(settings)
    setShowSettings(false)
  }

  const handleQuickAction = (action: string) => {
    setInput(action)
    setShowQuickActions(false)
    inputRef.current?.focus()
  }

  const formatContent = (content: string) => {
    return content
      .replace(/\*\*(.*?)\*\*/g, '<strong class="text-white">$1</strong>')
      .replace(/`(.*?)`/g, '<code class="bg-slate-700/50 text-cyan-300 px-1.5 py-0.5 rounded text-xs">$1</code>')
      .replace(/^### (.*$)/gm, '<h4 class="text-white font-semibold mt-3 mb-1">$1</h4>')
      .replace(/^## (.*$)/gm, '<h3 class="text-white font-bold mt-3 mb-1 text-sm">$1</h3>')
      .replace(/^- (.*$)/gm, '<div class="flex gap-1.5 ml-1"><span class="text-marine-400">•</span><span>$1</span></div>')
      .replace(/\n/g, '<br/>')
  }

  if (!isOpen) return null

  return (
    <div className={`${sidebarMode ? 'h-full' : 'fixed right-0 top-0 bottom-0'} ${sidebarMode ? 'w-full' : 'w-[420px]'} glass-panel flex flex-col ${sidebarMode ? '' : 'shadow-2xl z-50 border-l border-white/10 animate-slide-in-right'}`}>
      {/* ===== 顶部：标题 + 标签切换 + 操作按钮 ===== */}
      <div className="shrink-0">
        {/* 标题栏 */}
        <div className="flex items-center justify-between px-4 pt-4 pb-2">
          <div className="flex items-center gap-2">
            <div className="w-7 h-7 rounded-lg bg-gradient-to-br from-marine-500 to-cyan-500 flex items-center justify-center">
              <svg className="w-4 h-4 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9.75 17L9 20l-1 1h8l-1-1-.75-3M3 13h18M5 17h14a2 2 0 002-2V5a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z" />
              </svg>
            </div>
            <div className="font-semibold text-white text-sm">AI 助手</div>
          </div>
          <div className="flex gap-1">
            {mode === 'chat' && (
              <>
                <button
                  onClick={() => setShowQuickActions(!showQuickActions)}
                  className="p-1.5 text-gray-400 hover:text-white hover:bg-white/10 rounded-md transition-colors"
                  title="快捷操作"
                >
                  <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 10V3L4 14h7v7l9-11h-7z" />
                  </svg>
                </button>
                <button
                  onClick={() => setShowSettings(!showSettings)}
                  className="p-1.5 text-gray-400 hover:text-white hover:bg-white/10 rounded-md transition-colors"
                  title="设置"
                >
                  <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z" />
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
                  </svg>
                </button>
              </>
            )}
            <button
              onClick={onClose}
              className="p-1.5 text-gray-400 hover:text-white hover:bg-white/10 rounded-md transition-colors"
              title="关闭"
            >
              <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>
          </div>
        </div>

        {/* 模式切换标签 */}
        <div className="flex mx-3 mb-2 bg-white/5 rounded-lg p-0.5">
          <button
            onClick={() => setMode('chat')}
            className={`flex-1 text-xs font-medium py-1.5 rounded-md transition-all duration-200 ${
              mode === 'chat'
                ? 'bg-marine-500/20 text-marine-400 shadow-sm'
                : 'text-gray-500 hover:text-gray-300'
            }`}
          >
            <div className="flex items-center justify-center gap-1.5">
              <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 10h.01M12 10h.01M16 10h.01M9 16H5a2 2 0 01-2-2V6a2 2 0 012-2h14a2 2 0 012 2v8a2 2 0 01-2 2h-5l-5 5v-5z" />
              </svg>
              对话
            </div>
          </button>
          <button
            onClick={() => setMode('agent')}
            className={`flex-1 text-xs font-medium py-1.5 rounded-md transition-all duration-200 ${
              mode === 'agent'
                ? 'bg-cyan-500/20 text-cyan-400 shadow-sm'
                : 'text-gray-500 hover:text-gray-300'
            }`}
          >
            <div className="flex items-center justify-center gap-1.5">
              <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 6V4m0 2a2 2 0 100 4m0-4a2 2 0 110 4m-6 8a2 2 0 100-4m0 4a2 2 0 110-4m0 4v2m0-6V4m6 6v10m6-2a2 2 0 100-4m0 4a2 2 0 110-4m0 4v2m0-6V4" />
              </svg>
              Agent
            </div>
          </button>
        </div>
      </div>

      {/* ===== 对话模式 ===== */}
      {mode === 'chat' ? (
        <>
          {/* 设置面板 */}
          {showSettings && (
            <div className="p-4 border-b border-white/10 bg-white/[0.02] space-y-3 shrink-0">
              <div>
                <label className="block text-xs text-gray-400 mb-1">API Key</label>
                <input
                  type="password"
                  value={settings.apiKey}
                  onChange={(e) => setSettings({ ...settings, apiKey: e.target.value })}
                  placeholder="sk-..."
                  className="w-full bg-white/5 border border-white/10 rounded-lg px-3 py-2 text-sm text-white placeholder-gray-500 focus:outline-none focus:border-marine-500 transition-colors"
                />
              </div>
              <div>
                <label className="block text-xs text-gray-400 mb-1">Base URL</label>
                <input
                  type="text"
                  value={settings.baseUrl}
                  onChange={(e) => setSettings({ ...settings, baseUrl: e.target.value })}
                  placeholder="https://api.openai.com/v1"
                  className="w-full bg-white/5 border border-white/10 rounded-lg px-3 py-2 text-sm text-white placeholder-gray-500 focus:outline-none focus:border-marine-500 transition-colors"
                />
              </div>
              <div>
                <label className="block text-xs text-gray-400 mb-1">Model</label>
                <input
                  type="text"
                  value={settings.model}
                  onChange={(e) => setSettings({ ...settings, model: e.target.value })}
                  placeholder="gpt-4"
                  className="w-full bg-white/5 border border-white/10 rounded-lg px-3 py-2 text-sm text-white placeholder-gray-500 focus:outline-none focus:border-marine-500 transition-colors"
                />
              </div>
              <button onClick={handleSaveSettings} className="w-full bg-marine-500 hover:bg-marine-600 text-white rounded-lg py-2 text-sm font-medium transition-colors">
                保存配置
              </button>
            </div>
          )}

          {/* 快捷操作 */}
          {showQuickActions && (
            <div className="p-3 border-b border-white/10 bg-white/[0.02] shrink-0">
              <div className="text-[10px] text-gray-500 mb-2 uppercase tracking-wider">快捷操作</div>
              <div className="grid grid-cols-2 gap-1.5">
                {[
                  { label: '船队概览', query: '现在的船队整体情况如何？' },
                  { label: '瓶颈检测', query: '分析一下当前的系统瓶颈' },
                  { label: '综合诊断', query: '当前有哪些需要关注的问题？' },
                  { label: '延误检查', query: '有没有严重延误的船？' },
                  { label: '港口拥堵', query: '哪些港口拥堵？什么原因？' },
                  { label: '优化建议', query: '有什么优化建议？' },
                ].map((item) => (
                  <button
                    key={item.label}
                    onClick={() => handleQuickAction(item.query)}
                    className="text-left px-2.5 py-2 rounded-lg bg-white/5 hover:bg-white/10 text-xs text-gray-300 hover:text-white transition-colors truncate"
                  >
                    {item.label}
                  </button>
                ))}
              </div>
            </div>
          )}

          {/* 消息列表 */}
          <div className="flex-1 overflow-y-auto p-4 space-y-4">
            {messages.length === 0 && !isLoading && (
              <div className="text-center text-gray-500 py-12">
                <div className="w-16 h-16 mx-auto mb-4 rounded-2xl bg-gradient-to-br from-marine-500/20 to-cyan-500/20 flex items-center justify-center">
                  <svg className="w-8 h-8 text-marine-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M8 10h.01M12 10h.01M16 10h.01M9 16H5a2 2 0 01-2-2V6a2 2 0 012-2h14a2 2 0 012 2v8a2 2 0 01-2 2h-5l-5 5v-5z" />
                  </svg>
                </div>
                <div className="text-sm font-medium text-gray-300 mb-1">LinerDT AI 航运助手</div>
                <div className="text-xs text-gray-500 mb-4">
                  你可以用自然语言查询、分析和控制仿真
                </div>
                <div className="space-y-1.5 text-xs text-gray-600">
                  <div>「S003 的综合运营表现如何？」</div>
                  <div>「帮我分析瓶颈在哪里」</div>
                  <div>「把 S007 的航速降到 16 节」</div>
                </div>
              </div>
            )}

            {error && (
              <div className="bg-red-500/10 border border-red-500/30 rounded-lg p-3 text-red-400 text-sm">
                <div className="font-medium mb-1">错误</div>
                {error}
              </div>
            )}

            {messages.map((msg) => (
              <div key={msg.id} className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}>
                {msg.role === 'assistant' ? (
                  <div className="flex gap-2.5 max-w-[90%]">
                    <div className="w-7 h-7 rounded-lg bg-gradient-to-br from-marine-500 to-cyan-500 flex items-center justify-center shrink-0 mt-0.5">
                      <svg className="w-3.5 h-3.5 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9.75 17L9 20l-1 1h8l-1-1-.75-3M3 13h18M5 17h14a2 2 0 002-2V5a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z" />
                      </svg>
                    </div>
                    <div className="flex-1 min-w-0">
                      <div className="text-xs text-gray-500 mb-0.5">AI 助手</div>
                      {msg.toolCall && (
                        <div className="mb-2 px-2 py-1 bg-marine-500/10 border border-marine-500/20 rounded text-[10px] text-marine-400">
                          调用工具: {msg.toolCall.name}
                        </div>
                      )}
                      <div
                        className="text-sm text-gray-200 leading-relaxed [&_strong]:text-white [&_h3]:text-white [&_h4]:text-white"
                        dangerouslySetInnerHTML={{ __html: formatContent(msg.content) }}
                      />
                      {msg.toolCall?.result && (
                        <details className="mt-2">
                          <summary className="text-[10px] text-gray-500 cursor-pointer hover:text-gray-400">
                            查看工具返回数据
                          </summary>
                          <pre className="text-[10px] bg-black/30 p-2 rounded mt-1 overflow-x-auto max-h-32 whitespace-pre-wrap text-gray-400">
                            {msg.toolCall.result.length > 500
                              ? msg.toolCall.result.slice(0, 500) + '...'
                              : msg.toolCall.result}
                          </pre>
                        </details>
                      )}
                    </div>
                  </div>
                ) : msg.role === 'tool' ? (
                  <div className="max-w-[85%] px-3 py-1.5 bg-white/[0.02] border border-white/5 rounded-lg text-xs text-gray-500">
                    <span className="text-gray-600">Tool: </span>
                    {msg.content.slice(0, 200)}
                  </div>
                ) : (
                  <div className="max-w-[85%] rounded-2xl rounded-tr-md px-4 py-2.5 bg-marine-500/80 text-white text-sm">
                    {msg.content}
                  </div>
                )}
              </div>
            ))}

            {isLoading && (
              <div className="flex justify-start">
                <div className="flex gap-2.5 max-w-[90%]">
                  <div className="w-7 h-7 rounded-lg bg-gradient-to-br from-marine-500 to-cyan-500 flex items-center justify-center shrink-0">
                    <svg className="w-3.5 h-3.5 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9.75 17L9 20l-1 1h8l-1-1-.75-3M3 13h18M5 17h14a2 2 0 002-2V5a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z" />
                    </svg>
                  </div>
                  <div className="text-gray-400 text-sm py-1">
                    {currentToolCall ? (
                      <span className="text-marine-400 text-xs">
                        正在执行: {currentToolCall}...
                      </span>
                    ) : (
                      <span className="animate-pulse">AI 正在分析...</span>
                    )}
                  </div>
                </div>
              </div>
            )}

            <div ref={messagesEndRef} />
          </div>

          {/* 输入框 */}
          <form onSubmit={handleSubmit} className="p-4 border-t border-white/10 bg-white/[0.02] shrink-0">
            <div className="flex gap-2">
              <input
                ref={inputRef}
                type="text"
                value={input}
                onChange={(e) => setInput(e.target.value)}
                placeholder={isConfigured ? '输入消息... (Enter 发送)' : '请先配置 API Key'}
                disabled={!isConfigured || isLoading}
                className="flex-1 bg-white/5 border border-white/10 rounded-xl px-4 py-2.5 text-sm text-white placeholder-gray-500 focus:outline-none focus:border-marine-500 transition-colors disabled:opacity-50"
                onKeyDown={(e) => {
                  if (e.key === 'Enter' && !e.shiftKey) {
                    e.preventDefault()
                    handleSubmit(e)
                  }
                }}
              />
              <button
                type="submit"
                disabled={!isConfigured || isLoading || !input.trim()}
                className="bg-marine-500 hover:bg-marine-600 disabled:opacity-40 disabled:cursor-not-allowed text-white rounded-xl px-4 py-2.5 transition-colors"
              >
                <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 19l9 2-9-18-9 18 9-2zm0 0v-8" />
                </svg>
              </button>
            </div>
            {isConfigured && (
              <div className="mt-2 text-[10px] text-gray-600 text-center">
                基于实时仿真数据提供分析和建议
              </div>
            )}
          </form>
        </>
      ) : (
        /* ===== Agent 模式 ===== */
        <div className="flex-1 flex flex-col overflow-hidden">
          <div className="flex-1 overflow-y-auto">
            {/* Agent 配置编辑 */}
            <AgentConfigEditor />

            <div className="border-t border-white/10 mx-4" />

            {/* Agent 决策记录 */}
            <div>
              <div className="sticky top-0 bg-[#0d2137]/95 backdrop-blur-sm z-10 px-4 py-2">
                <div className="flex items-center justify-between mb-2">
                  <h3 className="text-xs font-semibold text-gray-300 uppercase tracking-wider">
                    Agent 决策记录
                    <span className="ml-2 text-[10px] text-gray-600 font-normal">{aiDecisions.length} 条</span>
                  </h3>
                  {aiDecisions.length > 0 && onClearDecisions && (
                    <button onClick={onClearDecisions} className="flex items-center gap-1 px-2 py-1 rounded-md text-[10px] text-red-400 hover:text-red-300 hover:bg-red-500/10 transition-colors" title="清除所有决策记录">
                      <svg className="w-3 h-3" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                      </svg>
                      清除
                    </button>
                  )}
                </div>
                <div className="flex gap-1 text-[10px]">
                  {[
                    { key: 'all', label: '全部' },
                    { key: 'ai_speed_decision', label: '航速' },
                    { key: 'fuel_switch', label: '燃油' },
                    { key: 'arrive_port', label: '港口' },
                  ].map(({ key, label }) => (
                    <button key={key} onClick={() => setDecisionFilter(key)}
                      className={`px-2 py-1 rounded-md transition-all ${decisionFilter === key ? 'bg-cyan-500/20 text-cyan-300' : 'bg-white/5 text-gray-500 hover:text-gray-300 hover:bg-white/10'}`}>
                      {label}
                    </button>
                  ))}
                </div>
              </div>
              <div className="p-3 space-y-1.5">
                {aiDecisions.length === 0 ? (
                  <div className="text-center text-gray-600 py-8 text-sm">
                    <div className="text-xs mt-1">启动仿真并启用 AI 后，Agent 决策将实时显示在此处</div>
                  </div>
                ) : (
                  [...aiDecisions].reverse().filter((d) => decisionFilter === 'all' || d.event === decisionFilter).slice(0, 100).map((decision: AIDecision, idx: number) => {
                    const entryId = decision._id || `dec-${idx}`
                    const eventType = decision.event || ''
                    const typeLabel = DECISION_TYPE_LABELS[eventType] || eventType
                    const borderColor = DECISION_TYPE_COLORS[eventType] || 'border-l-gray-500'
                    const isExpanded = expandedDecision === entryId
                    const day = Math.floor((decision.sim_time ?? 0) / 24)
                    const hour = (decision.sim_time ?? 0) % 24
                    return (
                      <div key={entryId} className={`border-l-2 ${borderColor} bg-white/[0.02] rounded-r-lg cursor-pointer transition-colors hover:bg-white/[0.04]`}
                        onClick={() => setExpandedDecision(isExpanded ? null : entryId)}>
                        <div className="px-3 py-2">
                          <div className="flex items-center gap-2 mb-0.5">
                            <span className="text-[10px] text-gray-600 font-mono shrink-0">D{day}H{hour.toFixed(0)}</span>
                            <span className="text-xs font-medium text-gray-200 truncate">{decision.ship_name || decision.ship_id || '未知船舶'}</span>
                            <span className="text-[10px] px-1.5 py-0.5 rounded-full bg-white/5 text-gray-500 shrink-0">{typeLabel}</span>
                          </div>
                          <p className="text-xs text-gray-400 line-clamp-1">{decision.reason || decision.summary || ''}</p>
                        </div>
                        {isExpanded && (
                          <div className="px-3 pb-3 border-t border-white/5 pt-2">
                            <div className="text-xs text-gray-300 space-y-1.5">
                              <div>
                                <span className="text-gray-500 text-[10px] font-medium">推理过程</span>
                                <p className="mt-0.5 text-gray-400 leading-relaxed">{decision.reason || '无详细推理'}</p>
                              </div>
                              {decision.context && Object.keys(decision.context).length > 0 && (
                                <div>
                                  <span className="text-gray-500 text-[10px] font-medium">决策上下文</span>
                                  <div className="mt-0.5 grid grid-cols-2 gap-1">
                                    {Object.entries(decision.context).map(([k, v]: [string, any]) => (
                                      <div key={k} className="bg-white/[0.03] rounded px-2 py-1">
                                        <span className="text-gray-600 text-[10px]">{k}: </span>
                                        <span className="text-gray-300 text-[10px] font-mono">{typeof v === 'number' ? v.toFixed(2) : String(v)}</span>
                                      </div>
                                    ))}
                                  </div>
                                </div>
                              )}
                              {decision.decision && (
                                <div className="flex items-center gap-2 pt-1">
                                  <span className="text-[10px] px-2 py-0.5 rounded-full bg-cyan-500/10 text-cyan-400 border border-cyan-500/20">{decision.decision}</span>
                                </div>
                              )}
                            </div>
                          </div>
                        )}
                      </div>
                    )
                  })
                )}
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
