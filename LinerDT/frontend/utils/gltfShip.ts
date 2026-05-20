'use client'

import * as THREE from 'three'
import { SHIP_COLORS } from './colors'

function hexToThree(hex: string): THREE.Color {
  return new THREE.Color(hex)
}

function buildShipScene(state: string): THREE.Scene {
  const scene = new THREE.Scene()
  const shipColor = hexToThree(SHIP_COLORS[state] || SHIP_COLORS.default)

  // ---- Hull (tapered box shape) ----
  // Use Shape + ExtrudeGeometry for a side-profile, then rotate
  const hullShape = new THREE.Shape()
  hullShape.moveTo(-0.9, 0)
  hullShape.lineTo(-0.9, 0.06)
  hullShape.quadraticCurveTo(-0.4, 0.10, 0, 0.10)
  hullShape.quadraticCurveTo(0.4, 0.10, 0.85, 0.04)
  hullShape.lineTo(0.9, 0)
  hullShape.closePath()

  const hullGeo = new THREE.ExtrudeGeometry(hullShape, {
    depth: 0.30,
    bevelEnabled: true,
    bevelThickness: 0.035,
    bevelSize: 0.035,
    bevelSegments: 3,
  })
  hullGeo.translate(0, 0, -0.15)
  // Rotate so length is along Z, width along X
  hullGeo.rotateX(-Math.PI / 2)

  const hullMat = new THREE.MeshStandardMaterial({
    color: shipColor,
    roughness: 0.7,
    metalness: 0.1,
    side: THREE.DoubleSide,
  })
  const hull = new THREE.Mesh(hullGeo, hullMat)
  hull.position.set(0, 0, 0)
  scene.add(hull)

  // ---- Deck (thin flat shape on top of hull) ----
  const deckShape = new THREE.Shape()
  deckShape.moveTo(-0.35, -0.85)
  deckShape.quadraticCurveTo(-0.35, 0, 0, 0.80)
  deckShape.quadraticCurveTo(0.35, 0, 0.35, -0.85)
  deckShape.closePath()

  const deckGeo = new THREE.ShapeGeometry(deckShape)
  const deckMat = new THREE.MeshStandardMaterial({
    color: 0x2d3748,
    roughness: 0.9,
    metalness: 0.0,
    side: THREE.DoubleSide,
  })
  const deck = new THREE.Mesh(deckGeo, deckMat)
  deck.rotation.x = -Math.PI / 2
  deck.position.set(0, 0.005, 0)
  scene.add(deck)

  // ---- Containers on deck ----
  const containerColors = [0xE53E3E, 0x3182CE, 0x38A169, 0xD69E2E, 0x805AD5, 0xDD6B20]
  const rowPositions = [-0.45, -0.25, 0.0]
  for (let ri = 0; ri < rowPositions.length; ri++) {
    const zPos = rowPositions[ri]
    for (let ci = 0; ci < 3; ci++) {
      const xPos = -0.12 + ci * 0.12
      const color = containerColors[(ri * 3 + ci) % containerColors.length]
      const cMat = new THREE.MeshStandardMaterial({
        color,
        roughness: 0.6,
        metalness: 0.2,
      })
      const box = new THREE.Mesh(new THREE.BoxGeometry(0.08, 0.04, 0.10), cMat)
      box.position.set(xPos, 0.03 + ri * 0.001, zPos)
      scene.add(box)
    }
  }

  // ---- Superstructure (aft) ----
  const ssMat = new THREE.MeshStandardMaterial({ color: 0x4a5568, roughness: 0.8 })
  const ssBase = new THREE.Mesh(new THREE.BoxGeometry(0.28, 0.06, 0.20), ssMat)
  ssBase.position.set(0, 0.04, -0.50)
  scene.add(ssBase)
  const ssTop = new THREE.Mesh(new THREE.BoxGeometry(0.22, 0.06, 0.16), ssMat)
  ssTop.position.set(0, 0.08, -0.50)
  scene.add(ssTop)

  // ---- Bridge ----
  const bridgeMat = new THREE.MeshStandardMaterial({ color: 0x63b3ed, roughness: 0.3 })
  const bridge = new THREE.Mesh(new THREE.BoxGeometry(0.16, 0.04, 0.12), bridgeMat)
  bridge.position.set(0, 0.12, -0.50)
  scene.add(bridge)

  // ---- Funnel ----
  const funnelMat = new THREE.MeshStandardMaterial({ color: 0xe53e3e, roughness: 0.5 })
  const funnel = new THREE.Mesh(new THREE.CylinderGeometry(0.04, 0.06, 0.10, 6), funnelMat)
  funnel.position.set(0, 0.16, -0.38)
  scene.add(funnel)

  // ---- Mast ----
  const mastMat = new THREE.MeshStandardMaterial({ color: 0x718096, roughness: 0.7 })
  const mast = new THREE.Mesh(new THREE.CylinderGeometry(0.01, 0.01, 0.14, 4), mastMat)
  mast.position.set(0, 0.07, 0.45)
  scene.add(mast)
  const arm = new THREE.Mesh(new THREE.BoxGeometry(0.08, 0.005, 0.005), mastMat)
  arm.position.set(0, 0.12, 0.45)
  scene.add(arm)

  return scene
}

// Cache blob URLs to avoid leaking memory
const uriCache = new Map<string, { uri: string; timestamp: number }>()
const CACHE_TTL = 30000 // 30 seconds

export async function getShipModelUri(state: string): Promise<string> {
  const cached = uriCache.get(state)
  if (cached && Date.now() - cached.timestamp < CACHE_TTL) {
    return cached.uri
  }

  // Clean old cache entries
  uriCache.forEach((val, key) => {
    if (Date.now() - val.timestamp > CACHE_TTL) {
      URL.revokeObjectURL(val.uri)
      uriCache.delete(key)
    }
  })

  try {
    const { GLTFExporter } = await import('three/examples/jsm/exporters/GLTFExporter.js')
    const scene = buildShipScene(state)

    return new Promise((resolve) => {
      const exporter = new GLTFExporter()
      exporter.parse(
        scene,
        (result) => {
          let blob: Blob
          if (result instanceof ArrayBuffer) {
            blob = new Blob([result], { type: 'model/gltf-binary' })
          } else {
            const json = JSON.stringify(result)
            blob = new Blob([json], { type: 'model/gltf+json' })
          }
          const uri = URL.createObjectURL(blob)
          uriCache.set(state, { uri, timestamp: Date.now() })
          resolve(uri)
        },
        (error) => {
          console.error('GLTF export error:', error)
          resolve('') // Return empty string on failure
        },
        { binary: false, trs: false, onlyVisible: true }
      )
    })
  } catch (err) {
    console.error('Failed to load GLTFExporter:', err)
    return ''
  }
}

export function revokeShipModelUri(uri: string) {
  if (uri && uri.startsWith('blob:')) {
    URL.revokeObjectURL(uri)
  }
}

export function clearShipModelCache() {
  uriCache.forEach((val, key) => {
    URL.revokeObjectURL(val.uri)
    uriCache.delete(key)
  })
}
