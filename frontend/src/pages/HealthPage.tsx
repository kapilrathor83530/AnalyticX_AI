import { HeartPulse } from 'lucide-react'
import { useEffect, useState } from 'react'
import { api, getErrorMessage } from '../api/client'

export default function HealthPage() {
  const [status, setStatus] = useState('Checking...')
  const [error, setError] = useState('')

  useEffect(() => {
    api
      .get('/health')
      .then((response) => setStatus(response.data.status))
      .catch((err) => setError(getErrorMessage(err)))
  }, [])

  return (
    <div className="glass rounded-3xl p-8">
      <div className="mb-4 flex items-center gap-3">
        <HeartPulse className="text-cyan-300" />
        <h1 className="text-2xl font-semibold">System Health</h1>
      </div>
      {error ? (
        <p className="text-red-300">{error}</p>
      ) : (
        <p className="text-slate-300">
          Backend status: <span className="font-semibold text-cyan-300">{status}</span>
        </p>
      )}
    </div>
  )
}
