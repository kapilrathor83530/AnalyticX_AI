import { createContext, useCallback, useContext, useEffect, useState } from 'react'
import { authService } from '../services/authService'
import type { GoogleAuthResponse, User } from '../types/auth'

interface AuthContextValue {
  user: User | null
  loading: boolean
  isAuthenticated: boolean
  login: (email: string, password: string, rememberMe?: boolean) => Promise<User>
  register: (email: string, password: string, fullName?: string) => Promise<User>
  loginWithOtp: (challengeId: string, email: string, code: string, fullName?: string) => Promise<User>
  loginWithGoogle: (payload: { email?: string; name?: string; credential?: string }) => Promise<GoogleAuthResponse>
  handleGoogleCallback: (code: string, redirectUri: string) => Promise<GoogleAuthResponse>
  setUser: React.Dispatch<React.SetStateAction<User | null>>
  logout: () => void
  refresh: () => Promise<void>
}

const AuthContext = createContext<AuthContextValue | null>(null)

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<User | null>(null)
  const [loading, setLoading] = useState(true)

  const refresh = useCallback(async () => {
    const token = authService.getToken()
    if (!token) {
      setUser(null)
      setLoading(false)
      return
    }
    try {
      const me = await authService.me()
      setUser(me)
    } catch {
      authService.clearToken()
      setUser(null)
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    refresh()
  }, [refresh])

  async function login(email: string, password: string, rememberMe: boolean = false): Promise<User> {
    const response = await authService.login(email, password, rememberMe)
    setUser(response.user)
    return response.user
  }

  async function register(email: string, password: string, fullName?: string): Promise<User> {
    const response = await authService.register(email, password, fullName)
    setUser(response.user)
    return response.user
  }

  async function loginWithOtp(challengeId: string, email: string, code: string, fullName?: string): Promise<User> {
    const response = await authService.verifyOtp(challengeId, email, code, fullName)
    setUser(response.user)
    return response.user
  }

  async function loginWithGoogle(payload: { email?: string; name?: string; credential?: string }): Promise<GoogleAuthResponse> {
    const response = await authService.loginWithGoogle(payload)
    if ('user' in response) {
      setUser(response.user)
    }
    return response
  }

  async function handleGoogleCallback(code: string, redirectUri: string): Promise<GoogleAuthResponse> {
    const response = await authService.handleGoogleCallback(code, redirectUri)
    if ('user' in response) {
      setUser(response.user)
    }
    return response
  }

  function logout() {
    authService.logout()
    setUser(null)
  }

  return (
    <AuthContext.Provider
      value={{
        user,
        loading,
        isAuthenticated: Boolean(user),
        login,
        register,
        loginWithOtp,
        loginWithGoogle,
        handleGoogleCallback,
        setUser,
        logout,
        refresh,
      }}
    >
      {children}
    </AuthContext.Provider>
  )
}

export function useAuth() {
  const ctx = useContext(AuthContext)
  if (!ctx) throw new Error('useAuth must be used inside AuthProvider')
  return ctx
}
