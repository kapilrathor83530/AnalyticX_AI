import { useEffect, useState } from 'react'
import { llmService } from '../services/llmService'
import type { ModelStatus } from '../types/llm'

export function useLLM() {
  const [status, setStatus] = useState<ModelStatus | null>(null)
  const [loading, setLoading] = useState(true)

  async function refresh() {
    setLoading(true)
    try {
      const data = await llmService.status()
      setStatus(data)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    refresh()
  }, [])

  return { status, loading, refresh }
}
