export interface UserPreferences {
  theme?: 'dark' | 'light'
  language?: string
  explanation_level?: 'executive' | 'standard' | 'technical'
  email_notifications?: boolean
  date_format?: string
  [key: string]: any
}

export interface User {
  id: number
  email: string
  full_name?: string | null
  is_active: boolean
  is_verified: boolean
  email_verified?: boolean
  auth_provider?: string
  account_status?: string
  profile_image_url?: string | null
  role: string
  primary_goal: string[]
  experience_level: string
  preferences: UserPreferences
  onboarding_completed: boolean
  avatar_url?: string | null
  last_login_at?: string | null
  last_login_method?: string | null
  created_at: string
}

export interface TokenResponse {
  access_token: string
  refresh_token: string
  token_type: string
  user: User
}

export interface Workspace {
  id: number
  user_id?: number | null
  name: string
  description?: string | null
  created_at: string
  updated_at?: string | null
}

export interface UserProfileUpdate {
  full_name?: string
  role?: string
  experience_level?: string
  avatar_url?: string
}

export interface UserPreferencesUpdate {
  theme?: 'dark' | 'light'
  language?: string
  explanation_level?: 'executive' | 'standard' | 'technical'
  email_notifications?: boolean
  date_format?: string
}

export interface OnboardingPayload {
  role: string
  primary_goal: string[]
  experience_level: string
  preferences?: UserPreferences
}

export interface ActivityItem {
  id: number
  user_id: number
  workspace_id?: number | null
  action_type: string
  entity_type?: string | null
  entity_id?: number | null
  title: string
  description?: string | null
  details?: Record<string, any>
  created_at: string
}

export interface NotificationItem {
  id: number
  title: string
  message: string
  level: 'info' | 'success' | 'warning' | 'error'
  is_read: boolean
  link?: string | null
  event_type: string
  created_at?: string | null
}

export interface NotificationListResponse {
  items: NotificationItem[]
  unread_count: number
}

export interface GoogleOAuthConfig {
  configured: boolean
  client_id?: string | null
  email_delivery_configured?: boolean
  instructions: string
}

export interface OtpSendResponse {
  success: boolean
  challenge_id: string
  masked_email: string
  expires_in: number
  cooldown: number
  message: string
}

export interface GoogleLinkChallengeResponse {
  account_linking_required: true
  email: string
  masked_email: string
  linking_token: string
  has_password: boolean
  message: string
}

export interface SmtpTestResponse {
  connected: boolean
  host: string
  port: number
  tls_active: boolean
  sender_configured: boolean
  message: string
  error_detail?: string | null
}

export type GoogleAuthResponse = TokenResponse | GoogleLinkChallengeResponse
