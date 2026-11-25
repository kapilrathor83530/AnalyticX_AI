import axios from 'axios'
import { authService } from '../services/authService'

export const api = axios.create({
  baseURL: import.meta.env.VITE_API_URL || '/api/v1',
  timeout: 60000,
})

api.interceptors.request.use((config) => {
  const token = authService.getToken()
  if (token) {
    config.headers = config.headers || {}
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error?.response?.status === 401) {
      // Clear invalid, revoked, or expired token
      authService.clearToken()

      // Only redirect if not already on an authentication or public landing page
      const path = window.location.pathname
      if (path !== '/login' && path !== '/register' && path !== '/reset-password' && path !== '/') {
        window.location.href = '/login?expired=true'
      }
    }
    return Promise.reject(error)
  },
)

export function getErrorMessage(error: unknown): string {
  if (axios.isAxiosError(error)) {
    return error.response?.data?.detail || error.message
  }
  if (error instanceof Error) {
    return error.message
  }
  return 'Unknown error'
}
