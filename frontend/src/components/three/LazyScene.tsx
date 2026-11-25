import { Suspense, lazy, useEffect, useState } from 'react'

const DataNodeScene = lazy(() => import('./DataNodeScene'))

export default function LazyScene() {
  const [supported, setSupported] = useState(true)
  const [reducedMotion, setReducedMotion] = useState(false)

  useEffect(() => {
    const canvas = document.createElement('canvas')
    const gl = canvas.getContext('webgl2') || canvas.getContext('webgl')
    setSupported(Boolean(gl))

    const mq = window.matchMedia('(prefers-reduced-motion: reduce)')
    setReducedMotion(mq.matches)
    const handler = () => setReducedMotion(mq.matches)
    mq.addEventListener('change', handler)
    return () => mq.removeEventListener('change', handler)
  }, [])

  if (!supported || reducedMotion) {
    return (
      <div className="flex h-full w-full items-center justify-center rounded-3xl border border-slate-800 bg-slate-950/40">
        <p className="text-sm text-slate-400">3D preview disabled (WebGL or reduced motion).</p>
      </div>
    )
  }

  return (
    <div className="h-full w-full overflow-hidden rounded-3xl border border-slate-800 bg-slate-950/40">
      <Suspense fallback={<div className="flex h-full items-center justify-center text-sm text-slate-500">Loading 3D…</div>}>
        <DataNodeScene />
      </Suspense>
    </div>
  )
}
