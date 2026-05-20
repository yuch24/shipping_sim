'use client'

import { useRef, useEffect } from 'react'

interface ShipTimeline {
  ship_id: string
  name: string
  segments: {
    start_time: number
    end_time: number
    state: string
    port?: string
  }[]
}

interface ShipGanttProps {
  data: ShipTimeline[]
  maxTime?: number
  height?: number
}

const STATE_COLORS: Record<string, string> = {
  IDLE: '#9CA3AF',
  SAILING: '#3B82F6',
  ARRIVING: '#F59E0B',
  WAITING: '#EF4444',
  BERTHING: '#10B981',
  LOADING: '#F97316',
  UNLOADING: '#F97316',
  DEPARTING: '#06B6D4',
}

export default function ShipGantt({ data, maxTime = 720, height = 400 }: ShipGanttProps) {
  const canvasRef = useRef<HTMLCanvasElement>(null)

  useEffect(() => {
    const canvas = canvasRef.current
    if (!canvas || data.length === 0) return

    const ctx = canvas.getContext('2d')
    if (!ctx) return

    const dpr = window.devicePixelRatio || 1
    const rect = canvas.getBoundingClientRect()
    canvas.width = rect.width * dpr
    canvas.height = height * dpr
    ctx.scale(dpr, dpr)

    const w = rect.width
    const h = height
    const padding = { top: 30, right: 20, bottom: 40, left: 140 }
    const chartW = w - padding.left - padding.right
    const chartH = h - padding.top - padding.bottom
    const rowH = chartH / data.length

    ctx.clearRect(0, 0, w, h)

    // Background
    ctx.fillStyle = '#0a1929'
    ctx.fillRect(0, 0, w, h)

    // Grid lines
    const numGridLines = 12
    ctx.strokeStyle = 'rgba(255,255,255,0.06)'
    ctx.lineWidth = 1
    for (let i = 0; i <= numGridLines; i++) {
      const x = padding.left + (chartW / numGridLines) * i
      ctx.beginPath()
      ctx.moveTo(x, padding.top)
      ctx.lineTo(x, h - padding.bottom)
      ctx.stroke()

      // Time labels
      const timeVal = Math.round((maxTime / numGridLines) * i)
      const days = Math.floor(timeVal / 24)
      ctx.fillStyle = '#6B7280'
      ctx.font = '11px sans-serif'
      ctx.textAlign = 'center'
      ctx.fillText(`D${days}`, x, h - padding.bottom + 16)
    }

    // Y-axis labels and rows
    data.forEach((ship, idx) => {
      const y = padding.top + idx * rowH

      // Row background (alternating)
      if (idx % 2 === 0) {
        ctx.fillStyle = 'rgba(255,255,255,0.02)'
        ctx.fillRect(padding.left, y, chartW, rowH)
      }

      // Ship name
      ctx.fillStyle = '#E5E7EB'
      ctx.font = '12px sans-serif'
      ctx.textAlign = 'right'
      ctx.fillText(ship.name.substring(0, 12), padding.left - 8, y + rowH / 2 + 4)

      // Timeline segments
      ship.segments.forEach((seg) => {
        const xStart = padding.left + (seg.start_time / maxTime) * chartW
        const xEnd = padding.left + (seg.end_time / maxTime) * chartW
        const width = Math.max(2, xEnd - xStart)
        const color = STATE_COLORS[seg.state] || '#9CA3AF'

        ctx.fillStyle = color
        const radius = 3
        const barY = y + 4
        const barH = rowH - 8

        // Rounded rect
        ctx.beginPath()
        ctx.moveTo(xStart + radius, barY)
        ctx.lineTo(xStart + width - radius, barY)
        ctx.quadraticCurveTo(xStart + width, barY, xStart + width, barY + radius)
        ctx.lineTo(xStart + width, barY + barH - radius)
        ctx.quadraticCurveTo(xStart + width, barY + barH, xStart + width - radius, barY + barH)
        ctx.lineTo(xStart + radius, barY + barH)
        ctx.quadraticCurveTo(xStart, barY + barH, xStart, barY + barH - radius)
        ctx.lineTo(xStart, barY + radius)
        ctx.quadraticCurveTo(xStart, barY, xStart + radius, barY)
        ctx.closePath()
        ctx.fill()

        // Port label for berthing segments
        if (seg.port && (seg.state === 'BERTHING' || seg.state === 'LOADING')) {
          ctx.fillStyle = 'rgba(255,255,255,0.6)'
          ctx.font = '9px sans-serif'
          ctx.textAlign = 'center'
          ctx.fillText(seg.port, xStart + width / 2, barY + barH / 2 + 3)
        }
      })
    })

    // Legend
    const legendItems = [
      { label: '航行', color: '#3B82F6' },
      { label: '在港', color: '#10B981' },
      { label: '等待', color: '#EF4444' },
      { label: '空闲', color: '#9CA3AF' },
    ]
    const legendX = padding.left
    const legendY = 8
    legendItems.forEach((item, i) => {
      const lx = legendX + i * 120
      ctx.fillStyle = item.color
      ctx.fillRect(lx, legendY, 10, 10)
      ctx.fillStyle = '#9CA3AF'
      ctx.font = '11px sans-serif'
      ctx.textAlign = 'left'
      ctx.fillText(item.label, lx + 16, legendY + 9)
    })
  }, [data, maxTime, height])

  return (
    <div className="w-full">
      <canvas
        ref={canvasRef}
        className="w-full"
        style={{ height: `${height}px` }}
      />
    </div>
  )
}
