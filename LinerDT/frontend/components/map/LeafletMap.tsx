'use client'

import { useEffect, useRef } from 'react'
import type { ShipData, PortData } from '@/types/simulation'
import { SHIP_COLORS } from '@/utils/colors'
import { PORT_COORDS } from '@/utils/mapData'
import { CDN } from '@/lib/api'

interface LeafletMapProps {
  ships: Record<string, ShipData> | ShipData[]
  ports: Record<string, PortData> | PortData[]
  onShipClick?: (shipId: string) => void
  onPortClick?: (portId: string) => void
}

// Sea route waypoints to avoid crossing land (format: [lat, lon])
// Cape of Good Hope route — SIN → Cape → Atlantic → Channel → Europe
const CAPE_ROUTE: [number, number][] = [
  [1.3, 103.8], [0, 104.5], [-5.5, 106], [-10, 100], [-15, 93],
  [-20, 85], [-25, 75], [-30, 65], [-33, 55], [-34, 45],
  [-34.5, 35], [-34.5, 28], [-34.5, 18.5],
  [-25, 10], [-15, 2], [-5, -5], [5, -10], [15, -15],
  [25, -15], [35, -10], [45, -5], [48, -3],
]

const SEA_WAYPOINTS: Record<string, [number, number][]> = {
  // China coastal
  'COAST_TSN_DLC': [[38.97, 117.78], [39, 119], [39.2, 120.5], [38.93, 121.65]],
  'COAST_DLC_TAO': [[38.93, 121.65], [37, 122], [36.5, 121], [36.07, 120.33]],
  'COAST_TAO_SHA': [[36.07, 120.33], [34, 121.5], [32, 122], [31.23, 121.47]],
  'COAST_SHA_NGB': [[31.23, 121.47], [30.5, 122], [29.87, 121.54]],
  'COAST_NGB_XMN': [[29.87, 121.54], [28, 121], [27, 120], [25.5, 119], [24.48, 118.09]],
  'COAST_XMN_YTN': [[24.48, 118.09], [23.5, 117], [23, 116], [22.58, 114.27]],
  // South China Sea
  'SCS_S': [[15, 114], [10, 109], [5, 106.5], [1.3, 104.8]],
  'SCS_PKG': [[15, 114], [8, 109], [5, 106], [3, 103], [3, 101.4]],
  // SIN → PKG short hop
  'SIN_PKG': [[1.3, 103.8], [2, 102], [3, 101.4]],
  // Cape of Good Hope (SIN → Europe via Cape)
  'CAPE': CAPE_ROUTE,
  // Cape → Channel → RTM
  'CAPE_TO_RTM': [...CAPE_ROUTE, [49, -1], [50, 0], [51.92, 4.05]],
  // Cape → Channel → HAM
  'CAPE_TO_HAM': [...CAPE_ROUTE, [49, -1], [50, 0], [51, 4], [52.5, 6], [53.55, 9.99]],
  // Cape → FXT
  'CAPE_TO_FXT': [...CAPE_ROUTE, [49, -1], [51.95, 1.35]],
  // Cape → TNG
  'CAPE_TO_TNG': [
    [1.3, 103.8], [0, 104.5], [-5.5, 106], [-10, 100], [-15, 93],
    [-20, 85], [-25, 75], [-30, 65], [-33, 55], [-34, 45],
    [-34.5, 35], [-34.5, 28], [-34.5, 18.5],
    [-25, 10], [-15, 2], [-5, -5], [5, -10], [15, -15],
    [25, -15], [35, -10], [35.77, -5.8],
  ],
  // North Sea coastal
  'NORTH_SEA': [[51.92, 4.05], [52.5, 6], [53, 7], [53.5, 8], [53.55, 9.99]],
  // Channel → LEH
  'CHANNEL_LEH': [[48, -3], [49, -1], [49.49, 0.11]],
  // TNG → DKK → SOU → LEH
  'TNG_DKK': [[35.77, -5.8], [37, -5], [39, -4], [41, -2], [44, 0], [48, 2], [51.05, 2.37]],
  'DKK_SOU': [[51.05, 2.37], [51, 1], [50.9, -0.5], [50.90, -1.4]],
  'SOU_LEH': [[50.90, -1.4], [50, -0.5], [49.49, 0.11]],
}

// AEU route segments — Cape of Good Hope route
const AEU_ROUTE_SEGMENTS = [
  ['TSN07', 'DLC01'],   // Tianjin → Dalian (Bohai)
  ['DLC01', 'TAO02'],   // Dalian → Qingdao (Yellow Sea)
  ['TAO02', 'SHA08'],   // Qingdao → Shanghai (East China Sea)
  ['SHA08', 'NGB07'],   // Shanghai → Ningbo (coastal)
  ['NGB07', 'XMN09'],   // Ningbo → Xiamen (coastal)
  ['XMN09', 'YTN01'],   // Xiamen → Yantian (South China Sea)
  ['YTN01', 'SIN02'],   // Yantian → Singapore (SCS)
  ['SIN02', 'FXT02'],   // Singapore → Felixstowe (via Cape)
  ['FXT02', 'ZEE03'],   // Felixstowe → Zeebrugge
  ['ZEE03', 'GDN02'],   // Zeebrugge → Gdansk
  ['GDN02', 'WVN01'],   // Gdansk → Wilhelmshaven
]

// Port ID mapping: Cesium IDs ↔ Leaflet simplified IDs
const PORT_ID_MAP: Record<string, string> = {
  'SHA08': 'SHA', 'NGB07': 'NGB', 'XMN09': 'XMN',
  'YTN01': 'YTN', 'SIN02': 'SIN', 'PKG03': 'PKG',
  'RTM06': 'RTM', 'RTM10': 'RTM', 'HAM01': 'HAM', 'HAM02': 'HAM',
  'FXT02': 'FXT', 'ZEE03': 'ZEE', 'GDN02': 'GDN', 'WVN01': 'WVN',
  'ANR07': 'ANR', 'LEH06': 'LEH', 'DKK01': 'DKK', 'SOU01': 'SOU',
  'TNG01': 'TNG', 'ALG03': 'ALG', 'TAO02': 'TAO', 'TAO06': 'TAO',
  'TSN07': 'TSN', 'DLC01': 'DLC',
}

function buildRoutePath(portMap: Map<string, PortData>): [number, number][] {
  const path: [number, number][] = []

  // Map port IDs to simple IDs for waypoint lookup
  const simplify = (id: string) => PORT_ID_MAP[id] || id
  const getCoords = (id: string): [number, number] | null => {
    const port = portMap.get(id)
    if (!port) return null
    const coords = PORT_COORDS[id]
    return coords ? [coords[0], coords[1]] : [port.lat, port.lon]
  }

  for (const [fromId, toId] of AEU_ROUTE_SEGMENTS) {
    const from = getCoords(fromId)
    const to = getCoords(toId)
    if (!from || !to) continue

    if (path.length === 0) path.push(from)

    const fromS = simplify(fromId)
    const toS = simplify(toId)
    const segKey = `${fromS}_to_${toS}`
    const reverseKey = `${toS}_to_${fromS}`

    // China coastal segments
    if (SEA_WAYPOINTS['COAST_TSN_DLC'] && fromId === 'TSN07' && toId === 'DLC01') {
      path.push(...SEA_WAYPOINTS['COAST_TSN_DLC'])
    } else if (SEA_WAYPOINTS['COAST_DLC_TAO'] && (fromId === 'DLC01' && (toId === 'TAO02' || toId === 'TAO06'))) {
      path.push(...SEA_WAYPOINTS['COAST_DLC_TAO'])
    } else if (SEA_WAYPOINTS['COAST_TAO_SHA'] && (fromId === 'TAO02' || fromId === 'TAO06') && toId === 'SHA08') {
      path.push(...SEA_WAYPOINTS['COAST_TAO_SHA'])
    } else if (SEA_WAYPOINTS['COAST_SHA_NGB'] && fromId === 'SHA08' && toId === 'NGB07') {
      path.push(...SEA_WAYPOINTS['COAST_SHA_NGB'])
    } else if (SEA_WAYPOINTS['COAST_NGB_XMN'] && fromId === 'NGB07' && toId === 'XMN09') {
      path.push(...SEA_WAYPOINTS['COAST_NGB_XMN'])
    } else if (SEA_WAYPOINTS['COAST_XMN_YTN'] && fromId === 'XMN09' && toId === 'YTN01') {
      path.push(...SEA_WAYPOINTS['COAST_XMN_YTN'])
    }
    // South China Sea
    else if (fromId === 'YTN01' && toId === 'SIN02') {
      path.push(...SEA_WAYPOINTS['SCS_S'])
    }
    // Cape of Good Hope: SIN → Europe
    else if (fromId === 'SIN02' && toId === 'FXT02') {
      path.push(...SEA_WAYPOINTS['CAPE_TO_FXT'])
    } else if (fromId === 'SIN02' && (toId === 'RTM06' || toId === 'RTM10')) {
      path.push(...SEA_WAYPOINTS['CAPE_TO_RTM'])
    } else if (fromId === 'SIN02' && (toId === 'HAM01' || toId === 'HAM02')) {
      path.push(...SEA_WAYPOINTS['CAPE_TO_HAM'])
    } else if (fromId === 'SIN02' && toId === 'TNG01') {
      path.push(...SEA_WAYPOINTS['CAPE_TO_TNG'])
    }
    // Europe coastal
    else if (fromId === 'FXT02' && toId === 'ZEE03') {
      path.push([51.7, 1], [51.5, 2], [51.33, 3.2])
    } else if (fromId === 'ZEE03' && toId === 'GDN02') {
      path.push([53, 5], [54, 7], [54.5, 9], [54.5, 11], [54.5, 13], [54.5, 16], [54.35, 18.65])
    } else if (fromId === 'GDN02' && toId === 'WVN01') {
      path.push([54, 16], [53.8, 14], [53.5, 12], [53.3, 10], [53.52, 8.12])
    }
    // Default: direct connection for short coastal hops
    else {
      path.push(to)
    }

    path.push(to)
  }

  return path
}

function loadScript(src: string): Promise<void> {
  return new Promise((resolve, reject) => {
    if (document.querySelector(`script[src="${src}"]`)) { resolve(); return }
    const script = document.createElement('script')
    script.src = src
    script.onload = () => resolve()
    script.onerror = () => reject(new Error(`Failed to load ${src}`))
    document.head.appendChild(script)
  })
}

function loadCSS(href: string): Promise<void> {
  return new Promise((resolve) => {
    if (document.querySelector(`link[href="${href}"]`)) { resolve(); return }
    const link = document.createElement('link')
    link.rel = 'stylesheet'
    link.href = href
    link.onload = () => resolve()
    document.head.appendChild(link)
  })
}

// SVG strings for custom map icons
function shipIconSvg(color: string, heading: number = 0): string {
  return `
    <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24">
      <g transform="rotate(${heading}, 12, 12)">
        <path d="M12 2 L18 18 L12 14 L6 18 Z" fill="${color}" stroke="#fff" stroke-width="0.8" opacity="0.9"/>
        <circle cx="12" cy="12" r="1.5" fill="#fff"/>
      </g>
    </svg>`
}

function portIconSvg(color: string): string {
  return `
    <svg xmlns="http://www.w3.org/2000/svg" width="28" height="28" viewBox="0 0 28 28">
      <rect x="12" y="4" width="4" height="20" rx="1" fill="${color}" stroke="#fff" stroke-width="0.8" opacity="0.9"/>
      <rect x="6" y="20" width="16" height="4" rx="1" fill="${color}" stroke="#fff" stroke-width="0.8" opacity="0.9"/>
      <circle cx="14" cy="8" r="2" fill="#fff" opacity="0.6"/>
    </svg>`
}

function portCongestedIconSvg(): string {
  const color = '#EF4444'
  return `
    <svg xmlns="http://www.w3.org/2000/svg" width="28" height="28" viewBox="0 0 28 28">
      <rect x="12" y="4" width="4" height="20" rx="1" fill="${color}" stroke="#fff" stroke-width="0.8" opacity="0.9"/>
      <rect x="6" y="20" width="16" height="4" rx="1" fill="${color}" stroke="#fff" stroke-width="0.8" opacity="0.9"/>
      <circle cx="14" cy="8" r="2" fill="#fff" opacity="0.6"/>
      <text x="14" y="17" text-anchor="middle" font-size="6" fill="#fff" font-weight="bold">!</text>
    </svg>`
}

export default function LeafletMap({
  ships,
  ports,
  onShipClick,
  onPortClick,
}: LeafletMapProps) {
  const containerRef = useRef<HTMLDivElement>(null)
  const mapRef = useRef<any>(null)
  const LRef = useRef<any>(null)
  const markersLayerRef = useRef<any>(null)
  const routeLayerRef = useRef<any>(null)

  useEffect(() => {
    if (!containerRef.current) return
    let destroyed = false

    async function init() {
      await loadCSS(CDN.LEAFLET_CSS)

      if (destroyed || !containerRef.current) return

      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      let L: any
      try {
        // 优先使用 npm 安装的 leaflet（更可靠）
        L = (await import('leaflet')).default
      } catch {
        // 回退到 CDN 加载
        await loadScript(CDN.LEAFLET_JS)
        if (destroyed || !containerRef.current) return
        L = (window as any).L
      }

      if (!L) {
        console.error('Leaflet 加载失败')
        return
      }

      const map = L.map(containerRef.current, {
        center: [20, 80],
        zoom: 3,
        minZoom: 2,
        maxZoom: 12,
        zoomControl: false,
        attributionControl: false,
        fadeAnimation: true,
        zoomAnimation: true,
      })

      // 缩放控件移到左下角，避免被顶部 UI 遮挡
      L.control.zoom({ position: 'bottomleft' }).addTo(map)

      L.tileLayer(CDN.CARTO_DARK_TILES, {
        maxZoom: 18,
        subdomains: 'abcd',
      }).addTo(map)

      mapRef.current = map
      LRef.current = L
    }

    init().catch(err => console.error('Leaflet 地图初始化失败:', err))
    return () => {
      destroyed = true
      if (mapRef.current) {
        mapRef.current.remove()
        mapRef.current = null
      }
    }
  }, [])

  // Draw route
  useEffect(() => {
    if (!mapRef.current) return
    const L = LRef.current
    if (!L) return

    const map = mapRef.current
    const portsArray = Array.isArray(ports) ? ports : Object.values(ports)
    const portMap = new Map<string, PortData>()
    portsArray.forEach((p: PortData) => {
      const coords = PORT_COORDS[p.unique_id]
      if (coords) {
        portMap.set(p.unique_id, { ...p, lat: coords[0], lon: coords[1] })
      }
    })

    if (routeLayerRef.current) {
      map.removeLayer(routeLayerRef.current)
    }

    const path = buildRoutePath(portMap)
    if (path.length > 1) {
      const layerGroup = L.layerGroup()

      // Main route line
      L.polyline(path, {
        color: '#0057b7',
        weight: 2.5,
        opacity: 0.45,
        dashArray: '6, 4',
        smoothFactor: 2,
      }).addTo(layerGroup)

      // Subtle glow line
      L.polyline(path, {
        color: '#36aaff',
        weight: 5,
        opacity: 0.1,
        smoothFactor: 2,
      }).addTo(layerGroup)

      layerGroup.addTo(map)
      routeLayerRef.current = layerGroup
    }
  }, [ports])

  // Draw markers
  useEffect(() => {
    if (!mapRef.current) return
    const L = LRef.current
    if (!L) return

    const map = mapRef.current

    if (markersLayerRef.current) {
      map.removeLayer(markersLayerRef.current)
    }

    const markersLayer = L.layerGroup().addTo(map)

    const portsArray = Array.isArray(ports) ? ports : Object.values(ports) as PortData[]

    // Draw port markers
    portsArray.forEach((port) => {
      const coords = PORT_COORDS[port.unique_id]
      const lat = coords ? coords[0] : port.lat
      const lon = coords ? coords[1] : port.lon
      const isCongested = port.queue_length > 0
      const color = isCongested ? '#EF4444' : '#10B981'
      const iconSvg = isCongested ? portCongestedIconSvg() : portIconSvg(color)

      const icon = L.divIcon({
        html: iconSvg,
        className: 'port-marker',
        iconSize: [28, 28],
        iconAnchor: [14, 14],
        popupAnchor: [0, -16],
      })

      const marker = L.marker([lat, lon], { icon }).addTo(markersLayer)

      // Hover label (permanent small label)
      marker.bindTooltip(port.name, {
        permanent: true,
        direction: 'right',
        offset: [14, 0],
        className: 'port-tooltip',
      })

      marker.on('click', () => {
        if (onPortClick) onPortClick(port.unique_id)
      })
    })

    // Draw ship markers
    const shipsArray = Array.isArray(ships) ? ships : Object.values(ships) as ShipData[]

    shipsArray.forEach((ship) => {
      if (!ship.lat || !ship.lon) return

      const colorHex = SHIP_COLORS[ship.state] || SHIP_COLORS.default

      const icon = L.divIcon({
        html: shipIconSvg(colorHex, 0),
        className: 'ship-marker',
        iconSize: [24, 24],
        iconAnchor: [12, 12],
        popupAnchor: [0, -14],
      })

      const marker = L.marker([ship.lat, ship.lon], { icon }).addTo(markersLayer)

      marker.bindTooltip(ship.name, {
        permanent: false,
        direction: 'top',
        className: 'ship-tooltip',
        offset: [0, -10],
      })

      marker.on('click', () => {
        if (onShipClick) onShipClick(ship.unique_id)
      })
    })

    markersLayerRef.current = markersLayer
  }, [ships, ports, onShipClick, onPortClick])

  return (
    <div
      ref={containerRef}
      className="absolute inset-0"
      style={{ backgroundColor: '#080f1a' }}
    />
  )
}
