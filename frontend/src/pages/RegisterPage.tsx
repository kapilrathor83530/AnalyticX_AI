import {
  ArrowLeft,
  ArrowRight,
  Check,
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
  User,
} from 'lucide-react'
import { useEffect, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { getErrorMessage } from '../api/client'
import AccountLinkingModal from '../components/auth/AccountLinkingModal'
import GoogleAuthModal from '../components/auth/GoogleAuthModal'
import { useAuth } from '../contexts/AuthContext'
import { authService } from '../services/authService'
import type { GoogleLinkChallengeResponse } from '../types/auth'

export default function RegisterPage() {
  const { register, loginWithOtp } = useAuth()
  const navigate = useNavigate()

  // Mode: 'password' or 'otp'
  const [signupMode, setSignupMode] = useState<'password' | 'otp'>('password')

  // Password fields
  const [fullName, setFullName] = useState('')
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [confirmPassword, setConfirmPassword] = useState('')
  const [showPassword, setShowPassword] = useState(false)
  const [agreeTerms, setAgreeTerms] = useState(true)

  // OTP Verification for Signup
  const [otpStep, setOtpStep] = useState<'form' | 'verify'>('form')
  const [otpChallengeId, setOtpChallengeId] = useState('')
  const [otpCode, setOtpCode] = useState('')
  const [maskedEmail, setMaskedEmail] = useState('')
  const [otpCooldown, setOtpCooldown] = useState(0)
  const [otpExpiresIn, setOtpExpiresIn] = useState(300)

  // Status & errors
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)
  const [googleModalOpen, setGoogleModalOpen] = useState(false)
  const [googleConfig, setGoogleConfig] = useState<{
    configured: boolean
    client_id?: string | null
    instructions: string
  } | null>(null)
  const [linkingChallenge, setLinkingChallenge] = useState<GoogleLinkChallengeResponse | null>(null)

  // Cooldown timer
  useEffect(() => {
    if (otpCooldown <= 0) return
    const timer = setInterval(() => {
      setOtpCooldown((prev) => (prev <= 1 ? 0 : prev - 1))
    }, 1000)
    return () => clearInterval(timer)
  }, [otpCooldown])

  // Expiration timer
  useEffect(() => {
    if (otpStep !== 'verify' || otpExpiresIn <= 0) return
    const timer = setInterval(() => {
      setOtpExpiresIn((prev) => (prev <= 1 ? 0 : prev - 1))
    }, 1000)
    return () => clearInterval(timer)
  }, [otpStep, otpExpiresIn])

  // Password Strength Calculations
  const hasLength = password.length >= 8
  const hasUpper = /[A-Z]/.test(password)
  const hasLower = /[a-z]/.test(password)
  const hasNumberOrSpecial = /[0-9!@#$%^&*(),.?":{}|<>]/.test(password)
  const criteriaCount = [hasLength, hasUpper, hasLower, hasNumberOrSpecial].filter(Boolean).length

  let strengthLabel = 'Very Weak'
  let strengthColor = 'bg-red-500'
  let strengthTextColor = 'text-red-400'
  let strengthPct = 'w-1/4'

  if (criteriaCount === 2) {
    strengthLabel = 'Fair'
    strengthColor = 'bg-amber-500'
    strengthTextColor = 'text-amber-400'
    strengthPct = 'w-2/4'
  } else if (criteriaCount === 3) {
    strengthLabel = 'Good'
    strengthColor = 'bg-blue-400'
    strengthTextColor = 'text-blue-300'
    strengthPct = 'w-3/4'
  } else if (criteriaCount === 4) {
    strengthLabel = 'Strong'
    strengthColor = 'bg-emerald-400'
    strengthTextColor = 'text-emerald-300'
    strengthPct = 'w-full'
  }

  const passwordsMatch = password.length > 0 && password === confirmPassword

  async function submitPasswordRegistration(event: React.FormEvent) {
    event.preventDefault()
    setError('')

    if (!hasLength) {
      setError('Password must be at least 8 characters long.')
      return
    }

    if (password !== confirmPassword) {
      setError('Passwords do not match. Please verify your entries.')
      return
    }

    if (!agreeTerms) {
      setError('Please acknowledge the Analyticx AI Terms of Service to continue.')
      return
    }

    setLoading(true)
    try {
      const res = await authService.signup({
        email: email.trim(),
        fullName: fullName.trim() || undefined,
        password,
      })
      setOtpChallengeId(res.challenge_id)
      setMaskedEmail(res.masked_email)
      setOtpCooldown(res.cooldown || 60)
      setOtpExpiresIn(res.expires_in || 300)
      setOtpStep('verify')
    } catch (err) {
      setError(getErrorMessage(err))
    } finally {
      setLoading(false)
    }
  }

  async function handleSendSignupOtp(e?: React.FormEvent) {
    if (e) e.preventDefault()
    if (!email.trim()) {
      setError('Please enter your email address.')
      return
    }
    if (!agreeTerms) {
      setError('Please acknowledge the Analyticx AI Terms of Service to continue.')
      return
    }
    setError('')
    setLoading(true)
    try {
      const res = await authService.signup({
        email: email.trim(),
        fullName: fullName.trim() || undefined,
        password: password || undefined,
      })
      setOtpChallengeId(res.challenge_id)
      setMaskedEmail(res.masked_email)
      setOtpCooldown(res.cooldown || 60)
      setOtpExpiresIn(res.expires_in || 300)
      setOtpStep('verify')
    } catch (err) {
      setError(getErrorMessage(err))
    } finally {
      setLoading(false)
    }
  }

  async function handleVerifySignupOtp(e: React.FormEvent) {
    e.preventDefault()
    if (!otpCode.trim() || otpCode.trim().length !== 6) {
      setError('Please enter the 6-digit verification code.')
      return
    }
    setError('')
    setLoading(true)
    try {
      await loginWithOtp(otpChallengeId, email.trim(), otpCode.trim(), fullName.trim() || undefined)
      navigate('/onboarding')
    } catch (err) {
      setError(getErrorMessage(err))
    } finally {
      setLoading(false)
    }
  }

  async function handleGoogleClick() {
    try {
      const cfg = await authService.getGoogleConfig()
      setGoogleConfig(cfg)
      if (cfg.configured && cfg.client_id) {
        window.location.href = `https://accounts.google.com/o/oauth2/v2/auth?client_id=${cfg.client_id}&response_type=code&scope=openid%20email%20profile&redirect_uri=${encodeURIComponent(
          window.location.origin + '/login'
        )}`
      } else {
        setGoogleModalOpen(true)
      }
    } catch {
      setGoogleModalOpen(true)
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

        {/* Card */}
        <div className="glass rounded-3xl border border-slate-800 bg-slate-950/85 p-8 shadow-2xl backdrop-blur-2xl relative overflow-hidden">
          {/* Subtle Ambient Glow */}
          <div className="absolute -top-24 -right-24 h-48 w-48 rounded-full bg-cyan-500/10 blur-3xl pointer-events-none" />
          <div className="absolute -bottom-24 -left-24 h-48 w-48 rounded-full bg-blue-500/10 blur-3xl pointer-events-none" />

          {/* Header */}
          <div className="mb-6 text-center">
            <div className="inline-flex h-12 w-12 items-center justify-center rounded-2xl bg-gradient-to-tr from-cyan-400 to-blue-500 text-slate-950 mb-3 shadow-lg shadow-cyan-500/20">
              <Sparkles size={24} />
            </div>
            <h1 className="text-2xl font-bold tracking-tight text-slate-100">Create Account</h1>
            <p className="mt-1 text-xs text-slate-400">
              Join <span className="text-cyan-300 font-medium">Analyticx AI</span> and get instant access to automated insights
            </p>
          </div>

          {/* Error Banner */}
          {error && (
            <div className="mb-4 rounded-xl border border-red-500/30 bg-red-500/10 px-4 py-3 text-xs text-red-300 flex items-start gap-2">
              <div className="h-1.5 w-1.5 rounded-full bg-red-400 mt-1 shrink-0" />
              <span>{error}</span>
            </div>
          )}

          {/* Verification Step: Show 6-Digit Email Code Input */}
          {otpStep === 'verify' ? (
            <form onSubmit={handleVerifySignupOtp} className="space-y-4">
              <div className="rounded-2xl border border-cyan-500/30 bg-cyan-950/30 p-4 text-center">
                <div className="inline-flex h-9 w-9 items-center justify-center rounded-xl bg-cyan-400/20 text-cyan-300 mb-2">
                  <Mail size={18} />
                </div>
                <h3 className="text-sm font-bold text-slate-100">Check Your Email</h3>
                <p className="text-xs text-slate-300 mt-1">
                  We sent a 6-digit verification code to <strong className="text-cyan-300">{maskedEmail}</strong>
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
                      setOtpStep('form')
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
                <label htmlFor="signup-otp-code" className="mb-1.5 block text-xs font-medium text-slate-300 text-center">
                  Enter 6-Digit Verification Code
                </label>
                <input
                  id="signup-otp-code"
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

              <div className="flex items-center justify-between text-xs px-1">
                <span className="text-slate-400">Didn't receive email?</span>
                <button
                  type="button"
                  onClick={() => handleSendSignupOtp()}
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
                    <span>Verifying Code & Activating...</span>
                  </>
                ) : (
                  <>
                    <CheckCircle2 size={16} />
                    <span>Confirm Code & Start Workspace</span>
                  </>
                )}
              </button>
            </form>
          ) : (
            <div>
              {/* Notice */}
              <div className="mb-4 rounded-xl border border-cyan-500/30 bg-cyan-950/25 px-3 py-2 text-xs text-cyan-300 flex items-center gap-2">
                <ShieldCheck size={16} className="text-cyan-400 shrink-0" />
                <span>Email verification required. A 6-digit code will be sent to your Gmail/Email.</span>
              </div>

              {/* Continue with Google Button */}
              <button
                type="button"
                onClick={handleGoogleClick}
                disabled={loading}
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
            <span className="group-hover:text-cyan-200 transition">Sign up with Google</span>
          </button>

          {/* Divider */}
          <div className="relative my-6 text-center">
            <div className="absolute inset-0 flex items-center">
              <div className="w-full border-t border-slate-800" />
            </div>
            <span className="relative bg-slate-950/90 px-3 text-[10px] text-slate-500 uppercase tracking-widest font-semibold">
              Or sign up with email
            </span>
          </div>

          {/* Signup Mode Tabs */}
          <div className="grid grid-cols-2 rounded-xl bg-slate-900/80 p-1 mb-5 border border-slate-800">
            <button
              type="button"
              onClick={() => {
                setSignupMode('password')
                setOtpStep('form')
                setError('')
              }}
              className={`flex items-center justify-center gap-1.5 py-2 text-xs font-semibold rounded-lg transition ${
                signupMode === 'password'
                  ? 'bg-slate-800 text-cyan-300 shadow-sm border border-slate-700/60'
                  : 'text-slate-400 hover:text-slate-200'
              }`}
            >
              <KeyRound size={13} />
              <span>Password Account</span>
            </button>
            <button
              type="button"
              onClick={() => {
                setSignupMode('otp')
                setOtpStep('form')
                setError('')
              }}
              className={`flex items-center justify-center gap-1.5 py-2 text-xs font-semibold rounded-lg transition ${
                signupMode === 'otp'
                  ? 'bg-slate-800 text-cyan-300 shadow-sm border border-slate-700/60'
                  : 'text-slate-400 hover:text-slate-200'
              }`}
            >
              <Mail size={13} />
              <span>Email Code (OTP)</span>
            </button>
          </div>

          {/* Form Content */}
          {signupMode === 'password' ? (
            <form onSubmit={submitPasswordRegistration} className="space-y-4">
              <div>
                <label htmlFor="full-name" className="mb-1.5 block text-xs font-medium text-slate-300">
                  Full Name
                </label>
                <div className="relative">
                  <input
                    id="full-name"
                    type="text"
                    placeholder="Full Name"
                    className="w-full rounded-xl border border-slate-700 bg-slate-900/90 pl-10 pr-3 py-2.5 text-sm text-slate-100 placeholder-slate-500 outline-none focus:border-cyan-400 transition"
                    value={fullName}
                    onChange={(e) => setFullName(e.target.value)}
                  />
                  <User size={16} className="absolute left-3.5 top-3 text-slate-500 pointer-events-none" />
                </div>
              </div>

              <div>
                <label htmlFor="email" className="mb-1.5 block text-xs font-medium text-slate-300">
                  Email Address <span className="text-red-400">*</span>
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
                <label htmlFor="password" className="mb-1.5 block text-xs font-medium text-slate-300">
                  Password <span className="text-red-400">*</span>
                </label>
                <div className="relative">
                  <input
                    id="password"
                    type={showPassword ? 'text' : 'password'}
                    required
                    placeholder="Minimum 8 characters"
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

                {/* Password Strength Meter */}
                <div className="mt-2 space-y-1.5">
                  {password.length > 0 && (
                    <>
                      <div className="flex items-center justify-between text-[11px]">
                        <span className="text-slate-400">Password Strength:</span>
                        <span className={`font-semibold ${strengthTextColor}`}>{strengthLabel}</span>
                      </div>
                      <div className="h-1.5 w-full rounded-full bg-slate-800 overflow-hidden">
                        <div className={`h-full ${strengthColor} ${strengthPct} transition-all duration-300`} />
                      </div>
                    </>
                  )}
                  <div className="grid grid-cols-2 gap-1 text-[10px] text-slate-400 pt-1">
                    <div className={`flex items-center gap-1 ${hasLength ? 'text-emerald-400' : 'text-slate-500'}`}>
                      <Check size={11} /> At least 8 characters
                    </div>
                    <div className={`flex items-center gap-1 ${hasUpper ? 'text-emerald-400' : 'text-slate-500'}`}>
                      <Check size={11} /> Uppercase letter
                    </div>
                    <div className={`flex items-center gap-1 ${hasLower ? 'text-emerald-400' : 'text-slate-500'}`}>
                      <Check size={11} /> Lowercase letter
                    </div>
                    <div className={`flex items-center gap-1 ${hasNumberOrSpecial ? 'text-emerald-400' : 'text-slate-500'}`}>
                      <Check size={11} /> Number or symbol
                    </div>
                  </div>
                </div>
              </div>

              <div>
                <label htmlFor="confirm-password" className="mb-1.5 block text-xs font-medium text-slate-300">
                  Confirm Password <span className="text-red-400">*</span>
                </label>
                <div className="relative">
                  <input
                    id="confirm-password"
                    type={showPassword ? 'text' : 'password'}
                    required
                    placeholder="Repeat your password"
                    className={`w-full rounded-xl border bg-slate-900/90 pl-10 pr-10 py-2.5 text-sm text-slate-100 placeholder-slate-500 outline-none transition ${
                      confirmPassword.length > 0
                        ? passwordsMatch
                          ? 'border-emerald-500 focus:border-emerald-400'
                          : 'border-red-500 focus:border-red-400'
                        : 'border-slate-700 focus:border-cyan-400'
                    }`}
                    value={confirmPassword}
                    onChange={(e) => setConfirmPassword(e.target.value)}
                  />
                  <ShieldCheck size={16} className="absolute left-3.5 top-3 text-slate-500 pointer-events-none" />
                </div>
              </div>

              {/* Terms */}
              <div className="pt-1">
                <label className="flex items-start gap-2 cursor-pointer select-none">
                  <input
                    type="checkbox"
                    checked={agreeTerms}
                    onChange={(e) => setAgreeTerms(e.target.checked)}
                    className="h-4 w-4 mt-0.5 rounded border-slate-700 bg-slate-900 text-cyan-400 focus:ring-cyan-400/20"
                  />
                  <span className="text-xs text-slate-300 leading-snug">
                    I agree to the <span className="text-cyan-400">Terms of Service</span> and acknowledge that my data will remain private and isolated.
                  </span>
                </label>
              </div>

              <button
                type="submit"
                disabled={loading}
                className="w-full rounded-xl bg-gradient-to-r from-cyan-400 to-blue-500 py-3 text-sm font-semibold text-slate-950 shadow-lg shadow-cyan-500/20 hover:from-cyan-300 hover:to-blue-400 transition disabled:opacity-60 flex items-center justify-center gap-2"
              >
                {loading ? (
                  <>
                    <div className="h-4 w-4 rounded-full border-2 border-slate-950 border-t-transparent animate-spin" />
                    <span>Sending Verification Code...</span>
                  </>
                ) : (
                  <>
                    <span>Verify Email & Create Account</span>
                    <ArrowRight size={15} />
                  </>
                )}
              </button>
            </form>
          ) : (
            /* Passwordless Email OTP Signup Flow */
            <form onSubmit={handleSendSignupOtp} className="space-y-4">
              <div>
                <label htmlFor="otp-full-name" className="mb-1.5 block text-xs font-medium text-slate-300">
                  Full Name
                </label>
                <div className="relative">
                  <input
                    id="otp-full-name"
                    type="text"
                    placeholder="Your full name"
                    className="w-full rounded-xl border border-slate-700 bg-slate-900/90 pl-10 pr-3 py-2.5 text-sm text-slate-100 placeholder-slate-500 outline-none focus:border-cyan-400 transition"
                    value={fullName}
                    onChange={(e) => setFullName(e.target.value)}
                  />
                  <User size={16} className="absolute left-3.5 top-3 text-slate-500 pointer-events-none" />
                </div>
              </div>

              <div>
                <label htmlFor="otp-signup-email" className="mb-1.5 block text-xs font-medium text-slate-300">
                  Email Address <span className="text-red-400">*</span>
                </label>
                <div className="relative">
                  <input
                    id="otp-signup-email"
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

              {/* Terms */}
              <div className="pt-1">
                <label className="flex items-start gap-2 cursor-pointer select-none">
                  <input
                    type="checkbox"
                    checked={agreeTerms}
                    onChange={(e) => setAgreeTerms(e.target.checked)}
                    className="h-4 w-4 mt-0.5 rounded border-slate-700 bg-slate-900 text-cyan-400 focus:ring-cyan-400/20"
                  />
                  <span className="text-xs text-slate-300 leading-snug">
                    I agree to the <span className="text-cyan-400">Terms of Service</span>.
                  </span>
                </label>
              </div>

              <button
                type="submit"
                disabled={loading || !email.trim()}
                className="w-full rounded-xl bg-gradient-to-r from-cyan-400 to-blue-500 py-3 text-sm font-semibold text-slate-950 shadow-lg shadow-cyan-500/20 hover:from-cyan-300 hover:to-blue-400 transition disabled:opacity-60 flex items-center justify-center gap-2"
              >
                {loading ? (
                  <>
                    <div className="h-4 w-4 rounded-full border-2 border-slate-950 border-t-transparent animate-spin" />
                    <span>Sending Verification Code...</span>
                  </>
                ) : (
                  <>
                    <span>Verify Email & Create Account</span>
                    <ArrowRight size={15} />
                  </>
                )}
              </button>
            </form>
          )}
        </div>
      )}

          {/* Footer Link */}
          <div className="mt-6 text-center text-xs text-slate-400 border-t border-slate-800/80 pt-4">
            <span>Already have an account? </span>
            <Link to="/login" className="font-semibold text-cyan-400 hover:text-cyan-300 transition">
              Sign In
            </Link>
          </div>
        </div>
      </div>

      {/* Account Linking Modal */}
      <AccountLinkingModal
        challenge={linkingChallenge}
        onClose={() => setLinkingChallenge(null)}
      />

      {/* Google OAuth Modal */}
      <GoogleAuthModal
        isOpen={googleModalOpen}
        onClose={() => setGoogleModalOpen(false)}
        isConfigured={googleConfig?.configured}
        clientId={googleConfig?.client_id}
      />
    </div>
  )
}
