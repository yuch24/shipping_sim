'use client'

import dynamic from 'next/dynamic'
import { useState } from 'react'
import MapErrorBoundary from './MapErrorBoundary'

const CesiumGlobe = dynamic(() => import('../CesiumGlobe'), {
  ssr: false,
  loading: () => (
    <div className="w-full h-full flex items-center justify-center bg-[#0a1929]">
      <div className="text-center">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-marine-500 mx-auto mb-4" />
        <p className="text-gray-400">加载 3D 地球...</p>
      </div>
    </div>
  ),
})

const LeafletMap = dynamic(() => import('./LeafletMap'), {
  ssr: false,
  loading: () => (
    <div className="w-full h-full flex items-center justify-center bg-[#0a1929]">
      <div className="text-center">
        <div className="animate-spin rounded-full h-10 w-10 border-b-2 border-gray-500 mx-auto mb-3" />
        <p className="text-gray-400">加载 2D 地图...</p>
      </div>
    </div>
  ),
})

interface MapContainerProps {
  ships: Record<string, any>
  ports: Record<string, any>
  routes?: string[][]
  className?: string
  selectedShipId?: string | null
  onShipClick?: (shipId: string) => void
  onPortClick?: (portId: string) => void
  simulationMode?: string
  mapType: '3d' | '2d'
  trajectories?: Record<string, any> | null
  currentTime?: number
  isRunning?: boolean
  speed?: number
  onSimTimeUpdate?: (simHours: number) => void
}

export default function MapContainer({
  ships,
  ports,
  routes,
  className = '',
  selectedShipId,
  onShipClick,
  onPortClick,
  simulationMode = 'academic',
  mapType,
  trajectories,
  currentTime = 0,
  isRunning = false,
  speed = 60,
  onSimTimeUpdate,
}: MapContainerProps) {
  const [isTransitioning, setIsTransitioning] = useState(false)

  return (
    <div className={`relative w-full h-full ${className}`}>
      {/* 地图内容层 — 使用 z-0 确保不遮挡同层 z-30 的 MapToggle */}
      <div
        className={`
          absolute inset-0 z-0 transition-opacity duration-300
          ${isTransitioning ? 'opacity-0' : 'opacity-100'}
        `.trim()}
        style={undefined}
      >
        {mapType === '3d' ? (
          <MapErrorBoundary>
            <div className="w-full h-full isolate">
              <CesiumGlobe
                ships={ships}
                ports={ports}
                routes={routes}
                selectedShipId={selectedShipId}
                onShipClick={onShipClick}
                onPortClick={onPortClick}
                simulationMode={simulationMode}
                trajectories={trajectories}
                currentTime={currentTime}
                isRunning={isRunning}
                speed={speed}
                onSimTimeUpdate={onSimTimeUpdate}
              />
            </div>
          </MapErrorBoundary>
        ) : (
          <div style={{ pointerEvents: 'all' }} className="absolute inset-0 z-0">
            <LeafletMap
              ships={ships}
              ports={ports}
              onShipClick={onShipClick}
              onPortClick={onPortClick}
            />
          </div>
        )}
      </div>

    </div>
  )
}