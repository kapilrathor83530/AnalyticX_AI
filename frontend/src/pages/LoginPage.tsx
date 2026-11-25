import {
  ArrowLeft,
  ArrowRight,
  CheckCircle2,
  Clock,
  Eye,
  EyeOff,
  KeyRound,
  Lock,
  Mail,
  RefreshCw,
  ShieldCheck,
  Sparkles,
  X,
} from 'lucide-react'
import { useEffect, useState } from 'react'
import { Link, useLocation, useNavigate } from 'react-router-dom'
import { getErrorMessage } from '../api/client'
import AccountLinkingModal from '../components/auth/AccountLinkingModal'
import GoogleAuthModal from '../components/auth/GoogleAuthModal'
import { useAuth } from '../contexts/AuthContext'
import { authService } from '../services/authService'
import type { GoogleLinkChallengeResponse } from '../types/auth'

export default function LoginPage() {
  const { login, loginWithOtp, handleGoogleCallback } = useAuth()
  const navigate = useNavigate()
  const location = useLocation()

  // Authentication Mode: default to 'otp' (Real Gmail OTP Verification)
  const [authMode, setAuthMode] = useState<'password' | 'otp'>('otp')

  // Password Login State
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [rememberMe, setRememberMe] = useState(true)
  const [showPassword, setShowPassword] = useState(false)

  // Passwordless Email OTP State
  const [otpEmail, setOtpEmail] = useState('')
  const [otpCode, setOtpCode] = useState('')
  const [otpChallengeId, setOtpChallengeId] = useState('')
  const [maskedEmail, setMaskedEmail] = useState('')
  const [otpStep, setOtpStep] = useState<'request' | 'verify'>('request')
  const [otpCooldown, setOtpCooldown] = useState(0)
  const [otpExpiresIn, setOtpExpiresIn] = useState(300)

  // Status & Errors
  const [error, setError] = useState('')
  const [successMessage, setSuccessMessage] = useState('')
  const [loading, setLoading] = useState(false)
  const [oauthProcessing, setOauthProcessing] = useState(false)

  // Modals State
  const [forgotModalOpen, setForgotModalOpen] = useState(false)
  const [forgotEmail, setForgotEmail] = useState('')
  const [forgotMessage, setForgotMessage] = useState('')
  const [forgotToken, setForgotToken] = useState('')
  const [forgotLoading, setForgotLoading] = useState(false)

  const [googleModalOpen, setGoogleModalOpen] = useState(false)
  const [googleConfig, setGoogleConfig] = useState<{
    configured: boolean
    client_id?: string | null
    instructions: string
  } | null>(null)
  const [linkingChallenge, setLinkingChallenge] = useState<GoogleLinkChallengeResponse | null>(null)

  // Cooldown countdown timer
  useEffect(() => {
    if (otpCooldown <= 0) return
    const timer = setInterval(() => {
      setOtpCooldown((prev) => (prev <= 1 ? 0 : prev - 1))
    }, 1000)
    return () => clearInterval(timer)
  }, [otpCooldown])

  // Expiration countdown timer
  useEffect(() => {
    if (otpStep !== 'verify' || otpExpiresIn <= 0) return
    const timer = setInterval(() => {
      setOtpExpiresIn((prev) => (prev <= 1 ? 0 : prev - 1))
    }, 1000)
    return () => clearInterval(timer)
  }, [otpStep, otpExpiresIn])

  // Check for Google OAuth callback in URL
  useEffect(() => {
    const params = new URLSearchParams(window.location.search)
    const code = params.get('code')
    if (code) {
      setOauthProcessing(true)
      setError('')
      const redirectUri = window.location.origin + '/login'
      handleGoogleCallback(code, redirectUri)
        .then((res) => {
          window.history.replaceState({}, document.title, window.location.pathname)
          if ('account_linking_required' in res && res.account_linking_required) {
            setLinkingChallenge(res as GoogleLinkChallengeResponse)
          } else if ('user' in res) {
            if (!res.user.onboarding_completed) {
              navigate('/onboarding')
            } else {
              navigate('/workspace')
            }
          }
        })
        .catch((err) => {
          setError(getErrorMessage(err))
          window.history.replaceState({}, document.title, window.location.pathname)
        })
        .finally(() => {
          setOauthProcessing(false)
        })
    }
  }, [handleGoogleCallback, navigate])

  // Handle Password Login Submission
  async function submitPasswordLogin(e: React.FormEvent) {
    e.preventDefault()
    setError('')
    setLoading(true)
    try {
      const user = await login(email.trim(), password, rememberMe)
      const fromPath = (location.state as any)?.from?.pathname
      const target = !user.onboarding_completed ? '/onboarding' : (fromPath || '/workspace')
      navigate(target)
    } catch (err) {
      const msg = getErrorMessage(err)
      setError(msg)
      if (msg.toLowerCase().includes('not been verified') || msg.toLowerCase().includes('verify your email')) {
        setOtpEmail(email.trim())
      }
    } finally {
      setLoading(false)
    }
  }

  // Handle Requesting OTP Code
  async function handleSendOtp(e?: React.FormEvent) {
    if (e) e.preventDefault()
    if (!otpEmail.trim()) {
      setError('Please enter your email address.')
      return
    }
    setError('')
    setSuccessMessage('')
    setLoading(true)
    try {
      const res = await authService.sendOtp(otpEmail.trim(), 'login')
      setOtpChallengeId(res.challenge_id)
      setMaskedEmail(res.masked_email)
      setOtpCooldown(res.cooldown || 60)
      setOtpExpiresIn(res.expires_in || 300)
      setOtpStep('verify')
      setSuccessMessage(res.message)
    } catch (err) {
      setError(getErrorMessage(err))
    } finally {
      setLoading(false)
    }
  }

  // Handle Verifying OTP Code
  async function handleVerifyOtp(e: React.FormEvent) {
    e.preventDefault()
    if (!otpCode.trim() || otpCode.trim().length !== 6) {
      setError('Please enter the 6-digit code sent to your email.')
      return
    }
    setError('')
    setLoading(true)
    try {
      const user = await loginWithOtp(otpChallengeId, otpEmail.trim(), otpCode.trim())
      const fromPath = (location.state as any)?.from?.pathname
      const target = !user.onboarding_completed ? '/onboarding' : (fromPath || '/workspace')
      navigate(target)
    } catch (err) {
      setError(getErrorMessage(err))
    } finally {
      setLoading(false)
    }
  }

  // Handle Google Login Click
  async function handleGoogleClick() {
    setError('')
    try {
      const cfg = await authService.getGoogleConfig()
      setGoogleConfig(cfg)
      if (cfg.configured && cfg.client_id) {
        // Redirect to real Google OAuth endpoint
        const redirectUri = window.location.origin + '/login'
        window.location.href = `https://accounts.google.com/o/oauth2/v2/auth?client_id=${cfg.client_id}&response_type=code&scope=openid%20email%20profile&redirect_uri=${encodeURIComponent(
          redirectUri
        )}`
      } else {
        setGoogleModalOpen(true)
      }
    } catch {
      setGoogleModalOpen(true)
    }
  }

  function fillDemo() {
    setEmail('demo@analyticx.ai')
    setPassword('analyticx123')
    setAuthMode('password')
    setError('')
  }

  async function handleForgotPassword(e: React.FormEvent) {
    e.preventDefault()
    if (!forgotEmail.trim()) return
    setForgotLoading(true)
    setForgotMessage('')
    try {
      const res = await authService.requestPasswordReset(forgotEmail.trim())
      setForgotMessage(res.message)
      if (res.reset_token) {
        setForgotToken(res.reset_token)
      }
    } catch (err) {
      setForgotMessage(getErrorMessage(err))
    } finally {
      setForgotLoading(false)
    }
  }

  const formatTimer = (seconds: number) => {
    const mins = Math.floor(seconds / 60)
    const secs = seconds % 60
    return `${mins}:${secs < 10 ? '0' : ''}${secs}`
  }

  return (
    <div className="min-h-[85vh] flex flex-col justify-center items-center px-4 py-12">
      <div className="w-full max-w-md">
        {/* Back Link */}
        <Link
          to="/"
          className="inline-flex items-center gap-1.5 text-xs text-slate-400 hover:text-cyan-300 transition mb-6"
        >
          <ArrowLeft size={14} />
          <span>Back to Home</span>
        </Link>

        {/* Login Card */}
        <div className="glass rounded-3xl border border-slate-800 bg-slate-950/85 p-8 shadow-2xl backdrop-blur-2xl relative overflow-hidden">
          {/* Subtle Ambient Glow */}
          <div className="absolute -top-24 -right-24 h-48 w-48 rounded-full bg-cyan-500/10 blur-3xl pointer-events-none" />
          <div className="absolute -bottom-24 -left-24 h-48 w-48 rounded-full bg-blue-500/10 blur-3xl pointer-events-none" />

          {/* Header */}
          <div className="mb-6 text-center">
            <div className="inline-flex h-12 w-12 items-center justify-center rounded-2xl bg-gradient-to-tr from-cyan-400 to-blue-500 text-slate-950 mb-3 shadow-lg shadow-cyan-500/20">
              <Sparkles size={24} />
            </div>
            <h1 className="text-2xl font-bold tracking-tight text-slate-100">Welcome Back</h1>
            <p className="mt-1 text-xs text-slate-400">
              Sign in to your <span className="text-cyan-300 font-medium">Analyticx AI</span> personalized workspace
            </p>
          </div>

          {/* Demo Account Quick-Fill Pill */}
          <div className="mb-6 rounded-2xl border border-cyan-500/30 bg-cyan-950/20 p-3 text-xs text-slate-300 flex items-center justify-between">
            <div className="flex items-center gap-2">
              <CheckCircle2 size={16} className="text-cyan-400 shrink-0" />
              <div>
                <p className="font-medium text-cyan-200">1-Click Demo Login (Kapil)</p>
                <p className="text-[10px] text-slate-400">demo@analyticx.ai • analyticx123</p>
              </div>
            </div>
            <button
              type="button"
              onClick={fillDemo}
              className="rounded-lg bg-cyan-400/20 px-3 py-1 text-[11px] font-semibold text-cyan-300 hover:bg-cyan-400/30 transition border border-cyan-400/30"
            >
              Fill Demo
            </button>
          </div>

          {/* OAuth Callback Processing Banner */}
          {oauthProcessing && (
            <div className="mb-4 rounded-xl border border-cyan-500/30 bg-cyan-950/40 px-4 py-3 text-xs text-cyan-200 flex items-center gap-2.5">
              <div className="h-4 w-4 rounded-full border-2 border-cyan-400 border-t-transparent animate-spin shrink-0" />
              <span>Verifying Google identity and establishing session...</span>
            </div>
          )}

          {/* Error Banner */}
          {error && (
            <div className="mb-4 rounded-xl border border-red-500/30 bg-red-500/10 px-4 py-3 text-xs text-red-300 flex items-start gap-2">
              <div className="h-1.5 w-1.5 rounded-full bg-red-400 mt-1 shrink-0" />
              <span>{error}</span>
            </div>
          )}

          {/* Success Banner */}
          {successMessage && (
            <div className="mb-4 rounded-xl border border-emerald-500/30 bg-emerald-950/20 px-4 py-3 text-xs text-emerald-300 flex items-start gap-2">
              <CheckCircle2 size={16} className="text-emerald-400 shrink-0 mt-0.5" />
              <span>{successMessage}</span>
            </div>
          )}

          {/* 1. Continue with Google Button */}
          <button
            type="button"
            onClick={handleGoogleClick}
            disabled={loading || oauthProcessing}
            className="w-full rounded-2xl border border-slate-700 bg-slate-900/90 hover:bg-slate-800 py-3 px-4 text-xs font-semibold text-slate-100 transition shadow-md flex items-center justify-center gap-3 group"
          >
            <svg className="h-4 w-4" viewBox="0 0 24 24">
              <path
                fill="#4285F4"
                d="M23.745 12.27c0-.7-.06-1.4-.19-2.07H12v4.51h6.6c-.29 1.52-1.14 2.8-2.4 3.66v3.05h3.88c2.27-2.09 3.66-5.17 3.66-9.15z"
              />
              <path
                fill="#34A853"
                d="M12 24c3.24 0 5.95-1.08 7.93-2.91l-3.88-3.05c-1.08.72-2.45 1.16-4.05 1.16-3.12 0-5.77-2.1-6.72-4.93H1.25v3.15C3.26 21.36 7.33 24 12 24z"
              />
              <path
                fill="#FBBC05"
                d="M5.28 14.27c-.25-.72-.38-1.49-.38-2.27s.13-1.55.38-2.27V6.58H1.25C.45 8.17 0 9.99 0 12s.45 3.83 1.25 5.42l4.03-3.15z"
              />
              <path
                fill="#EA4335"
                d="M12 4.75c1.77 0 3.35.61 4.6 1.8l3.42-3.42C17.95 1.19 15.24 0 12 0 7.33 0 3.26 2.64 1.25 6.58l4.03 3.15c.95-2.83 3.6-4.98 6.72-4.98z"
              />
            </svg>
            <span className="group-hover:text-cyan-200 transition">Continue with Google</span>
          </button>

          {/* Social Divider */}
          <div className="relative my-6 text-center">
            <div className="absolute inset-0 flex items-center">
              <div className="w-full border-t border-slate-800" />
            </div>
            <span className="relative bg-slate-950/90 px-3 text-[10px] text-slate-500 uppercase tracking-widest font-semibold">
              Or continue with email
            </span>
          </div>

          {/* Authentication Mode Tabs */}
          <div className="grid grid-cols-2 rounded-xl bg-slate-900/80 p-1 mb-5 border border-slate-800">
            <button
              type="button"
              onClick={() => {
                setAuthMode('otp')
                setError('')
              }}
              className={`flex items-center justify-center gap-1.5 py-2 text-xs font-semibold rounded-lg transition ${
                authMode === 'otp'
                  ? 'bg-slate-800 text-cyan-300 shadow-sm border border-slate-700/60'
                  : 'text-slate-400 hover:text-slate-200'
              }`}
            >
              <Mail size={13} />
              <span>Email Code (OTP)</span>
            </button>
            <button
              type="button"
              onClick={() => {
                setAuthMode('password')
                setError('')
              }}
              className={`flex items-center justify-center gap-1.5 py-2 text-xs font-semibold rounded-lg transition ${
                authMode === 'password'
                  ? 'bg-slate-800 text-cyan-300 shadow-sm border border-slate-700/60'
                  : 'text-slate-400 hover:text-slate-200'
              }`}
            >
              <KeyRound size={13} />
              <span>Email & Password</span>
            </button>
          </div>

          {/* 2. Passwordless Email OTP Flow */}
          {authMode === 'otp' && (
            <div>
              {otpStep === 'request' ? (
                <form onSubmit={handleSendOtp} className="space-y-4">
                  <div>
                    <label htmlFor="otp-email" className="mb-1.5 block text-xs font-medium text-slate-300">
                      Email Address
                    </label>
                    <div className="relative">
                      <input
                        id="otp-email"
                        type="email"
                        required
                        placeholder="Enter your email address"
                        className="w-full rounded-xl border border-slate-700 bg-slate-900/90 pl-10 pr-3 py-2.5 text-sm text-slate-100 placeholder-slate-500 outline-none focus:border-cyan-400 transition"
                        value={otpEmail}
                        onChange={(e) => setOtpEmail(e.target.value)}
                      />
                      <Mail size={16} className="absolute left-3.5 top-3 text-slate-500 pointer-events-none" />
                    </div>
                  </div>

                  <p className="text-[11px] text-slate-400 leading-relaxed">
                    We will send a cryptographically secure 6-digit one-time code to your email. No password needed.
                  </p>

                  <button
                    type="submit"
                    disabled={loading || !otpEmail.trim()}
                    className="w-full rounded-xl bg-gradient-to-r from-cyan-400 to-blue-500 py-3 text-sm font-semibold text-slate-950 shadow-lg shadow-cyan-500/20 hover:from-cyan-300 hover:to-blue-400 transition disabled:opacity-60 flex items-center justify-center gap-2"
                  >
                    {loading ? (
                      <>
                        <div className="h-4 w-4 rounded-full border-2 border-slate-950 border-t-transparent animate-spin" />
                        <span>Sending Verification Code...</span>
                      </>
                    ) : (
                      <>
                        <span>Send Verification Code</span>
                        <ArrowRight size={15} />
                      </>
                    )}
                  </button>
                </form>
              ) : (
                /* OTP Verification Screen */
                <form onSubmit={handleVerifyOtp} className="space-y-4">
                  <div className="rounded-2xl border border-cyan-500/30 bg-cyan-950/20 p-3.5 text-center">
                    <p className="text-xs text-slate-200">
                      We sent a verification code to <strong className="text-cyan-300">{maskedEmail}</strong>
                    </p>
                    <div className="flex items-center justify-center gap-3 mt-2 text-[11px] text-slate-400">
                      <span className="flex items-center gap-1 text-slate-400">
                        <Clock size={12} className="text-cyan-400" />
                        Expires in {formatTimer(otpExpiresIn)}
                      </span>
                      <span>•</span>
                      <button
                        type="button"
                        onClick={() => {
                          setOtpStep('request')
                          setOtpCode('')
                          setError('')
                        }}
                        className="text-cyan-400 hover:text-cyan-300 underline font-medium"
                      >
                        Change email
                      </button>
                    </div>
                  </div>

                  <div>
                    <label htmlFor="otp-code" className="mb-1.5 block text-xs font-medium text-slate-300 text-center">
                      Enter 6-Digit Code
                    </label>
                    <input
                      id="otp-code"
                      type="text"
                      maxLength={6}
                      autoFocus
                      required
                      placeholder="••••••"
                      value={otpCode}
                      onChange={(e) => setOtpCode(e.target.value.replace(/\D/g, ''))}
                      className="w-full text-center tracking-[12px] font-mono text-2xl font-bold rounded-xl border border-slate-700 bg-slate-900/90 py-3 text-cyan-300 placeholder-slate-600 outline-none focus:border-cyan-400 transition"
                    />
                  </div>

                  {/* Resend Code Controls */}
                  <div className="flex items-center justify-between text-xs px-1">
                    <span className="text-slate-400">Didn't receive the email?</span>
                    <button
                      type="button"
                      onClick={() => handleSendOtp()}
                      disabled={loading || otpCooldown > 0}
                      className="text-cyan-400 hover:text-cyan-300 disabled:text-slate-500 font-medium flex items-center gap-1 transition"
                    >
                      <RefreshCw size={12} className={loading ? 'animate-spin' : ''} />
                      {otpCooldown > 0 ? `Resend in ${otpCooldown}s` : 'Resend Code'}
                    </button>
                  </div>

                  <button
                    type="submit"
                    disabled={loading || otpCode.length !== 6 || otpExpiresIn <= 0}
                    className="w-full rounded-xl bg-gradient-to-r from-cyan-400 to-blue-500 py-3 text-sm font-semibold text-slate-950 shadow-lg shadow-cyan-500/20 hover:from-cyan-300 hover:to-blue-400 transition disabled:opacity-60 flex items-center justify-center gap-2"
                  >
                    {loading ? (
                      <>
                        <div className="h-4 w-4 rounded-full border-2 border-slate-950 border-t-transparent animate-spin" />
                        <span>Verifying Code...</span>
                      </>
                    ) : (
                      <>
                        <ShieldCheck size={16} />
                        <span>Verify & Sign In</span>
                      </>
                    )}
                  </button>
                </form>
              )}
            </div>
          )}

          {/* 3. Email & Password Form */}
          {authMode === 'password' && (
            <form onSubmit={submitPasswordLogin} className="space-y-4">
              <div>
                <label htmlFor="email" className="mb-1.5 block text-xs font-medium text-slate-300">
                  Email Address
                </label>
                <div className="relative">
                  <input
                    id="email"
                    type="email"
                    required
                    placeholder="analyst@example.com"
                    className="w-full rounded-xl border border-slate-700 bg-slate-900/90 pl-10 pr-3 py-2.5 text-sm text-slate-100 placeholder-slate-500 outline-none focus:border-cyan-400 transition"
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                  />
                  <Mail size={16} className="absolute left-3.5 top-3 text-slate-500 pointer-events-none" />
                </div>
              </div>

              <div>
                <div className="flex items-center justify-between mb-1.5">
                  <label htmlFor="password" className="block text-xs font-medium text-slate-300">
                    Password
                  </label>
                  <button
                    type="button"
                    onClick={() => {
                      setForgotModalOpen(true)
                      setForgotEmail(email)
                      setForgotMessage('')
                      setForgotToken('')
                    }}
                    className="text-[11px] text-cyan-400 hover:text-cyan-300 transition"
                  >
                    Forgot password?
                  </button>
                </div>
                <div className="relative">
                  <input
                    id="password"
                    type={showPassword ? 'text' : 'password'}
                    required
                    placeholder="••••••••"
                    className="w-full rounded-xl border border-slate-700 bg-slate-900/90 pl-10 pr-10 py-2.5 text-sm text-slate-100 placeholder-slate-500 outline-none focus:border-cyan-400 transition"
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                  />
                  <Lock size={16} className="absolute left-3.5 top-3 text-slate-500 pointer-events-none" />
                  <button
                    type="button"
                    onClick={() => setShowPassword((prev) => !prev)}
                    className="absolute right-3.5 top-3 text-slate-500 hover:text-slate-300 transition"
                    aria-label={showPassword ? 'Hide password' : 'Show password'}
                  >
                    {showPassword ? <EyeOff size={16} /> : <Eye size={16} />}
                  </button>
                </div>
              </div>

              {/* Remember Me */}
              <div className="flex items-center justify-between pt-1">
                <label className="flex items-center gap-2 cursor-pointer select-none">
                  <input
                    type="checkbox"
                    checked={rememberMe}
                    onChange={(e) => setRememberMe(e.target.checked)}
                    className="h-4 w-4 rounded border-slate-700 bg-slate-900 text-cyan-400 focus:ring-cyan-400/20"
                  />
                  <span className="text-xs text-slate-300">Remember this session</span>
                </label>
              </div>

              {/* Submit Button */}
              <button
                type="submit"
                disabled={loading}
                className="w-full rounded-xl bg-gradient-to-r from-cyan-400 to-blue-500 py-3 text-sm font-semibold text-slate-950 shadow-lg shadow-cyan-500/20 hover:from-cyan-300 hover:to-blue-400 transition disabled:opacity-60 flex items-center justify-center gap-2"
              >
                {loading ? (
                  <>
                    <div className="h-4 w-4 rounded-full border-2 border-slate-950 border-t-transparent animate-spin" />
                    <span>Signing In...</span>
                  </>
                ) : (
                  <span>Sign In to Workspace</span>
                )}
              </button>
            </form>
          )}

          {/* Footer Link */}
          <div className="mt-6 text-center text-xs text-slate-400 border-t border-slate-800/80 pt-4">
            <span>Don't have an account yet? </span>
            <Link to="/register" className="font-semibold text-cyan-400 hover:text-cyan-300 transition">
              Create Account
            </Link>
          </div>
        </div>
      </div>

      {/* Forgot Password Modal */}
      {forgotModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 backdrop-blur-md p-4">
          <div className="glass w-full max-w-md rounded-3xl border border-slate-800 bg-slate-950 p-6 shadow-2xl relative">
            <button
              onClick={() => setForgotModalOpen(false)}
              className="absolute top-5 right-5 text-slate-400 hover:text-slate-200"
            >
              <X size={18} />
            </button>
            <div className="flex items-center gap-2.5 mb-3 text-cyan-300">
              <KeyRound size={20} />
              <h3 className="font-bold text-slate-100">Reset Your Password</h3>
            </div>
            <p className="text-xs text-slate-400 mb-4">
              Enter your registered email address. We will generate a secure single-use recovery link.
            </p>

            <form onSubmit={handleForgotPassword} className="space-y-4">
              <div>
                <label className="block text-xs font-medium text-slate-300 mb-1">Email</label>
                <input
                  type="email"
                  required
                  placeholder="analyst@example.com"
                  className="w-full rounded-xl border border-slate-700 bg-slate-900 px-3 py-2 text-sm text-slate-100 outline-none focus:border-cyan-400"
                  value={forgotEmail}
                  onChange={(e) => setForgotEmail(e.target.value)}
                />
              </div>

              {forgotMessage && (
                <div className="rounded-xl border border-cyan-500/30 bg-cyan-950/20 p-3 text-xs text-cyan-200">
                  <p>{forgotMessage}</p>
                  {forgotToken && (
                    <div className="mt-2 pt-2 border-t border-cyan-500/20">
                      <p className="text-[10px] text-slate-400">Local Recovery Link:</p>
                      <Link
                        to={`/reset-password?token=${forgotToken}`}
                        onClick={() => setForgotModalOpen(false)}
                        className="text-xs text-cyan-400 font-semibold underline break-all hover:text-cyan-300"
                      >
                        Click here to set new password →
                      </Link>
                    </div>
                  )}
                </div>
              )}

              <div className="flex justify-end gap-2 pt-2">
                <button
                  type="button"
                  onClick={() => setForgotModalOpen(false)}
                  className="rounded-xl border border-slate-800 px-4 py-2 text-xs text-slate-400 hover:bg-slate-900"
                >
                  Close
                </button>
                <button
                  type="submit"
                  disabled={forgotLoading}
                  className="rounded-xl bg-cyan-400 px-4 py-2 text-xs font-semibold text-slate-950 hover:bg-cyan-300 disabled:opacity-50"
                >
                  {forgotLoading ? 'Dispatching...' : 'Send Recovery Link'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Safe Account Linking Modal */}
      <AccountLinkingModal
        challenge={linkingChallenge}
        onClose={() => setLinkingChallenge(null)}
      />

      {/* Google OAuth Modal / Credentials Config */}
      <GoogleAuthModal
        isOpen={googleModalOpen}
        onClose={() => setGoogleModalOpen(false)}
        isConfigured={googleConfig?.configured}
        clientId={googleConfig?.client_id}
      />
    </div>
  )
}
