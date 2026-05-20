'use client'

import dynamic from 'next/dynamic'

const CesiumGlobe = dynamic(() => import('../../CesiumGlobe'), { ssr: false })

interface View3DProps {
  ships: any[]
  ports: any[]
  onShipClick: (id: string) => void
  onPortClick: (id: string) => void
  simulationMode: string
}

export default function View3D({ ships, ports, onShipClick, onPortClick, simulationMode }: View3DProps) {
  return (
    <div className="h-full w-full">
      <CesiumGlobe ships={ships} ports={ports} onShipClick={onShipClick} onPortClick={onPortClick} simulationMode={simulationMode} />
    </div>
  )
}
