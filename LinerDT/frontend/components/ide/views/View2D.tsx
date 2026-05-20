'use client'

import dynamic from 'next/dynamic'

const LeafletMap = dynamic(() => import('../../map/LeafletMap'), { ssr: false })

interface View2DProps {
  ships: any[]
  ports: any[]
  onShipClick: (id: string) => void
  onPortClick: (id: string) => void
}

export default function View2D({ ships, ports, onShipClick, onPortClick }: View2DProps) {
  return (
    <div className="h-full w-full">
      <LeafletMap
        ships={ships}
        ports={ports}
        onShipClick={onShipClick}
        onPortClick={onPortClick}
      />
    </div>
  )
}
