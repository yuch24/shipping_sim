'use client'

import { useState, useCallback, useRef } from 'react'

export interface ChatMessage {
  id: string
  role: 'user' | 'assistant' | 'system' | 'tool'
  content: string
  toolCall?: {
    name: string
    result?: string
  }
  navigateAction?: {
    targetType: string
    targetId: string
  }
  timestamp: number
}

export interface AIConfig {
  apiKey: string
  baseUrl: string
  model: string
}

export function useAIChat() {
  const [messages, setMessages] = useState<ChatMessage[]>([])
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [isConfigured, setIsConfigured] = useState(false)
  const [currentToolCall, setCurrentToolCall] = useState<string | null>(null)
  const abortControllerRef = useRef<AbortController | null>(null)
  const messagesRef = useRef<ChatMessage[]>([])

  const checkConfig = useCallback(async () => {
    try {
      const res = await fetch('/api/ai/config')
      const data = await res.json()
      setIsConfigured(data.configured || false)
      return data.configured
    } catch {
      setIsConfigured(false)
      return false
    }
  }, [])

  const sendMessage = useCallback(async (content: string) => {
    if (!content.trim()) return

    const userMessage: ChatMessage = {
      id: `user-${Date.now()}`,
      role: 'user',
      content,
      timestamp: Date.now(),
    }

    setMessages((prev) => {
      const updated = [...prev, userMessage]
      messagesRef.current = updated
      return updated
    })
    setIsLoading(true)
    setError(null)
    setCurrentToolCall(null)

    const history = messagesRef.current.map((m) => ({
      role: m.role,
      content: m.content,
    }))

    try {
      const response = await fetch('/api/ai/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message: content, history }),
        signal: abortControllerRef.current?.signal,
      })

      if (!response.ok) {
        throw new Error(`HTTP error: ${response.status}`)
      }

      const reader = response.body?.getReader()
      if (!reader) throw new Error('No response body')

      const decoder = new TextDecoder()
      let assistantMessage: ChatMessage = {
        id: `assistant-${Date.now()}`,
        role: 'assistant',
        content: '',
        timestamp: Date.now(),
      }

      setMessages((prev) => {
        const updated = [...prev, assistantMessage]
        messagesRef.current = updated
        return updated
      })

      while (true) {
        const { done, value } = await reader.read()
        if (done) break

        const chunk = decoder.decode(value, { stream: true })
        const lines = chunk.split('\n')

        for (const line of lines) {
          if (line.startsWith('data: ')) {
            const data = line.slice(6).trim()
            if (data === '[DONE]') continue

            try {
              const parsed = JSON.parse(data)

              if (parsed.error) {
                setError(parsed.error)
                continue
              }

              if (parsed.tool_start) {
                setCurrentToolCall(parsed.tool_start)
                assistantMessage.toolCall = {
                  name: parsed.tool_start,
                }
                setMessages((prev) => {
                  const updated = [...prev]
                  const lastIdx = updated.length - 1
                  if (lastIdx >= 0 && updated[lastIdx].id === assistantMessage.id) {
                    updated[lastIdx] = { ...assistantMessage }
                  }
                  return updated
                })
              }

              if (parsed.content) {
                assistantMessage.content += parsed.content
                setMessages((prev) => {
                  const updated = [...prev]
                  const lastIdx = updated.length - 1
                  if (lastIdx >= 0 && updated[lastIdx].id === assistantMessage.id) {
                    updated[lastIdx] = { ...assistantMessage }
                  }
                  return updated
                })
              }

              if (parsed.action === 'navigate') {
                try {
                  const navData = JSON.parse(parsed.result || '{}')
                  assistantMessage.navigateAction = navData
                  setMessages((prev) => {
                    const updated = [...prev]
                    const lastIdx = updated.length - 1
                    if (lastIdx >= 0 && updated[lastIdx].id === assistantMessage.id) {
                      updated[lastIdx] = { ...assistantMessage }
                    }
                    return updated
                  })
                } catch {}
              }

              if (parsed.tool_result) {
                assistantMessage.toolCall = {
                  name: assistantMessage.toolCall?.name || 'unknown',
                  result: parsed.tool_result,
                }
                setMessages((prev) => {
                  const updated = [...prev]
                  const lastIdx = updated.length - 1
                  if (lastIdx >= 0 && updated[lastIdx].id === assistantMessage.id) {
                    updated[lastIdx] = { ...assistantMessage }
                  }
                  return updated
                })
              }
            } catch {
              continue
            }
          }
        }
      }
    } catch (e: unknown) {
      const errMsg = e instanceof Error ? e.message : String(e)
      if (e instanceof Error && e.name !== 'AbortError') {
        setError(errMsg)
      }
    } finally {
      setIsLoading(false)
    }
  }, []) // 使用 messagesRef 替代 messages 避免不必要的回调重建

  const abort = useCallback(() => {
    abortControllerRef.current?.abort()
    setIsLoading(false)
  }, [])

  const clearMessages = useCallback(() => {
    setMessages([])
    messagesRef.current = []
    setError(null)
  }, [])

  const updateConfig = useCallback(async (config: Partial<AIConfig>) => {
    try {
      // 前端使用驼峰命名，后端 API 使用下划线命名，需要做映射
      const res = await fetch('/api/ai/config', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          api_key: config.apiKey,
          base_url: config.baseUrl,
          model: config.model,
        }),
      })
      const data = await res.json()
      setIsConfigured(data.configured || false)
      return data
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : String(e))
      return null
    }
  }, [])

  return {
    messages,
    isLoading,
    error,
    isConfigured,
    currentToolCall,
    sendMessage,
    abort,
    clearMessages,
    checkConfig,
    updateConfig,
  }
}
