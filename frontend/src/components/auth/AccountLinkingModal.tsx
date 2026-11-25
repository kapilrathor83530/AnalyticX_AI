import { AlertCircle, CheckCircle2, KeyRound, Lock, Mail, ShieldCheck, X } from 'lucide-react'
import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useAuth } from '../../contexts/AuthContext'
import { authService } from '../../services/authService'
import type { GoogleLinkChallengeResponse } from '../../types/auth'

interface Props {
  challenge: GoogleLinkChallengeResponse | null
  onClose: () => void
}

export default function AccountLinkingModal({ challenge, onClose }: Props) {
  const { setUser } = useAuth()
  const navigate = useNavigate()

  const [activeTab, setActiveTab] = useState<'password' | 'otp'>(
    challenge?.has_password ? 'password' : 'otp'
  )
  const [password, setPassword] = useState('')
  const [otpCode, setOtpCode] = useState('')
  const [challengeId, setChallengeId] = useState('')
  const [otpSent, setOtpSent] = useState(false)
  const [otpCooldown, setOtpCooldown] = useState(0)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  if (!challenge) return null

  async function handleSendOtp() {
    if (!challenge) return
    setError(null)
    setLoading(true)
    try {
      const res = await authService.sendOtp(challenge.email, 'link')
      setChallengeId(res.challenge_id)
      setOtpSent(true)
      setOtpCooldown(res.cooldown)
      const timer = setInterval(() => {
        setOtpCooldown((prev) => {
          if (prev <= 1) {
            clearInterval(timer)
            return 0
          }
          return prev - 1
        })
      }, 1000)
    } catch (err: any) {
      setError(err?.response?.data?.detail || 'Failed to dispatch email verification code.')
    } finally {
      setLoading(false)
    }
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    if (!challenge) return
    setError(null)
    setLoading(true)

    try {
      const payload: {
        linking_token: string
        password?: string
        challenge_id?: string
        code?: string
      } = {
        linking_token: challenge.linking_token,
      }

      if (activeTab === 'password') {
        if (!password.trim()) {
          setError('Please enter your account password.')
          setLoading(false)
          return
        }
        payload.password = password
      } else {
        if (!challengeId || !otpCode.trim()) {
          setError('Please enter the 6-digit verification code sent to your email.')
          setLoading(false)
          return
        }
        payload.challenge_id = challengeId
        payload.code = otpCode.trim()
      }

      const res = await authService.confirmGoogleLink(payload)
      setUser(res.user)
      onClose()
      if (!res.user.onboarding_completed) {
        navigate('/onboarding')
      } else {
        navigate('/workspace')
      }
    } catch (err: any) {
      setError(err?.response?.data?.detail || 'Account linking verification failed.')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/80 backdrop-blur-md p-4">
      <div className="relative w-full max-w-md rounded-3xl border border-slate-800 bg-slate-950 p-6 shadow-2xl overflow-hidden">
        {/* Close Button */}
        <button
          onClick={onClose}
          className="absolute right-4 top-4 rounded-xl p-1.5 text-slate-400 hover:bg-slate-800 hover:text-slate-200 transition"
        >
          <X size={18} />
        </button>

        {/* Header */}
        <div className="flex items-center gap-3 border-b border-slate-800/80 pb-4 mb-5">
          <div className="flex h-11 w-11 items-center justify-center rounded-2xl bg-gradient-to-tr from-cyan-400 to-blue-500 text-slate-950 shadow-md">
            <ShieldCheck size={22} />
          </div>
          <div>
            <h3 className="text-base font-bold text-slate-100">Confirm Account Ownership</h3>
            <p className="text-xs text-slate-400">Safe Account Linking Policy</p>
          </div>
        </div>

        <p className="text-xs text-slate-300 mb-4 leading-relaxed">
          An Analyticx AI account already exists for <strong className="text-cyan-300">{challenge.masked_email}</strong>.
          To securely link your Google sign-in to this existing account and preserve all your data, please confirm your ownership:
        </p>

        {error && (
          <div className="mb-4 flex items-center gap-2 rounded-xl border border-rose-500/30 bg-rose-950/20 p-3 text-xs text-rose-300">
            <AlertCircle size={16} className="shrink-0" />
            <span>{error}</span>
          </div>
        )}

        {/* Tabs */}
        <div className="flex rounded-xl bg-slate-900 p-1 mb-4 border border-slate-800">
          {challenge.has_password && (
            <button
              type="button"
              onClick={() => {
                setActiveTab('password')
                setError(null)
              }}
              className={`flex-1 flex items-center justify-center gap-1.5 py-1.5 text-xs font-semibold rounded-lg transition ${
                activeTab === 'password'
                  ? 'bg-slate-800 text-cyan-300 shadow'
                  : 'text-slate-400 hover:text-slate-200'
              }`}
            >
              <KeyRound size={13} />
              <span>Use Password</span>
            </button>
          )}
          <button
            type="button"
            onClick={() => {
              setActiveTab('otp')
              setError(null)
            }}
            className={`flex-1 flex items-center justify-center gap-1.5 py-1.5 text-xs font-semibold rounded-lg transition ${
              activeTab === 'otp'
                ? 'bg-slate-800 text-cyan-300 shadow'
                : 'text-slate-400 hover:text-slate-200'
            }`}
          >
            <Mail size={13} />
            <span>Use Email OTP</span>
          </button>
        </div>

        <form onSubmit={handleSubmit} className="space-y-4">
          {activeTab === 'password' ? (
            <div>
              <label className="text-xs font-medium text-slate-300 block mb-1.5">
                Existing Account Password
              </label>
              <div className="relative">
                <Lock size={15} className="absolute left-3.5 top-3 text-slate-500" />
                <input
                  type="password"
                  required
                  placeholder="••••••••"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  className="w-full rounded-xl border border-slate-700 bg-slate-900 pl-10 pr-3 py-2.5 text-sm text-slate-100 placeholder-slate-500 focus:border-cyan-400 focus:outline-none"
                />
              </div>
            </div>
          ) : (
            <div className="space-y-3">
              {!otpSent ? (
                <div className="rounded-2xl border border-slate-800 bg-slate-900/60 p-4 text-center">
                  <p className="text-xs text-slate-300 mb-3">
                    We will send a single-use 6-digit code to <strong>{challenge.masked_email}</strong>.
                  </p>
                  <button
                    type="button"
                    onClick={handleSendOtp}
                    disabled={loading}
                    className="w-full rounded-xl bg-cyan-500 hover:bg-cyan-400 py-2.5 text-xs font-bold text-slate-950 transition"
                  >
                    {loading ? 'Sending Code...' : 'Send Verification Code'}
                  </button>
                </div>
              ) : (
                <div>
                  <div className="flex items-center justify-between mb-1.5">
                    <label className="text-xs font-medium text-slate-300">
                      Enter 6-Digit Code
                    </label>
                    <button
                      type="button"
                      onClick={handleSendOtp}
                      disabled={loading || otpCooldown > 0}
                      className="text-[11px] text-cyan-400 hover:text-cyan-300 disabled:opacity-50"
                    >
                      {otpCooldown > 0 ? `Resend in ${otpCooldown}s` : 'Resend Code'}
                    </button>
                  </div>
                  <input
                    type="text"
                    maxLength={6}
                    required
                    placeholder="123456"
                    value={otpCode}
                    onChange={(e) => setOtpCode(e.target.value.replace(/\D/g, ''))}
                    className="w-full text-center tracking-[8px] font-mono font-bold text-lg rounded-xl border border-slate-700 bg-slate-900 py-2.5 text-slate-100 focus:border-cyan-400 focus:outline-none"
                  />
                  <p className="text-[11px] text-emerald-400 flex items-center gap-1.5 mt-2">
                    <CheckCircle2 size={13} />
                    <span>Verification code sent to {challenge.masked_email}</span>
                  </p>
                </div>
              )}
            </div>
          )}

          {(activeTab === 'password' || otpSent) && (
            <button
              type="submit"
              disabled={loading}
              className="w-full rounded-xl bg-gradient-to-r from-cyan-400 to-blue-500 py-2.5 text-xs font-bold text-slate-950 hover:from-cyan-300 hover:to-blue-400 transition shadow-lg shadow-cyan-500/20 disabled:opacity-50"
            >
              {loading ? 'Confirming Ownership...' : 'Link Account & Proceed'}
            </button>
          )}
        </form>
      </div>
    </div>
  )
}
