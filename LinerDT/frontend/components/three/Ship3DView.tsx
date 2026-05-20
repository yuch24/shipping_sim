'use client'

import { useEffect, useRef } from 'react'
import * as THREE from 'three'
import { GLTFLoader } from 'three/examples/jsm/loaders/GLTFLoader.js'

interface Ship3DViewProps {
  state: string
  currentSpeed?: number
  ciiRating?: string
  width?: number
  height?: number
}

const STATE_COLORS: Record<string, number> = {
  IDLE: 0x9CA3AF,
  SAILING: 0x3B82F6,
  ARRIVING: 0xF59E0B,
  BERTHING: 0x10B981,
  WAITING: 0xEF4444,
  LOADING: 0xF97316,
  DEPARTING: 0x06B6D4,
}

// ---- Animated wave surface ----
function createWaveSurface(): THREE.Mesh {
  const geo = new THREE.CircleGeometry(2.0, 48)
  const mat = new THREE.MeshPhongMaterial({
    color: 0x1a365d,
    transparent: true,
    opacity: 0.25,
    side: THREE.DoubleSide,
    shininess: 40,
    specular: new THREE.Color(0x3B82F6),
  })
  const mesh = new THREE.Mesh(geo, mat)
  mesh.rotation.x = -Math.PI / 2
  mesh.position.y = -0.08
  return mesh
}

function updateWaves(mesh: THREE.Mesh, t: number) {
  const pos = mesh.geometry.attributes.position
  const array = pos.array as Float32Array
  for (let i = 0; i < array.length; i += 3) {
    const x = array[i]
    const z = array[i + 1]
    array[i + 2] =
      Math.sin(x * 3.5 + t * 1.5) * 0.012 +
      Math.sin(z * 4.5 + t * 2.0) * 0.010 +
      Math.sin((x + z) * 2.5 + t * 1.2) * 0.008
  }
  pos.needsUpdate = true
  mesh.geometry.computeVertexNormals()
}

// ---- Smoke particle system ----
function createParticleSystem(): { mesh: THREE.Points; update: (t: number) => void } {
  const count = 50
  const positions = new Float32Array(count * 3)
  const data: { vy: number; phase: number; lifetime: number }[] = []

  for (let i = 0; i < count; i++) {
    positions[i * 3] = (Math.random() - 0.5) * 0.02
    positions[i * 3 + 1] = Math.random() * 0.25
    positions[i * 3 + 2] = (Math.random() - 0.5) * 0.02
    data.push({
      vy: 0.003 + Math.random() * 0.006,
      phase: Math.random() * Math.PI * 2,
      lifetime: Math.random(),
    })
  }

  const geo = new THREE.BufferGeometry()
  geo.setAttribute('position', new THREE.Float32BufferAttribute(positions, 3))

  const mat = new THREE.PointsMaterial({
    color: 0x9CA3AF,
    size: 0.035,
    transparent: true,
    opacity: 0.3,
    blending: THREE.AdditiveBlending,
    depthWrite: false,
  })

  const mesh = new THREE.Points(geo, mat)
  mesh.position.set(0, 0.25, -0.6)

  const update = (t: number) => {
    const pos = mesh.geometry.attributes.position.array as Float32Array
    for (let i = 0; i < count; i++) {
      pos[i * 3 + 1] += data[i].vy
      pos[i * 3] += Math.sin(t * 2 + data[i].phase) * 0.0008
      pos[i * 3 + 2] += Math.cos(t * 2.3 + data[i].phase) * 0.0008

      if (pos[i * 3 + 1] > 0.3) {
        pos[i * 3] = (Math.random() - 0.5) * 0.02
        pos[i * 3 + 1] = 0
        pos[i * 3 + 2] = (Math.random() - 0.5) * 0.02
        data[i].lifetime = 0
      } else {
        data[i].lifetime += 0.01
      }
    }
    mesh.geometry.attributes.position.needsUpdate = true

    const heights = pos.filter((_, i) => i % 3 === 1)
    const avgHeight = heights.reduce((a, b) => a + b, 0) / count
    mat.opacity = 0.15 + (1 - avgHeight / 0.3) * 0.2
  }

  return { mesh, update }
}

// ---- State indicator ring (colored ring around the ship) ----
function createStateRing(color: number): THREE.Mesh {
  const geo = new THREE.RingGeometry(0.55, 0.65, 32)
  const mat = new THREE.MeshBasicMaterial({
    color,
    transparent: true,
    opacity: 0.6,
    side: THREE.DoubleSide,
    depthWrite: false,
  })
  const mesh = new THREE.Mesh(geo, mat)
  mesh.rotation.x = -Math.PI / 2
  mesh.position.y = -0.05
  return mesh
}

export default function Ship3DView({
  state,
  currentSpeed,
  width = 240,
  height = 160,
}: Ship3DViewProps) {
  const containerRef = useRef<HTMLDivElement>(null)
  const sceneRef = useRef<THREE.Scene | null>(null)
  const cameraRef = useRef<THREE.PerspectiveCamera | null>(null)
  const rendererRef = useRef<THREE.WebGLRenderer | null>(null)
  const shipGroupRef = useRef<THREE.Group | null>(null)
  const modelRef = useRef<THREE.Group | null>(null)
  const stateRingRef = useRef<THREE.Mesh | null>(null)
  const wakeRef = useRef<THREE.Mesh | null>(null)
  const waveRef = useRef<THREE.Mesh | null>(null)
  const particlesRef = useRef<{ update: (t: number) => void } | null>(null)
  const stateRef = useRef(state)
  const animFrameRef = useRef<number>(0)

  stateRef.current = state

  useEffect(() => {
    if (!containerRef.current) return

    // ---- Scene ----
    const scene = new THREE.Scene()
    sceneRef.current = scene

    // ---- Camera ----
    const camera = new THREE.PerspectiveCamera(35, width / height, 0.1, 50)
    camera.position.set(2.5, 1.8, 3.5)
    camera.lookAt(0, 0, 0)
    cameraRef.current = camera

    // ---- Renderer ----
    const renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true })
    renderer.setSize(width, height)
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2))
    renderer.setClearColor(0x000000, 0)
    renderer.toneMapping = THREE.ACESFilmicToneMapping
    renderer.toneMappingExposure = 1.2
    containerRef.current.appendChild(renderer.domElement)
    rendererRef.current = renderer

    // ---- Lighting ----
    scene.add(new THREE.AmbientLight(0x404060, 0.5))
    const dirLight = new THREE.DirectionalLight(0xffffff, 1.5)
    dirLight.position.set(8, 12, 6)
    scene.add(dirLight)
    const rimLight = new THREE.DirectionalLight(0x4488ff, 0.5)
    rimLight.position.set(-4, 2, -6)
    scene.add(rimLight)
    const backLight = new THREE.DirectionalLight(0xff8844, 0.3)
    backLight.position.set(-3, 2, 5)
    scene.add(backLight)
    const fillLight = new THREE.DirectionalLight(0x88ccff, 0.3)
    fillLight.position.set(0, -1, 0)
    scene.add(fillLight)

    // ---- Ship Group ----
    const shipGroup = new THREE.Group()
    shipGroupRef.current = shipGroup
    scene.add(shipGroup)

    // ---- State Ring (漂浮在船体下方的状态光圈) ----
    const ringColor = STATE_COLORS[state] || STATE_COLORS.IDLE
    const stateRing = createStateRing(ringColor)
    stateRing.position.y = -0.05
    shipGroup.add(stateRing)
    stateRingRef.current = stateRing

    // ---- Wake Trail ----
    const wakeGeo = new THREE.BufferGeometry()
    const wakeVerts = new Float32Array([
      -0.15, 0, -0.8,
      0.15, 0, -0.8,
      0.0, 0, -1.6,
    ])
    wakeGeo.setAttribute('position', new THREE.BufferAttribute(wakeVerts, 3))
    wakeGeo.computeVertexNormals()
    const wakeMat = new THREE.MeshBasicMaterial({
      color: 0xffffff,
      transparent: true,
      opacity: 0,
      side: THREE.DoubleSide,
      depthWrite: false,
    })
    const wake = new THREE.Mesh(wakeGeo, wakeMat)
    wake.position.y = -0.04
    wake.visible = false
    scene.add(wake)
    wakeRef.current = wake

    // ---- Wave Surface ----
    const wave = createWaveSurface()
    scene.add(wave)
    waveRef.current = wave

    // ---- Particle System ----
    const particles = createParticleSystem()
    scene.add(particles.mesh)
    particlesRef.current = particles

    // ---- Load GLTF Model ----
    const loader = new GLTFLoader()
    loader.load(
      '/models/container_ship/scene.gltf',
      (gltf) => {
        const model = gltf.scene

        // GLTF 模型坐标范围约 94.8~96.7 X, 6.2~7.4 Y, -3.07~3.07 Z
        // 居中并缩放到适合视口的尺寸
        model.position.set(-95.75, -6.8, 0)
        model.scale.set(0.14, 0.14, 0.14)

        // 启用阴影
        model.traverse((child) => {
          if (child instanceof THREE.Mesh) {
            child.castShadow = true
            child.receiveShadow = true
            // 提升材质质感
            if (child.material) {
              const mats = Array.isArray(child.material) ? child.material : [child.material]
              mats.forEach((m) => {
                m.roughness = Math.min((m as any).roughness ?? 0.5, 0.6)
                m.metalness = Math.min((m as any).metalness ?? 0.0, 0.3)
              })
            }
          }
        })

        modelRef.current = model
        shipGroup.add(model)
      },
      undefined,
      (error) => {
        console.error('GLTF ship model failed to load:', error)
      }
    )

    // ---- Animation Loop ----
    const animate = () => {
      animFrameRef.current = requestAnimationFrame(animate)
      const time = Date.now() / 1000
      const s = stateRef.current

      // --- Ship motion ---
      let wakeOpacity = 0
      if (shipGroupRef.current) {
        let bobY: number
        let rollZ: number

        switch (s) {
          case 'SAILING':
            bobY = Math.sin(time * 2.2) * 0.015
            rollZ = Math.sin(time * 1.6) * 0.01
            wakeOpacity = 0.2
            break
          case 'BERTHING':
          case 'LOADING':
          case 'UNLOADING':
            bobY = Math.sin(time * 1.0) * 0.02
            rollZ = Math.sin(time * 1.3) * 0.012
            break
          case 'WAITING':
            bobY = Math.sin(time * 1.7) * 0.05
            rollZ = Math.sin(time * 0.9) * 0.04
            break
          case 'ARRIVING':
          case 'DEPARTING':
            bobY = Math.sin(time * 1.5) * 0.025
            rollZ = Math.sin(time * 1.4) * 0.018
            wakeOpacity = 0.08
            break
          default:
            bobY = Math.sin(time * 1.2) * 0.03
            rollZ = Math.sin(time * 1.8) * 0.018
        }

        shipGroupRef.current.position.y = bobY
        shipGroupRef.current.rotation.z = rollZ
        shipGroupRef.current.rotation.y += 0.005
      }

      // --- State ring pulsing ---
      if (stateRingRef.current) {
        const ring = stateRingRef.current
        const mat = ring.material as THREE.MeshBasicMaterial
        mat.opacity = 0.3 + Math.sin(time * 2) * 0.2
        const pulse = 1 + Math.sin(time * 2) * 0.05
        ring.scale.set(pulse, pulse, 1)
      }

      // --- Wake ---
      if (wakeRef.current) {
        const w = wakeRef.current
        w.visible = wakeOpacity > 0
        const mat = w.material as THREE.MeshBasicMaterial
        mat.opacity = wakeOpacity
        const wakeScale = 1 + Math.sin(time * 2) * 0.05
        w.scale.set(wakeScale, wakeScale, 1)
      }

      // --- Waves ---
      if (waveRef.current) {
        updateWaves(waveRef.current, time)
      }

      // --- Particles ---
      if (particlesRef.current) {
        particlesRef.current.update(time)
      }

      renderer.render(scene, camera)
    }
    animate()

    return () => {
      cancelAnimationFrame(animFrameRef.current)
      scene.traverse((obj) => {
        if (obj instanceof THREE.Mesh) {
          obj.geometry?.dispose()
          if (Array.isArray(obj.material)) {
            obj.material.forEach((m) => m.dispose())
          } else {
            obj.material?.dispose()
          }
        }
      })
      if (rendererRef.current && containerRef.current) {
        containerRef.current.removeChild(rendererRef.current.domElement)
      }
      rendererRef.current?.dispose()
    }
  }, [state, width, height])

  // Update ring color when state changes
  useEffect(() => {
    if (stateRingRef.current) {
      const color = STATE_COLORS[state] || STATE_COLORS.IDLE
      ;(stateRingRef.current.material as THREE.MeshBasicMaterial).color.setHex(color)
    }
  }, [state])

  return (
    <div
      ref={containerRef}
      className="rounded-lg overflow-hidden"
      style={{ width: `${width}px`, height: `${height}px` }}
    />
  )
}
