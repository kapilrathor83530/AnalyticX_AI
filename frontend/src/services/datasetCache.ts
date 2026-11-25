import { api } from '../api/client'

export interface PreviewResponse {
  columns: string[]
  rows: Record<string, unknown>[]
  total_rows?: number
}

const previewPromiseCache = new Map<string, Promise<PreviewResponse>>()
const previewDataCache = new Map<string, { data: PreviewResponse; timestamp: number }>()
const CACHE_TTL_MS = 60000 // 1 minute

/**
 * Deduplicated & cached dataset preview loader.
 * Simultaneous requests for the same dataset and limit share a single inflight HTTP request.
 */
export async function getCachedDatasetPreview(datasetId: number, limit = 500): Promise<PreviewResponse> {
  const key = `${datasetId}_${limit}`

  const cached = previewDataCache.get(key)
  if (cached && Date.now() - cached.timestamp < CACHE_TTL_MS) {
    return cached.data
  }

  if (!previewPromiseCache.has(key)) {
    const reqPromise = api
      .get<PreviewResponse>(`/datasets/${datasetId}/preview`, { params: { limit } })
      .then((res) => {
        previewDataCache.set(key, { data: res.data, timestamp: Date.now() })
        previewPromiseCache.delete(key)
        return res.data
      })
      .catch((err) => {
        previewPromiseCache.delete(key)
        throw err
      })
    previewPromiseCache.set(key, reqPromise)
  }

  return previewPromiseCache.get(key)!
}

export function invalidateDatasetPreviewCache(datasetId?: number): void {
  if (datasetId) {
    for (const key of previewDataCache.keys()) {
      if (key.startsWith(`${datasetId}_`)) {
        previewDataCache.delete(key)
      }
    }
    for (const key of previewPromiseCache.keys()) {
      if (key.startsWith(`${datasetId}_`)) {
        previewPromiseCache.delete(key)
      }
    }
  } else {
    previewDataCache.clear()
    previewPromiseCache.clear()
  }
}
