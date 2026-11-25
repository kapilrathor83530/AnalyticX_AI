import { Canvas, useFrame } from '@react-three/fiber'
import { Float, OrbitControls } from '@react-three/drei'
import { Suspense, useMemo, useRef } from 'react'
import * as THREE from 'three'

function DataNodes() {
  const group = useRef<THREE.Group>(null)

  const points = useMemo(() => {
    const arr: [number, number, number][] = []
    for (let i = 0; i < 40; i++) {
      arr.push([
        (Math.random() - 0.5) * 8,
        (Math.random() - 0.5) * 5,
        (Math.random() - 0.5) * 8,
      ])
    }
    return arr
  }, [])

  useFrame((state) => {
    if (!group.current) return
    const t = state.clock.getElapsedTime()
    group.current.rotation.y = t * 0.05
    group.current.rotation.x = Math.sin(t * 0.1) * 0.1
  })

  return (
    <group ref={group}>
      {points.map((position, i) => (
        <Float key={i} speed={1 + (i % 3) * 0.5} rotationIntensity={0.4} floatIntensity={0.6}>
          <mesh position={position}>
            <sphereGeometry args={[0.08, 16, 16]} />
            <meshBasicMaterial color="#22d3ee" />
          </mesh>
        </Float>
      ))}

      <mesh>
        <icosahedronGeometry args={[1.5, 1]} />
        <meshStandardMaterial color="#0ea5e9" wireframe emissive="#0ea5e9" emissiveIntensity={0.4} />
      </mesh>
    </group>
  )
}

export default function DataNodeScene() {
  return (
    <Canvas camera={{ position: [0, 0, 6], fov: 50 }} dpr={[1, 1.5]}>
      <ambientLight intensity={0.4} />
      <pointLight position={[5, 5, 5]} intensity={1} color="#22d3ee" />
      <Suspense fallback={null}>
        <DataNodes />
      </Suspense>
      <OrbitControls enableZoom={false} enablePan={false} autoRotate autoRotateSpeed={0.5} />
    </Canvas>
  )
}
