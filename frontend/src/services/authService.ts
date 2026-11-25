import { api } from '../api/client'
import type {
  ActivityItem,
  GoogleAuthResponse,
  GoogleOAuthConfig,
  NotificationListResponse,
  OnboardingPayload,
  OtpSendResponse,
  TokenResponse,
  User,
  UserPreferencesUpdate,
  UserProfileUpdate,
  Workspace,
} from '../types/auth'

const TOKEN_KEY = 'analyticx_token'

export const authService = {
  getToken(): string | null {
    return localStorage.getItem(TOKEN_KEY)
  },

  setToken(token: string) {
    localStorage.setItem(TOKEN_KEY, token)
  },

  clearToken() {
    localStorage.removeItem(TOKEN_KEY)
  },

  async register(email: string, password: string, fullName?: string): Promise<TokenResponse> {
    const response = await api.post<TokenResponse>('/auth/register', {
      email,
      password,
      full_name: fullName,
    })
    this.setToken(response.data.access_token)
    return response.data
  },

  async login(email: string, password: string, rememberMe: boolean = false): Promise<TokenResponse> {
    const response = await api.post<TokenResponse>('/auth/login', {
      email,
      password,
      remember_me: rememberMe,
    })
    this.setToken(response.data.access_token)
    return response.data
  },

  async me(): Promise<User> {
    const response = await api.get<User>('/auth/me')
    return response.data
  },

  async getProfile(): Promise<{ user: User; stats: { dataset_count: number; dashboard_count: number; report_count: number; unread_notifications: number } }> {
    const response = await api.get('/users/profile')
    return response.data
  },

  async updateProfile(payload: UserProfileUpdate): Promise<User> {
    const response = await api.put<User>('/users/profile', payload)
    return response.data
  },

  async updatePreferences(payload: UserPreferencesUpdate): Promise<User> {
    const response = await api.put<User>('/users/preferences', payload)
    return response.data
  },

  async saveOnboarding(payload: OnboardingPayload): Promise<User> {
    const response = await api.post<User>('/users/onboarding', payload)
    return response.data
  },

  async changePassword(currentPassword: string, newPassword: string): Promise<{ updated: boolean; message: string }> {
    const response = await api.post('/users/change-password', {
      current_password: currentPassword,
      new_password: newPassword,
    })
    return response.data
  },

  async requestPasswordReset(email: string): Promise<{ message: string; reset_token?: string }> {
    const response = await api.post('/auth/password-reset/request', { email })
    return response.data
  },

  async confirmPasswordReset(token: string, newPassword: string): Promise<{ updated: boolean; message: string }> {
    const response = await api.post('/auth/password-reset/confirm', {
      token,
      new_password: newPassword,
    })
    return response.data
  },

  async verifyEmail(token: string): Promise<{ verified: boolean; message: string }> {
    const response = await api.post('/auth/verify-email', { token })
    return response.data
  },

  async resendVerification(email: string): Promise<{ sent: boolean; message: string; dev_token?: string }> {
    const response = await api.post('/auth/resend-verification', { email })
    return response.data
  },

  async getActivity(limit: number = 25): Promise<ActivityItem[]> {
    const response = await api.get<ActivityItem[]>('/users/activity', { params: { limit } })
    return response.data
  },

  async getNotifications(unreadOnly: boolean = false): Promise<NotificationListResponse> {
    const response = await api.get<NotificationListResponse>('/users/notifications', { params: { unread_only: unreadOnly } })
    return response.data
  },

  async markNotificationRead(id: number): Promise<void> {
    await api.post(`/users/notifications/${id}/read`)
  },

  async markAllNotificationsRead(): Promise<void> {
    await api.post('/users/notifications/read-all')
  },

  async exportUserData(): Promise<void> {
    const response = await api.get('/users/export-data', { responseType: 'blob' })
    const url = window.URL.createObjectURL(new Blob([response.data]))
    const link = document.createElement('a')
    link.href = url
    link.setAttribute('download', 'analyticx_user_data_export.json')
    document.body.appendChild(link)
    link.click()
    link.remove()
    window.URL.revokeObjectURL(url)
  },

  async deleteAccount(confirmation: string): Promise<{ deleted: boolean; message: string }> {
    const response = await api.delete('/users/account', { params: { confirmation } })
    this.clearToken()
    return response.data
  },

  async getGoogleConfig(): Promise<GoogleOAuthConfig> {
    const response = await api.get<GoogleOAuthConfig>('/auth/oauth/google/config')
    return response.data
  },

  async sendOtp(email: string, purpose: string = 'login'): Promise<OtpSendResponse> {
    const response = await api.post<OtpSendResponse>('/auth/request-otp', { email, purpose })
    return response.data
  },

  async requestOtp(email: string, purpose: string = 'login'): Promise<OtpSendResponse> {
    const response = await api.post<OtpSendResponse>('/auth/request-otp', { email, purpose })
    return response.data
  },

  async resendOtp(email: string, purpose: string = 'login', challengeId?: string): Promise<OtpSendResponse> {
    const response = await api.post<OtpSendResponse>('/auth/resend-otp', {
      email,
      purpose,
      challenge_id: challengeId,
    })
    return response.data
  },

  async signup(payload: { email: string; fullName?: string; password?: string }): Promise<{
    success: boolean
    challenge_id: string
    email: string
    masked_email: string
    expires_in: number
    cooldown: number
    message: string
  }> {
    const response = await api.post('/auth/signup', {
      email: payload.email,
      full_name: payload.fullName,
      password: payload.password,
    })
    return response.data
  },

  async testSmtpConnection(): Promise<{
    connected: boolean
    host: string
    port: number
    tls_active: boolean
    sender_configured: boolean
    message: string
    error_detail?: string | null
  }> {
    const response = await api.post('/auth/smtp/test-connection')
    return response.data
  },

  async verifyOtp(challengeId: string, email: string, code: string, fullName?: string): Promise<TokenResponse> {
    const response = await api.post<TokenResponse>('/auth/verify-otp', {
      challenge_id: challengeId,
      email,
      code,
      full_name: fullName,
    })
    this.setToken(response.data.access_token)
    return response.data
  },

  async loginWithGoogle(payload: { credential?: string; email?: string; name?: string; avatar_url?: string }): Promise<GoogleAuthResponse> {
    const response = await api.post<GoogleAuthResponse>('/auth/oauth/google/verify', payload)
    if ('access_token' in response.data) {
      this.setToken(response.data.access_token)
    }
    return response.data
  },

  async confirmGoogleLink(payload: {
    linking_token: string
    password?: string
    challenge_id?: string
    code?: string
  }): Promise<TokenResponse> {
    const response = await api.post<TokenResponse>('/auth/oauth/google/confirm-link', payload)
    this.setToken(response.data.access_token)
    return response.data
  },

  async handleGoogleCallback(code: string, redirectUri: string): Promise<GoogleAuthResponse> {
    const response = await api.post<GoogleAuthResponse>('/auth/oauth/google/callback', {
      code,
      redirect_uri: redirectUri,
    })
    if ('access_token' in response.data) {
      this.setToken(response.data.access_token)
    }
    return response.data
  },

  async configureGoogleOAuth(clientId: string, clientSecret: string): Promise<{ configured: boolean; message: string }> {
    const response = await api.post('/auth/oauth/google/configure', {
      client_id: clientId,
      client_secret: clientSecret,
    })
    return response.data
  },

  async listWorkspaces(): Promise<Workspace[]> {
    const response = await api.get<Workspace[]>('/workspaces')
    return response.data
  },

  async createWorkspace(name: string, description?: string): Promise<Workspace> {
    const response = await api.post<Workspace>('/workspaces', { name, description })
    return response.data
  },

  async deleteWorkspace(id: number): Promise<void> {
    await api.delete(`/workspaces/${id}`)
  },

  logout() {
    this.clearToken()
  },
}
