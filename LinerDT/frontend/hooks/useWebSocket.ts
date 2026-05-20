'use client'

import { useEffect, useRef, useState, useCallback } from 'react'

export interface ShipTrajectoryData {
  ship_id: string
  name: string
  service: string
  week_offset: number
  cycle_hours: number
  waypoints: { t: number; lat: number; lon: number }[]
  schedule: { port: string; eta: number; etd: number | null }[]
}

export interface SimState {
  current_time: number
  is_running: boolean
  speed: number
  simulation_mode?: string
  ships: Record<string, ShipData>
  ports: Record<string, PortData>
}

export interface ShipData {
  unique_id: string
  name: string
  service: string
  state: string
  lat: number | null
  lon: number | null
  current_port: string | null
  next_port: string | null
}

export interface PortData {
  unique_id: string
  name: string
  lat: number
  lon: number
  queue_length: number
  available_berths?: number
  berth_count?: number
  ships_at_port?: number
}

export function useWebSocket(onStateChange?: (state: SimState) => void) {
  const [connected, setConnected] = useState(false)
  const [simState, setSimState] = useState<SimState | null>(null)
  const [trajectories, setTrajectories] = useState<Record<string, ShipTrajectoryData> | null>(null)
  const wsRef = useRef<WebSocket | null>(null)
  const reconnectTimeoutRef = useRef<NodeJS.Timeout>()
  const currentStateRef = useRef<SimState | null>(null)

  const connect = useCallback(() => {
    if (typeof window === 'undefined') return

    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
    const host = window.location.host
    const wsUrl = `${protocol}//${host}/ws/sim`

    try {
      const ws = new WebSocket(wsUrl)
      wsRef.current = ws

      ws.onopen = () => {
        console.log('WebSocket connected')
        setConnected(true)
      }

      ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data)

          if (data.type === 'full_sync') {
            if (data.trajectories) {
              setTrajectories(data.trajectories)
            }
            currentStateRef.current = data
            setSimState(data)
            onStateChange?.(data as SimState)
          } else if (data.type === 'clock_update') {
            if (currentStateRef.current) {
              const newState: SimState = {
                ...currentStateRef.current,
                current_time: data.current_time ?? currentStateRef.current.current_time,
                is_running: data.is_running ?? currentStateRef.current.is_running,
                speed: data.speed ?? currentStateRef.current.speed,
                ships: data.ships ?? currentStateRef.current.ships,
                ports: data.ports ?? currentStateRef.current.ports,
              }
              currentStateRef.current = newState
              setSimState(newState)
              onStateChange?.(newState)
            } else {
              currentStateRef.current = data
              setSimState(data)
              onStateChange?.(data as SimState)
            }
          } else if (data.type === 'trajectories') {
            setTrajectories(data.data)
          } else if (data.type === 'heartbeat' || data.type === 'pong') {
            // ignore
          }
        } catch (e) {
          console.error('Failed to parse WebSocket message:', e)
        }
      }

      ws.onclose = () => {
        console.log('WebSocket disconnected')
        setConnected(false)
        reconnectTimeoutRef.current = setTimeout(connect, 3000)
      }

      ws.onerror = (error) => {
        console.error('WebSocket error:', error)
      }
    } catch (e) {
      console.error('Failed to create WebSocket:', e)
      reconnectTimeoutRef.current = setTimeout(connect, 3000)
    }
  }, [onStateChange])

  useEffect(() => {
    connect()
    return () => {
      if (reconnectTimeoutRef.current) clearTimeout(reconnectTimeoutRef.current)
      if (wsRef.current) wsRef.current.close()
    }
  }, [connect])

  const sendAction = useCallback((action: string, params?: Record<string, unknown>) => {
    if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify({ action, ...params }))
    }
  }, [])

  const start = useCallback((speed?: number) => {
    sendAction('start', { speed: speed ?? 60 })
  }, [sendAction])

  const pause = useCallback(() => {
    sendAction('pause')
  }, [sendAction])

  const setSpeed = useCallback((speed: number) => {
    sendAction('set-speed', { speed })
  }, [sendAction])

  const reset = useCallback(() => {
    sendAction('reset')
  }, [sendAction])

  const getState = useCallback(() => {
    sendAction('get_state')
  }, [sendAction])

  const getTrajectories = useCallback(() => {
    sendAction('get_trajectories')
  }, [sendAction])

  return {
    connected,
    simState,
    trajectories,
    start,
    pause,
    setSpeed,
    reset,
    getState,
    getTrajectories,
    sendAction,
  }
}