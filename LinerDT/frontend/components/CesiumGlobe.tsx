'use client'

import { useEffect, useRef, useCallback, useState } from 'react'
import { loadPortsFromCsv, loadWaypointsFromCsv } from '@/utils/csvLoader'
import type { ShipTrajectoryData } from '@/hooks/useWebSocket'

declare global {
  interface Window {
    Cesium: any
  }
}

const CESIUM_CDN = '/cesium'

const CSV_PORT_COORDS = loadPortsFromCsv()
const CSV_WAYPOINT_SEGMENTS = loadWaypointsFromCsv()

let _debugMode = false
const DEBUG_KEY = 'd'
function toggleDebugMode() { _debugMode = !_debugMode }
function isDebugMode() { return _debugMode }

let _debugLat = 0, _debugLon = 0

if (typeof window !== 'undefined') {
  window.addEventListener('keydown', (e) => {
    if (e.ctrlKey && e.key === DEBUG_KEY) { toggleDebugMode() }
  })
}

interface ShipData {
  unique_id: string
  name: string
  state: string
  current_speed: number
  lat: number | null
  lon: number | null
  current_port: string | null
  next_port: string | null
  viz_status?: string
  co2_emissions?: number
  cii_rating?: string
  service?: string
}

interface PortData {
  unique_id: string
  name: string
  lat: number
  lon: number
  queue_length: number
  available_berths?: number
  berth_count?: number
  ships_at_port?: number
}

interface CesiumGlobeProps {
  ships: Record<string, ShipData> | ShipData[]
  ports: Record<string, PortData> | PortData[]
  trajectories?: Record<string, ShipTrajectoryData> | null
  currentTime?: number
  isRunning?: boolean
  speed?: number
  selectedShipId?: string | null
  onShipClick?: (shipId: string) => void
  onPortClick?: (portId: string) => void
  simulationMode?: string
  onSimTimeUpdate?: (simHours: number) => void
}

const SHIP_COLORS: Record<string, string> = {
  at_port: '#F59E0B',
  sailing: '#3B82F6',
  SAILING: '#3B82F6',
  IDLE: '#9CA3AF',
  ARRIVING: '#F59E0B',
  BERTHING: '#10B981',
  WAITING: '#EF4444',
  LOADING: '#F97316',
  DEPARTING: '#06B6D4',
  default: '#FFFFFF',
}

const SERVICE_COLORS: Record<string, string> = {
  AEU1: '#0057b7',
  AEU2: '#10B981',
  AEU3: '#F59E0B',
}

const PORT_COORDS: Record<string, [number, number]> = CSV_PORT_COORDS

const SEGMENT_MAP = new Map<string, number[]>()
for (const [segId, group] of Object.entries(CSV_WAYPOINT_SEGMENTS)) {
  const key = `${group.from_port}\u2192${group.to_port}`
  const keyReverse = `${group.to_port}\u2192${group.from_port}`
  const lons = group.points.map(p => p[1])
  const lats = group.points.map(p => p[0])
  SEGMENT_MAP.set(key, [...lons, ...lats])
  SEGMENT_MAP.set(keyReverse, [...lons.slice().reverse(), ...lats.slice().reverse()])
}

const dotCache = new Map<string, HTMLCanvasElement>()
function createDotIcon(color: string, size: number = 20): HTMLCanvasElement {
  const key = `dot-${color}`
  if (dotCache.has(key)) return dotCache.get(key)!
  const canvas = document.createElement('canvas')
  canvas.width = size; canvas.height = size
  const ctx = canvas.getContext('2d')!
  const cx = size / 2, cy = size / 2
  const glow = ctx.createRadialGradient(cx, cy, 0, cx, cy, size / 2)
  glow.addColorStop(0, color)
  glow.addColorStop(0.5, color + '80')
  glow.addColorStop(1, color + '00')
  ctx.fillStyle = glow
  ctx.fillRect(0, 0, size, size)
  ctx.beginPath()
  ctx.arc(cx, cy, size * 0.18, 0, Math.PI * 2)
  ctx.fillStyle = '#ffffff'
  ctx.fill()
  ctx.beginPath()
  ctx.arc(cx, cy, size * 0.14, 0, Math.PI * 2)
  ctx.fillStyle = color
  ctx.fill()
  dotCache.set(key, canvas)
  return canvas
}

function createGlowDot(): HTMLCanvasElement {
  const s = 16
  const canvas = document.createElement('canvas')
  canvas.width = s; canvas.height = s
  const ctx = canvas.getContext('2d')!
  const grad = ctx.createRadialGradient(s / 2, s / 2, 0, s / 2, s / 2, s / 2)
  grad.addColorStop(0, 'rgba(0, 136, 255, 1)')
  grad.addColorStop(0.3, 'rgba(0, 136, 255, 0.8)')
  grad.addColorStop(0.7, 'rgba(0, 136, 255, 0.3)')
  grad.addColorStop(1, 'rgba(0, 136, 255, 0)')
  ctx.fillStyle = grad
  ctx.fillRect(0, 0, s, s)
  return canvas
}

function buildShipDescription(ship: ShipData, colorHex: string): string {
  const loadTEU = ship.lat !== null && ship.lon !== null ? '' : ''
  return `
    <div class="cesium-info-box">
      <h3 style="color: #00d4ff; margin: 0 0 8px 0;">${ship.name}</h3>
      <table style="width: 100%; font-size: 12px;">
        <tr><td style="color: #9ca3af;">航线</td><td style="color: ${SERVICE_COLORS[ship.service || ''] || colorHex};">${ship.service || 'N/A'}</td></tr>
        <tr><td style="color: #9ca3af;">状态</td><td style="color: ${colorHex};">${ship.state}</td></tr>
        <tr><td style="color: #9ca3af;">当前港口</td><td>${ship.current_port || '航行中'}</td></tr>
        <tr><td style="color: #9ca3af;">下一港口</td><td>${ship.next_port || 'N/A'}</td></tr>
      </table>
    </div>`
}

const AEU_ROUTES: { id: string; sequence: string[]; color: string }[] = [
  {
    id: 'AEU1',
    sequence: ['CNTAO','CNSHA','CNNGB','CNXMN','CNYTN','SGSIN','GBFXT','BEZEE','PLGDY','DEWVN','SGSIN','CNYTN','CNTAO'],
    color: '#0057b7',
  },
  {
    id: 'AEU2',
    sequence: ['CNNGB','CNSHA','CNYTN','SGSIN','MAPTM','FRDKK','GBSOU','FRLEH','MYPKG','CNNGB'],
    color: '#10B981',
  },
  {
    id: 'AEU3',
    sequence: ['CNTXG','CNDLC','CNTAO','CNSHA','CNNGB','SGSIN','NLRTM','DEHAM','BEANR','CNSHA','CNTXG'],
    color: '#F59E0B',
  },
]

function buildRouteFromSequence(sequence: string[], coords: Record<string, [number, number]>): number[] {
  const route: number[] = []
  for (let i = 0; i < sequence.length - 1; i++) {
    const from = sequence[i]
    const to = sequence[i + 1]
    const fromC = coords[from]
    const toC = coords[to]
    if (!fromC || !toC) continue
    if (route.length === 0) route.push(fromC[1], fromC[0])
    const segKey = `${from}\u2192${to}`
    const waypoints = SEGMENT_MAP.get(segKey)
    if (waypoints) {
      const half = waypoints.length / 2
      for (let j = 0; j < half; j++)
        route.push(waypoints[j], waypoints[half + j])
    }
    route.push(toC[1], toC[0])
  }
  return route
}

export default function CesiumGlobe({
  ships, ports, trajectories, currentTime = 0, isRunning = false, speed = 60,
  selectedShipId, onShipClick, onPortClick, simulationMode,
  onSimTimeUpdate,
}: CesiumGlobeProps) {
  const containerRef = useRef<HTMLDivElement>(null)
  const wrapperRef = useRef<HTMLDivElement>(null)
  const viewerRef = useRef<any>(null)
  const clickHandlerRef = useRef<any>(null)
  const animFrameRef = useRef<number>(0)
  const routeDotsRef = useRef<any[]>([])
  const routePositionsRef = useRef<number[]>([])
  const [cesiumReady, setCesiumReady] = useState(false)
  const [cesiumError, setCesiumError] = useState<string | null>(null)

  const shipEntitiesRef = useRef<Map<string, any>>(new Map())
  const trajAppliedRef = useRef<Set<string>>(new Set())

  const handleShipClick = useCallback((shipId: string) => { onShipClick?.(shipId) }, [onShipClick])
  const handlePortClick = useCallback((portId: string) => { onPortClick?.(portId) }, [onPortClick])

  // ---- Load Cesium SDK ----
  useEffect(() => {
    if (typeof window === 'undefined') return
    if (window.Cesium) { setCesiumReady(true); return }
    let cancelled = false
    ;(window as any).CESIUM_BASE_URL = '/cesium/'
    const cssLink = document.createElement('link')
    cssLink.rel = 'stylesheet'
    cssLink.href = `${CESIUM_CDN}/Widgets/widgets.css`
    document.head.appendChild(cssLink)
    const script = document.createElement('script')
    script.src = `${CESIUM_CDN}/Cesium.js`
    script.async = true
    script.onload = () => { if (!cancelled) setCesiumReady(true) }
    script.onerror = () => { if (!cancelled) setCesiumError('Cesium SDK load failed') }
    document.head.appendChild(script)
    return () => { cancelled = true }
  }, [])

  if (cesiumError) throw new Error(cesiumError)

  // ---- Initialize Viewer ----
  useEffect(() => {
    if (typeof window === 'undefined' || !window.Cesium || !containerRef.current || !cesiumReady) return

    const Cesium = window.Cesium
    const token = process.env.NEXT_PUBLIC_CESIUM_ION_TOKEN
    if (token && token !== 'your_token_here') Cesium.Ion.defaultAccessToken = token

    const hasToken = token && token !== 'your_token_here'
    const imageryProvider = hasToken
      ? undefined
      : new Cesium.OpenStreetMapImageryProvider({ url: 'https://tile.openstreetmap.org/' })

    const viewer = new Cesium.Viewer(containerRef.current, {
      animation: false, timeline: false, baseLayerPicker: false,
      geocoder: false, homeButton: false, sceneModePicker: false,
      navigationHelpButton: false, infoBox: false, fullscreenButton: false,
      selectionIndicator: false,
      imageryProvider,
      creditContainer: document.createElement('div'),
      contextOptions: { webgl: { alpha: true, preserveDrawingBuffer: false, powerPreference: 'high-performance' } },
    })
    viewer.scene.pickPosition = false
    viewer.scene.pickTranslucentDepth = false
    viewerRef.current = viewer

    return () => {
      cancelAnimationFrame(animFrameRef.current)
      if (viewerRef.current) { viewerRef.current.destroy(); viewerRef.current = null }
    }
  }, [cesiumReady])

  // ---- Route Lines (3 separate AEU routes) ----
  useEffect(() => {
    if (!viewerRef.current || typeof window === 'undefined' || !window.Cesium) return

    const Cesium = window.Cesium
    const viewer = viewerRef.current

    const oldIds = AEU_ROUTES.map(r => [`${r.id}-route`, `${r.id}-route-glow`]).flat()
    for (const id of oldIds) {
      const old = viewer.entities.getById(id)
      if (old) viewer.entities.remove(old)
    }
    routeDotsRef.current.forEach((dot: any) => viewer.entities.remove(dot))
    routeDotsRef.current = []
    routePositionsRef.current = []

    for (const routeDef of AEU_ROUTES) {
      const rp = buildRouteFromSequence(routeDef.sequence, PORT_COORDS)
      if (rp.length < 4) continue

      const cartesians = Cesium.Cartesian3.fromDegreesArray(rp)

      viewer.entities.add({
        id: `${routeDef.id}-route`,
        polyline: { positions: cartesians, width: 2, material: Cesium.Color.fromCssColorString(routeDef.color).withAlpha(0.6), clampToGround: true },
      })
      viewer.entities.add({
        id: `${routeDef.id}-route-glow`,
        polyline: { positions: cartesians, width: 6, material: Cesium.Color.fromCssColorString(routeDef.color).withAlpha(0.12), clampToGround: true },
      })

      const glowDot = createGlowDot()
      for (let i = 0; i < 2; i++) {
        const dot = viewer.entities.add({
          position: Cesium.Cartesian3.fromDegrees(rp[0], rp[1]),
          billboard: {
            image: glowDot, scale: 0.6,
            scaleByDistance: new Cesium.NearFarScalar(1e5, 0.8, 5e7, 0.15),
            translucencyByDistance: new Cesium.NearFarScalar(1e4, 0.6, 1e7, 0.0),
            heightReference: Cesium.HeightReference.CLAMP_TO_GROUND,
          },
        })
        routeDotsRef.current.push(dot)
      }

      routePositionsRef.current = rp
    }
  }, [cesiumReady])

  // ---- Ships: SampledPositionProperty based on trajectories ----
  useEffect(() => {
    if (!viewerRef.current || typeof window === 'undefined' || !window.Cesium) return
    if (!trajectories) return

    const Cesium = window.Cesium
    const viewer = viewerRef.current

    for (const [shipId, traj] of Object.entries(trajectories)) {
      if (trajAppliedRef.current.has(shipId)) continue

      const existingEntity = viewer.entities.getById(`ship-dot-${shipId}`)
      if (existingEntity) {
        viewer.entities.remove(existingEntity)
      }

      const positionProperty = new Cesium.SampledPositionProperty()
      const epoch = Cesium.JulianDate.fromDate(new Date('2024-01-01T00:00:00Z'))

      for (const wp of traj.waypoints) {
        const wpDate = Cesium.JulianDate.addSeconds(epoch, wp.t * 3600, new Cesium.JulianDate())
        const pos = Cesium.Cartesian3.fromDegrees(wp.lon, wp.lat, 0)
        positionProperty.addSample(wpDate, pos)
      }

      positionProperty.setInterpolationOptions({
        interpolationDegree: 1,
        interpolationAlgorithm: Cesium.LinearApproximation,
      })

      positionProperty.forwardExtrapolationType = Cesium.ExtrapolationType.HOLD
      positionProperty.backwardExtrapolationType = Cesium.ExtrapolationType.HOLD

      const serviceColor = SERVICE_COLORS[traj.service] || '#3B82F6'
      const dotIcon = createDotIcon(serviceColor)

      const maxSimSeconds = traj.waypoints[traj.waypoints.length - 1]?.t * 3600 || traj.cycle_hours * 3600 * 10
      const endTime = Cesium.JulianDate.addSeconds(epoch, maxSimSeconds, new Cesium.JulianDate())

      const entity = viewer.entities.add({
        id: `ship-dot-${shipId}`,
        name: traj.name,
        position: positionProperty,
        billboard: {
          image: dotIcon, scale: 1.0,
          scaleByDistance: new Cesium.NearFarScalar(1e3, 1.8, 1e7, 0.5),
          translucencyByDistance: new Cesium.NearFarScalar(5e4, 1.0, 5e8, 0.3),
          heightReference: Cesium.HeightReference.CLAMP_TO_GROUND,
        },
        label: {
          text: traj.name.substring(0, 15), font: '11px sans-serif',
          fillColor: Cesium.Color.WHITE, outlineColor: Cesium.Color.BLACK,
          outlineWidth: 2, style: Cesium.LabelStyle.FILL_AND_OUTLINE,
          verticalOrigin: Cesium.VerticalOrigin.BOTTOM, pixelOffset: new Cesium.Cartesian2(0, -12),
          scaleByDistance: new Cesium.NearFarScalar(5e2, 1.0, 5e6, 0.5),
          translucencyByDistance: new Cesium.NearFarScalar(1e5, 1.0, 1e7, 0.0),
          show: true,
        },
        availability: new Cesium.TimeIntervalCollection([
          new Cesium.TimeInterval({ start: epoch, stop: endTime }),
        ]),
      })

      shipEntitiesRef.current.set(shipId, entity)
      trajAppliedRef.current.add(shipId)
    }
  }, [trajectories, cesiumReady])

  // ---- Virtual clock → Cesium Clock sync ----
  // Cesium is the sole time driver. Backend provides state data only.
  // clock.currentTime is set once on init/reset, then Cesium advances autonomously.
  useEffect(() => {
    if (!viewerRef.current || typeof window === 'undefined' || !window.Cesium) return
    if (!cesiumReady) return

    const Cesium = window.Cesium
    const viewer = viewerRef.current
    const clock = viewer.clock

    const epoch = Cesium.JulianDate.fromDate(new Date('2024-01-01T00:00:00Z'))

    if (!isRunning && currentTime === 0) {
      Cesium.JulianDate.clone(epoch, clock.currentTime)
      Cesium.JulianDate.clone(epoch, clock.startTime)
      clock.shouldAnimate = false
      if (onSimTimeUpdate) onSimTimeUpdate(0)
      return
    }

    if (isRunning) {
      clock.multiplier = speed
      clock.shouldAnimate = true
      clock.clockRange = Cesium.ClockRange.UNBOUNDED
    } else {
      clock.shouldAnimate = false
    }

    const shipsArray = Array.isArray(ships) ? ships : Object.values(ships)
    for (const ship of shipsArray) {
      const entity = shipEntitiesRef.current.get(ship.unique_id)
      if (!entity) continue
      const serviceColor = SERVICE_COLORS[ship.service || ''] || SHIP_COLORS[ship.state] || SHIP_COLORS.default
      if (entity._lastColor !== serviceColor) {
        entity.billboard.image = createDotIcon(serviceColor)
        entity._lastColor = serviceColor
      }
    }
  }, [currentTime, isRunning, speed, ships, cesiumReady])

  // ---- Selected ship 3D model ----
  useEffect(() => {
    if (!viewerRef.current || typeof window === 'undefined' || !window.Cesium) return

    const viewer = viewerRef.current
    const oldModel = viewer.entities.getById('selected-ship-model')
    if (oldModel) viewer.entities.remove(oldModel)

    if (!selectedShipId) return

    const entity = shipEntitiesRef.current.get(selectedShipId)
    if (!entity) return

    const Cesium = window.Cesium

    viewer.entities.add({
      id: 'selected-ship-model',
      position: entity.position,
      orientation: entity.orientation,
      model: {
        uri: '/models/container_ship/scene.gltf',
        scale: 2.2,
        maximumScale: 2.2,
        silhouetteColor: Cesium.Color.fromCssColorString('#ffffff').withAlpha(0.9),
        silhouetteSize: 3,
        heightReference: Cesium.HeightReference.RELATIVE_TO_GROUND,
      },
    })
  }, [selectedShipId, trajectories, cesiumReady])

  // ---- Ports ----
  useEffect(() => {
    if (!viewerRef.current || typeof window === 'undefined' || !window.Cesium) return

    const Cesium = window.Cesium
    const viewer = viewerRef.current
    const entityCollection = viewer.entities

    const portsArray = Array.isArray(ports) ? ports : Object.values(ports)

    portsArray.forEach((port) => {
      const coords = PORT_COORDS[port.unique_id]
      const plat = coords ? coords[0] : port.lat
      const plon = coords ? coords[1] : port.lon
      if (!plat && !plon) return

      const isCongested = port.queue_length > 0
      const color = isCongested ? '#EF4444' : '#10B981'

      const existing = entityCollection.getById(`port-${port.unique_id}`)
      if (existing) {
        existing.position = Cesium.Cartesian3.fromDegrees(plon, plat, 0)
        if (existing._lastColor !== color && existing.billboard) {
          existing.billboard.image = createDotIcon(color, 36)
          existing._lastColor = color
        }
        return
      }

      entityCollection.add({
        id: `port-${port.unique_id}`,
        name: port.name,
        position: Cesium.Cartesian3.fromDegrees(plon, plat, 0),
        billboard: {
          image: createDotIcon(color, 36), scale: 1.0,
          pixelOffset: new Cesium.Cartesian2(0, -8),
          heightReference: Cesium.HeightReference.CLAMP_TO_GROUND,
        },
        label: {
          text: port.name, font: '13px sans-serif',
          fillColor: Cesium.Color.WHITE, outlineColor: Cesium.Color.BLACK,
          outlineWidth: 2, style: Cesium.LabelStyle.FILL_AND_OUTLINE,
          verticalOrigin: Cesium.VerticalOrigin.BOTTOM, pixelOffset: new Cesium.Cartesian2(0, -22),
        },
      })._lastColor = color
    })
  }, [ports, cesiumReady])

  // ---- Click Handler + Debug Mouse Move ----
  useEffect(() => {
    if (!viewerRef.current || typeof window === 'undefined' || !window.Cesium) return

    const Cesium = window.Cesium
    const viewer = viewerRef.current
    const canvas = viewer.scene.canvas as HTMLCanvasElement

    if (clickHandlerRef.current) clickHandlerRef.current.destroy()

    const shipsArray = Array.isArray(ships) ? ships : Object.values(ships)
    const shipIds = new Set(shipsArray.map(s => s.unique_id))
    const portIds = new Set(
      (Array.isArray(ports) ? ports : Object.values(ports)).map(p => `port-${p.unique_id}`)
    )

    clickHandlerRef.current = new Cesium.ScreenSpaceEventHandler(canvas)
    clickHandlerRef.current.setInputAction((click: any) => {
      const picked = viewer.scene.pick(click.position)
      if (picked) {
        const entityId = typeof picked.id === 'string' ? picked.id : picked.id?.id ?? null
        if (entityId && typeof entityId === 'string') {
          const shipId = entityId.startsWith('ship-dot-') ? entityId.replace('ship-dot-', '') : entityId
          if (shipIds.has(shipId)) handleShipClick(shipId)
          else if (entityId.startsWith('port-') && portIds.has(entityId)) handlePortClick(entityId.replace('port-', ''))
        }
      }
    }, Cesium.ScreenSpaceEventType.LEFT_CLICK)

    const moveHandler = new Cesium.ScreenSpaceEventHandler(canvas)
    moveHandler.setInputAction((movement: any) => {
      if (!isDebugMode()) return
      const cartesian = viewer.camera.pickEllipsoid(movement.endPosition, viewer.scene.globe.ellipsoid)
      if (cartesian) {
        const cartographic = Cesium.Cartographic.fromCartesian(cartesian)
        _debugLat = Cesium.Math.toDegrees(cartographic.latitude)
        _debugLon = Cesium.Math.toDegrees(cartographic.longitude)
      }
    }, Cesium.ScreenSpaceEventType.MOUSE_MOVE)

    return () => {
      if (clickHandlerRef.current) { clickHandlerRef.current.destroy(); clickHandlerRef.current = null }
      moveHandler.destroy()
    }
  }, [ships, ports, handleShipClick, handlePortClick])

  // ---- Debug mode state ----
  const [showDebug, setShowDebug] = useState(false)
  useEffect(() => {
    const interval = setInterval(() => { setShowDebug(isDebugMode()) }, 500)
    return () => clearInterval(interval)
  }, [])

  // ---- Route glow dots animation + sim time reporting ----
  useEffect(() => {
    if (!cesiumReady || !viewerRef.current) return

    const Cesium = window.Cesium
    const viewer = viewerRef.current
    let animTime = 0
    const epoch = Cesium.JulianDate.fromDate(new Date('2024-01-01T00:00:00Z'))

    function animate() {
      animFrameRef.current = requestAnimationFrame(animate)
      animTime += 0.008

      // Route glow dots
      const rp = routePositionsRef.current
      if (rp.length && routeDotsRef.current.length) {
        const totalSegs = (rp.length / 2) - 1
        routeDotsRef.current.forEach((dot: any, i: number) => {
          const progress = ((animTime * 0.06 + i * (1 / routeDotsRef.current.length)) % 1)
          const segFloat = progress * totalSegs
          const segIdx = Math.floor(segFloat)
          const frac = segFloat - segIdx
          if (segIdx >= totalSegs) return
          const lon = rp[segIdx * 2] * (1 - frac) + rp[(segIdx + 1) * 2] * frac
          const lat = rp[segIdx * 2 + 1] * (1 - frac) + rp[(segIdx + 1) * 2 + 1] * frac
          dot.position = Cesium.Cartesian3.fromDegrees(lon, lat)
        })
      }

      // Report sim time from Cesium clock
      if (onSimTimeUpdate && viewer.clock) {
        const diff = Cesium.JulianDate.secondsDifference(viewer.clock.currentTime, epoch)
        const simHours = diff / 3600.0
        if (simHours >= 0) {
          onSimTimeUpdate(simHours)
        }
      }
    }

    animate()
    return () => cancelAnimationFrame(animFrameRef.current)
  }, [cesiumReady, onSimTimeUpdate])

  const isRealTime = simulationMode === 'real_time'
  const debugPorts = Object.entries(PORT_COORDS)

  return (
    <div ref={wrapperRef} className="relative w-full h-full" style={{ backgroundColor: '#0a1929' }}>
      <div ref={containerRef} className="w-full h-full" />
      {showDebug && (
        <div className="absolute top-2 right-2 z-20 p-2 rounded bg-black/80 text-xs font-mono text-green-400 max-w-xs pointer-events-none select-none">
          <div className="font-bold text-yellow-400 mb-1">COORD DEBUG (Ctrl+D)</div>
          <div>Mouse: {_debugLat.toFixed(4)}, {_debugLon.toFixed(4)}</div>
          <div className="mt-1 font-bold text-cyan-400">Ports (CSV):</div>
          {debugPorts.slice(0, 25).map(([id, c]) => (
            <div key={id}>{id}: {c[0].toFixed(4)}, {c[1].toFixed(4)}</div>
          ))}
        </div>
      )}
      <div className={`absolute top-3 left-1/2 -translate-x-1/2 z-10 transition-all duration-500 ${
        isRealTime ? 'opacity-100' : 'opacity-0 pointer-events-none'
      }`}>
        <div className="flex items-center gap-2 px-3 py-1 rounded-full bg-green-500/10 border border-green-500/30 backdrop-blur-sm">
          <span className="w-2 h-2 rounded-full bg-green-400 animate-ping" />
          <span className="text-[10px] text-green-400 font-medium tracking-wider">DATA ACTIVE</span>
        </div>
      </div>
    </div>
  )
}