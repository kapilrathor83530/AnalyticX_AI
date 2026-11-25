import {
  AlertCircle,
  ArrowRight,
  CheckCircle2,
  ExternalLink,
  KeyRound,
  Mail,
  ShieldAlert,
  Sparkles,
  X,
} from 'lucide-react'
import { useState } from 'react'
import { authService } from '../../services/authService'

interface Props {
  isOpen: boolean
  onClose: () => void
  isConfigured?: boolean
  clientId?: string | null
}

export default function GoogleAuthModal({ isOpen, onClose, isConfigured, clientId }: Props) {
  const [inputClientId, setInputClientId] = useState('')
  const [inputClientSecret, setInputClientSecret] = useState('')
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [successMessage, setSuccessMessage] = useState<string | null>(null)

  if (!isOpen) return null

  function handleGoogleOAuthRedirect() {
    if (clientId) {
      const redirectUri = window.location.origin + '/login'
      window.location.href = `https://accounts.google.com/o/oauth2/v2/auth?client_id=${clientId}&response_type=code&scope=openid%20email%20profile&redirect_uri=${encodeURIComponent(
        redirectUri
      )}`
    }
  }

  async function handleSaveCredentials(e: React.FormEvent) {
    e.preventDefault()
    if (!inputClientId.trim() || !inputClientSecret.trim()) {
      setError('Both Google Client ID and Client Secret are required.')
      return
    }
    setSaving(true)
    setError(null)
    setSuccessMessage(null)
    try {
      const res = await authService.configureGoogleOAuth(inputClientId.trim(), inputClientSecret.trim())
      setSuccessMessage(res.message)
      setTimeout(() => {
        window.location.reload()
      }, 1200)
    } catch (err: any) {
      setError(err?.response?.data?.detail || 'Failed to save Google credentials')
    } finally {
      setSaving(false)
    }
  }

  const redirectUri = window.location.origin + '/login'
  const originUri = window.location.origin

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/80 backdrop-blur-md p-4">
      <div className="relative w-full max-w-lg rounded-3xl border border-slate-800 bg-slate-950 p-6 shadow-2xl overflow-hidden">
        {/* Close Button */}
        <button
          onClick={onClose}
          className="absolute right-4 top-4 rounded-xl p-1.5 text-slate-400 hover:bg-slate-800 hover:text-slate-200 transition"
        >
          <X size={18} />
        </button>

        {/* Header */}
        <div className="flex items-center gap-3 border-b border-slate-800/80 pb-4 mb-5">
          <div className="flex h-11 w-11 items-center justify-center rounded-2xl bg-white shadow-md">
            {/* Google G Logo SVG */}
            <svg viewBox="0 0 24 24" className="h-6 w-6">
              <path
                fill="#4285F4"
                d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"
              />
              <path
                fill="#34A853"
                d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"
              />
              <path
                fill="#FBBC05"
                d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.06H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.94l2.85-2.22.81-.63z"
              />
              <path
                fill="#EA4335"
                d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.06l3.66 2.84c.87-2.6 3.3-4.52 6.16-4.52z"
              />
            </svg>
          </div>
          <div>
            <h3 className="text-base font-bold text-slate-100 flex items-center gap-1.5">
              Google Cloud Sign-In
              {isConfigured ? (
                <span className="text-[10px] bg-emerald-500/10 text-emerald-300 border border-emerald-500/30 px-2 py-0.5 rounded-full font-semibold">
                  OAuth Active
                </span>
              ) : (
                <span className="text-[10px] bg-amber-500/10 text-amber-300 border border-amber-500/30 px-2 py-0.5 rounded-full font-semibold">
                  Setup Required
                </span>
              )}
            </h3>
            <p className="text-xs text-slate-400">Official OpenID Connect & OAuth 2.0 Integration</p>
          </div>
        </div>

        {error && (
          <div className="mb-4 flex items-center gap-2 rounded-xl border border-rose-500/30 bg-rose-950/20 p-3 text-xs text-rose-300">
            <AlertCircle size={16} className="shrink-0" />
            <span>{error}</span>
          </div>
        )}

        {successMessage && (
          <div className="mb-4 flex items-center gap-2 rounded-xl border border-emerald-500/30 bg-emerald-950/20 p-3 text-xs text-emerald-300">
            <CheckCircle2 size={16} className="shrink-0" />
            <span>{successMessage}</span>
          </div>
        )}

        {/* If Google is configured on server */}
        {isConfigured && clientId ? (
          <div className="space-y-4 text-center py-2">
            <p className="text-xs text-slate-300 leading-relaxed">
              Google OAuth is active. Click below to authenticate via your Google account using Google's secure consent flow.
            </p>

            <button
              onClick={handleGoogleOAuthRedirect}
              className="w-full flex items-center justify-center gap-3 rounded-2xl bg-white hover:bg-slate-100 text-slate-900 font-bold py-3 px-4 text-xs shadow-lg transition"
            >
              <svg viewBox="0 0 24 24" className="h-4 w-4">
                <path
                  fill="#4285F4"
                  d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"
                />
                <path
                  fill="#34A853"
                  d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"
                />
                <path
                  fill="#FBBC05"
                  d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.06H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.94l2.85-2.22.81-.63z"
                />
                <path
                  fill="#EA4335"
                  d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.06l3.66 2.84c.87-2.6 3.3-4.52 6.16-4.52z"
                />
              </svg>
              <span>Continue to Google Accounts</span>
            </button>
          </div>
        ) : (
          /* When Google Cloud credentials are NOT yet set */
          <div className="space-y-4">
            <div className="rounded-2xl border border-amber-500/30 bg-amber-950/20 p-3.5 text-xs text-amber-200">
              <div className="flex items-center gap-2 font-bold mb-1">
                <ShieldAlert size={16} className="text-amber-400 shrink-0" />
                <span>Google OAuth 2.0 Credentials Required</span>
              </div>
              <p className="text-[11px] text-slate-300 leading-relaxed">
                Analyticx AI enforces genuine server-side Google OpenID Connect identity validation.
                To activate Google Sign-In, please configure your Google Cloud Client ID and Secret below.
              </p>
            </div>

            {/* Quick Setup Instructions */}
            <div className="rounded-2xl border border-slate-800 bg-slate-900/60 p-3.5 text-[11px] space-y-2 text-slate-300">
              <div className="flex items-center justify-between text-slate-200 font-semibold border-b border-slate-800 pb-1.5">
                <span>Google Cloud Console Configuration</span>
                <a
                  href="https://console.cloud.google.com/apis/credentials"
                  target="_blank"
                  rel="noreferrer"
                  className="text-cyan-400 hover:text-cyan-300 flex items-center gap-1 text-[10px]"
                >
                  <span>Open Console</span>
                  <ExternalLink size={11} />
                </a>
              </div>
              <p>1. In Google Cloud Console, create an <strong>OAuth 2.0 Client ID</strong> (Web application).</p>
              <div className="space-y-1 font-mono text-[10px] bg-slate-950 p-2 rounded-xl border border-slate-800">
                <div className="text-slate-400">Authorized JavaScript origin:</div>
                <div className="text-cyan-300">{originUri}</div>
                <div className="text-slate-400 pt-1">Authorized redirect URI:</div>
                <div className="text-cyan-300">{redirectUri}</div>
              </div>
              <p>2. Paste the generated credentials below to save them directly to <span className="font-mono text-cyan-300">backend/.env</span>:</p>
            </div>

            {/* Form to enter Client ID and Secret */}
            <form onSubmit={handleSaveCredentials} className="space-y-3">
              <div>
                <label className="text-[11px] font-semibold text-slate-300 block mb-1">
                  Google Client ID
                </label>
                <input
                  type="text"
                  required
                  placeholder="xxxxx-xxxxx.apps.googleusercontent.com"
                  value={inputClientId}
                  onChange={(e) => setInputClientId(e.target.value)}
                  className="w-full rounded-xl border border-slate-700 bg-slate-900 px-3 py-2 text-xs text-slate-100 placeholder-slate-600 focus:border-cyan-400 focus:outline-none"
                />
              </div>

              <div>
                <label className="text-[11px] font-semibold text-slate-300 block mb-1">
                  Google Client Secret
                </label>
                <input
                  type="password"
                  required
                  placeholder="GOCSPX-xxxxxxxxxxxxxxxx"
                  value={inputClientSecret}
                  onChange={(e) => setInputClientSecret(e.target.value)}
                  className="w-full rounded-xl border border-slate-700 bg-slate-900 px-3 py-2 text-xs text-slate-100 placeholder-slate-600 focus:border-cyan-400 focus:outline-none"
                />
              </div>

              <div className="flex items-center justify-between pt-1">
                <button
                  type="button"
                  onClick={onClose}
                  className="text-xs text-slate-400 hover:text-slate-200"
                >
                  Use Email OTP instead
                </button>
                <button
                  type="submit"
                  disabled={saving}
                  className="rounded-xl bg-cyan-400 hover:bg-cyan-300 text-slate-950 font-bold px-4 py-2 text-xs transition disabled:opacity-50 flex items-center gap-1.5"
                >
                  <KeyRound size={14} />
                  <span>{saving ? 'Activating...' : 'Save & Activate'}</span>
                </button>
              </div>
            </form>
          </div>
        )}
      </div>
    </div>
  )
}
