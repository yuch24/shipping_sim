// Cesium Globe 辅助函数 — 图标绘制、尾迹颜色、描述构建等

import type { ShipData } from '@/types/simulation'

export interface TrailPoint {
  lon: number
  lat: number
}

// ---- Enhanced 3D-looking ship icon (canvas) ----
export function createShipIcon(colorHex: string, state: string, size: number = 48): HTMLCanvasElement {
  const canvas = document.createElement('canvas')
  canvas.width = size
  canvas.height = size
  const ctx = canvas.getContext('2d')!
  const cx = size / 2
  const cy = size / 2
  const s = size * 0.42

  // Parse color for shading
  const r = parseInt(colorHex.slice(1, 3), 16)
  const g = parseInt(colorHex.slice(3, 5), 16)
  const b = parseInt(colorHex.slice(5, 7), 16)
  const darkColor = `rgb(${Math.max(0, r - 60)},${Math.max(0, g - 60)},${Math.max(0, b - 60)})`
  const lightColor = `rgb(${Math.min(255, r + 40)},${Math.min(255, g + 40)},${Math.min(255, b + 40)})`

  // ---- Hull (ship shape viewed from above, pointing up) ----
  ctx.beginPath()
  ctx.moveTo(cx, cy - s * 1.1)           // bow
  ctx.lineTo(cx + s * 0.9, cy - s * 0.3) // starboard bow
  ctx.lineTo(cx + s * 1.0, cy + s * 0.5) // starboard mid
  ctx.lineTo(cx + s * 0.8, cy + s * 1.0) // starboard stern
  ctx.lineTo(cx - s * 0.8, cy + s * 1.0) // port stern
  ctx.lineTo(cx - s * 1.0, cy + s * 0.5) // port mid
  ctx.lineTo(cx - s * 0.9, cy - s * 0.3) // port bow
  ctx.closePath()

  // Gradient fill for 3D shading
  const grad = ctx.createLinearGradient(cx - s, cy - s, cx + s, cy + s)
  grad.addColorStop(0, lightColor)
  grad.addColorStop(0.5, colorHex)
  grad.addColorStop(1, darkColor)
  ctx.fillStyle = grad
  ctx.fill()
  ctx.strokeStyle = 'rgba(255,255,255,0.4)'
  ctx.lineWidth = 1
  ctx.stroke()

  // ---- Deck containers (small colored rectangles on the deck) ----
  const containerColors = ['#E53E3E', '#3182CE', '#38A169', '#D69E2E', '#805AD5', '#DD6B20']
  const containerW = s * 0.18
  const containerH = s * 0.12
  // 2 rows x 3 columns
  for (let row = 0; row < 2; row++) {
    for (let col = 0; col < 3; col++) {
      const xOffset = cx + (col - 1) * s * 0.38
      const yOffset = cy - s * 0.15 + row * s * 0.35
      ctx.fillStyle = containerColors[(row * 3 + col) % containerColors.length]
      ctx.fillRect(xOffset - containerW / 2, yOffset - containerH / 2, containerW, containerH)
      ctx.strokeStyle = 'rgba(255,255,255,0.15)'
      ctx.lineWidth = 0.5
      ctx.strokeRect(xOffset - containerW / 2, yOffset - containerH / 2, containerW, containerH)
    }
  }

  // ---- Bridge/superstructure ----
  ctx.fillStyle = 'rgba(255,255,255,0.25)'
  ctx.fillRect(cx - s * 0.12, cy + s * 0.25, s * 0.24, s * 0.20)

  // ---- Funnel (small rectangle aft of bridge) ----
  ctx.fillStyle = darkColor
  ctx.fillRect(cx - s * 0.06, cy + s * 0.48, s * 0.12, s * 0.12)

  return canvas
}

// ---- Glow dot for animated routes ----
export function createGlowDot(size: number = 12): HTMLCanvasElement {
  const canvas = document.createElement('canvas')
  canvas.width = size
  canvas.height = size
  const ctx = canvas.getContext('2d')!
  const cx = size / 2
  const cy = size / 2
  const grad = ctx.createRadialGradient(cx, cy, 0, cx, cy, cx)
  grad.addColorStop(0, 'rgba(0, 200, 255, 0.9)')
  grad.addColorStop(0.3, 'rgba(0, 200, 255, 0.5)')
  grad.addColorStop(1, 'rgba(0, 200, 255, 0)')
  ctx.fillStyle = grad
  ctx.fillRect(0, 0, size, size)
  return canvas
}

// ---- Port icon (enhanced crane) ----
export function createPortIcon(color: string, size: number = 36): HTMLCanvasElement {
  const canvas = document.createElement('canvas')
  canvas.width = size
  canvas.height = size
  const ctx = canvas.getContext('2d')!
  const cx = size / 2

  // Crane structure
  ctx.fillStyle = color
  ctx.fillRect(cx - size * 0.08, size * 0.12, size * 0.16, size * 0.40)
  ctx.fillRect(cx, size * 0.15, size * 0.35, size * 0.06)
  ctx.fillRect(cx - size * 0.30, size * 0.15, size * 0.30, size * 0.04)
  ctx.fillRect(size * 0.10, size * 0.60, size * 0.80, size * 0.08)

  // White highlights
  ctx.fillStyle = 'rgba(255,255,255,0.3)'
  ctx.fillRect(cx - size * 0.05, size * 0.15, size * 0.03, size * 0.35)

  // Warning indicator for congested ports
  if (color === '#EF4444') {
    ctx.beginPath()
    ctx.arc(cx + size * 0.28, size * 0.18, size * 0.04, 0, Math.PI * 2)
    ctx.fillStyle = '#EF4444'
    ctx.fill()
    ctx.strokeStyle = '#ffffff'
    ctx.lineWidth = 1
    ctx.stroke()
  }

  return canvas
}

// ---- Trail color from CII rating ----
export function getTrailColor(ciiRating: string | undefined, co2: number | undefined): string {
  if (ciiRating === 'A' || ciiRating === 'B') return '#4ade80'
  if (ciiRating === 'C') return '#facc15'
  if (ciiRating === 'D') return '#fb923c'
  if (ciiRating === 'E') return '#ef4444'
  if (co2 !== undefined && co2 > 5000) return '#fb923c'
  if (co2 !== undefined && co2 > 2000) return '#facc15'
  return '#4ade80'
}

// ---- Build ship description HTML for Cesium info box ----
export function buildShipDescription(ship: ShipData, colorHex: string): string {
  return `
    <div class="cesium-info-box">
      <h3 style="color: #00d4ff; margin: 0 0 10px 0;">${ship.name}</h3>
      <table style="width: 100%; font-size: 12px;">
        <tr><td style="color: #9ca3af;">状态</td><td style="color: ${colorHex};">${ship.state}</td></tr>
        <tr><td style="color: #9ca3af;">航速</td><td>${ship.current_speed} 节</td></tr>
        <tr><td style="color: #9ca3af;">位置</td><td>${ship.lat?.toFixed(4)}, ${ship.lon?.toFixed(4)}</td></tr>
        <tr><td style="color: #9ca3af;">当前港口</td><td>${ship.current_port || 'N/A'}</td></tr>
        <tr><td style="color: #9ca3af;">下一港口</td><td>${ship.next_port || 'N/A'}</td></tr>
        ${ship.cii_rating ? `<tr><td style="color: #9ca3af;">CII评级</td><td style="color: ${getTrailColor(ship.cii_rating, undefined)};">${ship.cii_rating}</td></tr>` : ''}
        ${ship.co2_emissions !== undefined ? `<tr><td style="color: #9ca3af;">CO₂</td><td>${(ship.co2_emissions / 1000).toFixed(1)} t</td></tr>` : ''}
      </table>
    </div>
  `
}
