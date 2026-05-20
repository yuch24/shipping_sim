'use client'

import { useRef, useEffect } from 'react'

interface DelayLink {
  source: string
  target: string
  delay_hours: number
  propagation_count: number
}

interface DelayNode {
  id: string
  name: string
  avg_delay: number
  ship_count: number
  is_congested?: boolean
}

interface DelayNetworkProps {
  nodes: DelayNode[]
  links: DelayLink[]
  width?: number
  height?: number
}

export default function DelayNetwork({
  nodes,
  links,
  width = 600,
  height = 400,
}: DelayNetworkProps) {
  const canvasRef = useRef<HTMLCanvasElement>(null)

  useEffect(() => {
    const canvas = canvasRef.current
    if (!canvas || nodes.length === 0) return

    const ctx = canvas.getContext('2d')
    if (!ctx) return

    const dpr = window.devicePixelRatio || 1
    canvas.width = width * dpr
    canvas.height = height * dpr
    ctx.scale(dpr, dpr)

    ctx.clearRect(0, 0, width, height)

    // Background
    ctx.fillStyle = '#0a1929'
    ctx.fillRect(0, 0, width, height)

    // Layout: arrange nodes in a circle
    const cx = width / 2
    const cy = height / 2
    const radius = Math.min(cx, cy) - 60
    const maxDelay = Math.max(...nodes.map(n => n.avg_delay), 1)

    const positionedNodes = nodes.map((node, i) => {
      const angle = (2 * Math.PI * i) / nodes.length - Math.PI / 2
      return {
        ...node,
        x: cx + radius * Math.cos(angle),
        y: cy + radius * Math.sin(angle),
        scaledDelay: node.avg_delay / maxDelay,
      }
    })
    const nodeMap = new Map(positionedNodes.map(n => [n.id, n]))

    // Draw links (edges)
    const maxLinkDelay = Math.max(...links.map(l => l.delay_hours), 1)

    links.forEach((link) => {
      const source = nodeMap.get(link.source)
      const target = nodeMap.get(link.target)
      if (!source || !target) return

      const opacity = Math.max(0.1, link.delay_hours / maxLinkDelay)
      const width_ = Math.max(1, link.propagation_count * 2)

      ctx.strokeStyle = `rgba(239, 68, 68, ${opacity})`
      ctx.lineWidth = width_
      ctx.beginPath()
      ctx.moveTo(source.x, source.y)
      ctx.lineTo(target.x, target.y)
      ctx.stroke()

      // Delay label on edge
      const midX = (source.x + target.x) / 2
      const midY = (source.y + target.y) / 2
      ctx.fillStyle = 'rgba(239, 68, 68, 0.7)'
      ctx.font = '9px sans-serif'
      ctx.textAlign = 'center'
      ctx.fillText(`${link.delay_hours.toFixed(0)}h`, midX, midY - 4)
    })

    // Draw nodes
    positionedNodes.forEach((node) => {
      const nodeRadius = 15 + node.scaledDelay * 20
      const isCongested = node.is_congested || node.avg_delay > 5

      // Glow effect for congested nodes
      if (isCongested) {
        ctx.beginPath()
        ctx.arc(node.x, node.y, nodeRadius + 8, 0, 2 * Math.PI)
        ctx.fillStyle = 'rgba(239, 68, 68, 0.15)'
        ctx.fill()
      }

      // Node circle
      ctx.beginPath()
      ctx.arc(node.x, node.y, nodeRadius, 0, 2 * Math.PI)

      const gradient = ctx.createRadialGradient(node.x, node.y, 0, node.x, node.y, nodeRadius)
      if (isCongested) {
        gradient.addColorStop(0, '#EF4444')
        gradient.addColorStop(1, '#7F1D1D')
      } else {
        gradient.addColorStop(0, '#3B82F6')
        gradient.addColorStop(1, '#1E3A5F')
      }
      ctx.fillStyle = gradient
      ctx.fill()

      ctx.strokeStyle = isCongested ? '#FCA5A5' : '#93C5FD'
      ctx.lineWidth = 2
      ctx.stroke()

      // Node label
      ctx.fillStyle = '#E5E7EB'
      ctx.font = 'bold 11px sans-serif'
      ctx.textAlign = 'center'
      ctx.fillText(node.name, node.x, node.y + nodeRadius + 16)

      // Delay value
      ctx.fillStyle = isCongested ? '#FCA5A5' : '#93C5FD'
      ctx.font = '10px sans-serif'
      ctx.fillText(`${node.avg_delay.toFixed(1)}h`, node.x, node.y + nodeRadius + 30)
    })
  }, [nodes, links, width, height])

  return (
    <div className="w-full flex justify-center">
      <canvas
        ref={canvasRef}
        className="rounded-lg"
        style={{ width: `${width}px`, height: `${height}px` }}
      />
    </div>
  )
}
