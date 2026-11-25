import { CheckCircle2, Clock, Mail, RefreshCw, ShieldCheck, X } from 'lucide-react'
import { useEffect, useState } from 'react'
import { getErrorMessage } from '../../api/client'
import { useAuth } from '../../contexts/AuthContext'
import { authService } from '../../services/authService'

interface VerifyEmailModalProps {
  isOpen: boolean
  onClose: () => void
}

export default function VerifyEmailModal({ isOpen, onClose }: VerifyEmailModalProps) {
  const { user, refresh } = useAuth()
  const [code, setCode] = useState('')
  const [challengeId, setChallengeId] = useState('')
  const [maskedEmail, setMaskedEmail] = useState('')
  const [cooldown, setCooldown] = useState(0)
  const [expiresIn, setExpiresIn] = useState(300)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [success, setSuccess] = useState('')

  // Cooldown timer
  useEffect(() => {
    if (cooldown <= 0) return
    const timer = setInterval(() => {
      setCooldown((prev) => (prev <= 1 ? 0 : prev - 1))
    }, 1000)
    return () => clearInterval(timer)
  }, [cooldown])

  // Expiration timer
  useEffect(() => {
    if (!isOpen || expiresIn <= 0) return
    const timer = setInterval(() => {
      setExpiresIn((prev) => (prev <= 1 ? 0 : prev - 1))
    }, 1000)
    return () => clearInterval(timer)
  }, [isOpen, expiresIn])

  // Automatically request OTP code when modal is opened
  useEffect(() => {
    if (isOpen && user?.email && !challengeId) {
      handleRequestCode()
    }
  }, [isOpen, user?.email])

  async function handleRequestCode() {
    if (!user?.email) return
    setError('')
    setSuccess('')
    setLoading(true)
    try {
      const res = await authService.sendOtp(user.email, 'verify')
      setChallengeId(res.challenge_id)
      setMaskedEmail(res.masked_email)
      setCooldown(res.cooldown || 60)
      setExpiresIn(res.expires_in || 300)
      setSuccess(`A 6-digit verification code was sent to ${res.masked_email}`)
    } catch (err) {
      setError(getErrorMessage(err))
    } finally {
      setLoading(false)
    }
  }

  async function handleVerify(e: React.FormEvent) {
    e.preventDefault()
    if (!user?.email || code.trim().length !== 6) {
      setError('Please enter the 6-digit code received in your email.')
      return
    }

    setError('')
    setLoading(true)
    try {
      await authService.verifyOtp(challengeId, user.email, code.trim())
      await refresh()
      setSuccess('Your email address has been verified successfully!')
      setTimeout(() => {
        onClose()
      }, 1500)
    } catch (err) {
      setError(getErrorMessage(err))
    } finally {
      setLoading(false)
    }
  }

  if (!isOpen || !user) return null

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-950/80 backdrop-blur-md animate-in fade-in duration-200">
      <div className="relative w-full max-w-md rounded-3xl border border-slate-800 bg-slate-900 p-6 shadow-2xl overflow-hidden">
        {/* Glow */}
        <div className="absolute -top-12 -right-12 h-32 w-32 rounded-full bg-cyan-500/15 blur-2xl pointer-events-none" />

        {/* Close Button */}
        <button
          onClick={onClose}
          className="absolute right-4 top-4 rounded-xl p-1 text-slate-400 hover:text-slate-100 hover:bg-slate-800 transition"
        >
          <X size={18} />
        </button>

        {/* Header */}
        <div className="flex items-center gap-3 mb-5">
          <div className="flex h-11 w-11 items-center justify-center rounded-2xl bg-gradient-to-tr from-cyan-400 to-blue-500 text-slate-950 shadow-lg shadow-cyan-500/20">
            <Mail size={20} />
          </div>
          <div>
            <h3 className="text-base font-bold text-slate-100">Verify Your Email Address</h3>
            <p className="text-xs text-slate-400">Confirm your account ownership</p>
          </div>
        </div>

        {/* Status / Alerts */}
        {error && (
          <div className="mb-4 rounded-xl border border-red-500/30 bg-red-500/10 px-3.5 py-2.5 text-xs text-red-300">
            {error}
          </div>
        )}

        {success && (
          <div className="mb-4 rounded-xl border border-emerald-500/30 bg-emerald-500/10 px-3.5 py-2.5 text-xs text-emerald-300 flex items-center gap-2">
            <CheckCircle2 size={14} className="shrink-0 text-emerald-400" />
            <span>{success}</span>
          </div>
        )}

        <form onSubmit={handleVerify} className="space-y-4">
          <div className="rounded-2xl border border-cyan-500/30 bg-cyan-950/20 p-3.5 text-center">
            <p className="text-xs text-slate-200">
              We dispatched a verification code to <strong className="text-cyan-300">{maskedEmail || user.email}</strong>
            </p>
            <div className="flex items-center justify-center gap-1.5 mt-2 text-[11px] text-slate-400">
              <Clock size={12} className="text-cyan-400" />
              <span>
                Code expires in {Math.floor(expiresIn / 60)}:
                {(expiresIn % 60).toString().padStart(2, '0')}
              </span>
            </div>
          </div>

          <div>
            <label htmlFor="verify-modal-otp" className="mb-1.5 block text-xs font-medium text-slate-300 text-center">
              Enter 6-Digit Code
            </label>
            <input
              id="verify-modal-otp"
              type="text"
              maxLength={6}
              autoFocus
              required
              placeholder="••••••"
              value={code}
              onChange={(e) => setCode(e.target.value.replace(/\D/g, ''))}
              className="w-full text-center tracking-[12px] font-mono text-2xl font-bold rounded-xl border border-slate-700 bg-slate-950 py-3 text-cyan-300 placeholder-slate-600 outline-none focus:border-cyan-400 transition"
            />
          </div>

          <div className="flex items-center justify-between text-xs px-1">
            <span className="text-slate-400">Didn't receive email?</span>
            <button
              type="button"
              onClick={handleRequestCode}
              disabled={loading || cooldown > 0}
              className="text-cyan-400 hover:text-cyan-300 disabled:text-slate-500 font-medium flex items-center gap-1 transition"
            >
              <RefreshCw size={12} className={loading ? 'animate-spin' : ''} />
              {cooldown > 0 ? `Resend in ${cooldown}s` : 'Resend Code'}
            </button>
          </div>

          <button
            type="submit"
            disabled={loading || code.length !== 6 || expiresIn <= 0}
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
                <span>Verify & Activate Account</span>
              </>
            )}
          </button>
        </form>
      </div>
    </div>
  )
}
