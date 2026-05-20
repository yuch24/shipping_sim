'use client'

import { useEffect, useRef } from 'react'
import * as THREE from 'three'
import { GLTFLoader } from 'three/examples/jsm/loaders/GLTFLoader.js'

interface Port3DViewProps {
  queueLength: number
  availableBerths: number
  totalBerths: number
  width?: number
  height?: number
}

function createWaterSurface(): THREE.Mesh {
  const geo = new THREE.CircleGeometry(2.8, 48)
  const mat = new THREE.MeshPhongMaterial({
    color: 0x1a365d,
    transparent: true,
    opacity: 0.15,
    side: THREE.DoubleSide,
    shininess: 30,
    specular: new THREE.Color(0x3B82F6),
  })
  const mesh = new THREE.Mesh(geo, mat)
  mesh.rotation.x = -Math.PI / 2
  mesh.position.y = -0.04
  return mesh
}

function updateWater(mesh: THREE.Mesh, t: number) {
  const pos = mesh.geometry.attributes.position
  const array = pos.array as Float32Array
  for (let i = 0; i < array.length; i += 3) {
    const x = array[i]
    const z = array[i + 1]
    array[i + 2] =
      Math.sin(x * 2.5 + t * 1.2) * 0.01 +
      Math.sin(z * 3.0 + t * 1.8) * 0.008 +
      Math.sin((x + z) * 2.0 + t * 0.8) * 0.006
  }
  pos.needsUpdate = true
  mesh.geometry.computeVertexNormals()
}

export default function Port3DView({
  queueLength,
  availableBerths,
  totalBerths,
  width = 240,
  height = 160,
}: Port3DViewProps) {
  const containerRef = useRef<HTMLDivElement>(null)
  const sceneRef = useRef<THREE.Scene | null>(null)
  const rendererRef = useRef<THREE.WebGLRenderer | null>(null)
  const cameraRef = useRef<THREE.PerspectiveCamera | null>(null)
  const groupRef = useRef<THREE.Group | null>(null)
  const modelRef = useRef<THREE.Group | null>(null)
  const waterRef = useRef<THREE.Mesh | null>(null)
  const animFrameRef = useRef<number>(0)

  const occupiedCount = totalBerths - availableBerths

  useEffect(() => {
    if (!containerRef.current) return

    // Scene
    const scene = new THREE.Scene()
    sceneRef.current = scene

    // Camera
    const camera = new THREE.PerspectiveCamera(35, width / height, 0.1, 50)
    camera.position.set(3, 2.5, 4)
    camera.lookAt(0, 0, 0)
    cameraRef.current = camera

    // Renderer
    const renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true })
    renderer.setSize(width, height)
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2))
    renderer.setClearColor(0x000000, 0)
    renderer.toneMapping = THREE.ACESFilmicToneMapping
    renderer.toneMappingExposure = 1.0
    containerRef.current.appendChild(renderer.domElement)
    rendererRef.current = renderer

    // Lighting
    scene.add(new THREE.AmbientLight(0x404060, 0.5))
    const dirLight = new THREE.DirectionalLight(0xffffff, 1.2)
    dirLight.position.set(5, 10, 5)
    scene.add(dirLight)
    const rimLight = new THREE.DirectionalLight(0x4488ff, 0.4)
    rimLight.position.set(-3, 1, -5)
    scene.add(rimLight)

    // Water
    const water = createWaterSurface()
    scene.add(water)
    waterRef.current = water

    // Port group
    const group = new THREE.Group()
    groupRef.current = group
    scene.add(group)

    // ---- Berth occupancy indicators (泊位占用指示器) ----
    const berthIndicators: THREE.Mesh[] = []
    const spacing = 1.0 / Math.max(totalBerths, 1)
    const startX = -0.5 + spacing / 2

    for (let i = 0; i < totalBerths; i++) {
      const isOccupied = i >= availableBerths
      const color = isOccupied ? 0xEF4444 : 0x10B981

      const indicatorMat = new THREE.MeshBasicMaterial({
        color,
        transparent: true,
        opacity: 0.7,
      })
      const indicator = new THREE.Mesh(
        new THREE.CircleGeometry(0.04, 12),
        indicatorMat
      )
      indicator.position.set(startX + i * spacing, 0.02, 0.55)
      indicator.rotation.x = -Math.PI / 2
      indicator.userData = { isOccupied, idx: i, baseColor: color }
      group.add(indicator)
      berthIndicators.push(indicator)
    }

    // ---- Waiting queue indicators (排队船舶指示器) ----
    const waitingIndicators: THREE.Mesh[] = []
    for (let i = 0; i < Math.min(queueLength, 5); i++) {
      const wMat = new THREE.MeshBasicMaterial({
        color: 0xEF4444,
        transparent: true,
        opacity: 0.6,
      })
      const wShip = new THREE.Mesh(new THREE.CircleGeometry(0.035, 8), wMat)
      wShip.position.set(-0.6 + i * 0.25, 0.02, 0.85)
      wShip.rotation.x = -Math.PI / 2
      group.add(wShip)
      waitingIndicators.push(wShip)
    }

    // ---- Load GLTF Model ----
    const loader = new GLTFLoader()
    loader.load(
      '/models/glan_port/scene.gltf',
      (gltf) => {
        const model = gltf.scene

        // 调整位置和缩放
        model.position.set(0, 0, 0)
        model.scale.set(0.008, 0.008, 0.008)

        // 优化材质
        model.traverse((child) => {
          if (child instanceof THREE.Mesh) {
            child.castShadow = true
            child.receiveShadow = true
            if (child.material) {
              const mats = Array.isArray(child.material) ? child.material : [child.material]
              mats.forEach((m) => {
                m.roughness = Math.min((m as any).roughness ?? 0.5, 0.7)
              })
            }
          }
        })

        modelRef.current = model
        group.add(model)
      },
      undefined,
      (error) => {
        console.error('GLTF port model failed to load:', error)
      }
    )

    // ---- Animation Loop ----
    const animate = () => {
      animFrameRef.current = requestAnimationFrame(animate)
      const t = Date.now() / 1000

      // Slow rotation
      if (groupRef.current) {
        groupRef.current.rotation.y += 0.003
      }

      // Pulsing berth indicators
      berthIndicators.forEach((indicator) => {
        const mat = indicator.material as THREE.MeshBasicMaterial
        if (indicator.userData.isOccupied) {
          mat.opacity = 0.5 + Math.sin(t * 2.5 + indicator.userData.idx) * 0.3
        } else {
          mat.opacity = 0.4 + Math.sin(t * 1.0 + indicator.userData.idx) * 0.2
        }
        // Pulsing scale
        const pulse = indicator.userData.isOccupied
          ? 1 + Math.sin(t * 2.5 + indicator.userData.idx) * 0.15
          : 1 + Math.sin(t * 1.0 + indicator.userData.idx) * 0.1
        indicator.scale.set(pulse, pulse, 1)
      })

      // Pulsing waiting indicators
      waitingIndicators.forEach((w, i) => {
        const mat = w.material as THREE.MeshBasicMaterial
        mat.opacity = 0.4 + Math.sin(t * 1.8 + i * 1.2) * 0.25
      })

      // Animate water
      if (waterRef.current) {
        updateWater(waterRef.current, t)
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
  }, [queueLength, availableBerths, totalBerths, width, height])

  return (
    <div
      ref={containerRef}
      className="rounded-lg overflow-hidden"
      style={{ width: `${width}px`, height: `${height}px` }}
    />
  )
}
