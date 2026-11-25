import { useState } from 'react'
import { Link, useNavigate, useSearchParams } from 'react-router-dom'
import { ArrowLeft, Check, CheckCircle2, Eye, EyeOff, KeyRound, Lock, ShieldCheck, Sparkles } from 'lucide-react'
import { getErrorMessage } from '../api/client'
import { authService } from '../services/authService'

export default function ResetPasswordPage() {
  const [searchParams] = useSearchParams()
  const navigate = useNavigate()
  const initialToken = searchParams.get('token') || ''

  const [token, setToken] = useState(initialToken)
  const [newPassword, setNewPassword] = useState('')
  const [confirmPassword, setConfirmPassword] = useState('')
  const [showPassword, setShowPassword] = useState(false)
  const [error, setError] = useState('')
  const [success, setSuccess] = useState(false)
  const [loading, setLoading] = useState(false)

  const hasLength = newPassword.length >= 8
  const hasUpper = /[A-Z]/.test(newPassword)
  const hasLower = /[a-z]/.test(newPassword)
  const hasNumberOrSpecial = /[0-9!@#$%^&*(),.?":{}|<>]/.test(newPassword)
  const passwordsMatch = newPassword.length > 0 && newPassword === confirmPassword

  async function submit(e: React.FormEvent) {
    e.preventDefault()
    setError('')

    if (!token.trim()) {
      setError('Password reset token is missing. Please use the link sent to your email.')
      return
    }

    if (!hasLength) {
      setError('New password must be at least 8 characters long.')
      return
    }

    if (newPassword !== confirmPassword) {
      setError('Passwords do not match. Please verify your entries.')
      return
    }

    setLoading(true)
    try {
      await authService.confirmPasswordReset(token.trim(), newPassword)
      setSuccess(true)
    } catch (err) {
      setError(getErrorMessage(err))
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="min-h-[85vh] flex flex-col justify-center items-center px-4 py-12">
      <div className="w-full max-w-md">
        <Link
          to="/login"
          className="inline-flex items-center gap-1.5 text-xs text-slate-400 hover:text-cyan-300 transition mb-6"
        >
          <ArrowLeft size={14} />
          <span>Back to Sign In</span>
        </Link>

        <div className="glass rounded-3xl border border-slate-800 bg-slate-950/85 p-8 shadow-2xl backdrop-blur-2xl relative overflow-hidden">
          <div className="mb-6 text-center">
            <div className="inline-flex h-12 w-12 items-center justify-center rounded-2xl bg-gradient-to-tr from-cyan-400 to-blue-500 text-slate-950 mb-3 shadow-lg shadow-cyan-500/20">
              <KeyRound size={24} />
            </div>
            <h1 className="text-2xl font-bold tracking-tight text-slate-100">Set New Password</h1>
            <p className="mt-1 text-xs text-slate-400">
              Choose a secure password for your <span className="text-cyan-300 font-medium">Analyticx AI</span> account
            </p>
          </div>

          {success ? (
            <div className="space-y-4 text-center py-4">
              <div className="inline-flex h-12 w-12 items-center justify-center rounded-full bg-emerald-500/20 text-emerald-400 mb-1">
                <CheckCircle2 size={28} />
              </div>
              <h2 className="text-lg font-bold text-slate-100">Password Reset Successful!</h2>
              <p className="text-xs text-slate-300">
                Your password has been securely updated. You can now log into your workspace with your new credentials.
              </p>
              <div className="pt-2">
                <button
                  onClick={() => navigate('/login')}
                  className="w-full rounded-xl bg-cyan-400 py-2.5 text-xs font-semibold text-slate-950 hover:bg-cyan-300 transition"
                >
                  Proceed to Sign In
                </button>
              </div>
            </div>
          ) : (
            <>
              {error && (
                <div className="mb-4 rounded-xl border border-red-500/30 bg-red-500/10 px-4 py-3 text-xs text-red-300">
                  {error}
                </div>
              )}

              <form onSubmit={submit} className="space-y-4">
                {!initialToken && (
                  <div>
                    <label className="mb-1.5 block text-xs font-medium text-slate-300">
                      Reset Token <span className="text-red-400">*</span>
                    </label>
                    <input
                      type="text"
                      required
                      placeholder="Paste reset token here"
                      className="w-full rounded-xl border border-slate-700 bg-slate-900/90 px-3 py-2 text-xs text-slate-100 outline-none focus:border-cyan-400 font-mono"
                      value={token}
                      onChange={(e) => setToken(e.target.value)}
                    />
                  </div>
                )}

                <div>
                  <label className="mb-1.5 block text-xs font-medium text-slate-300">
                    New Password <span className="text-red-400">*</span>
                  </label>
                  <div className="relative">
                    <input
                      type={showPassword ? 'text' : 'password'}
                      required
                      placeholder="At least 8 characters"
                      className="w-full rounded-xl border border-slate-700 bg-slate-900/90 pl-10 pr-10 py-2.5 text-sm text-slate-100 outline-none focus:border-cyan-400"
                      value={newPassword}
                      onChange={(e) => setNewPassword(e.target.value)}
                    />
                    <Lock size={16} className="absolute left-3.5 top-3 text-slate-500 pointer-events-none" />
                    <button
                      type="button"
                      onClick={() => setShowPassword((p) => !p)}
                      className="absolute right-3.5 top-3 text-slate-500 hover:text-slate-300"
                    >
                      {showPassword ? <EyeOff size={16} /> : <Eye size={16} />}
                    </button>
                  </div>
                </div>

                <div>
                  <label className="mb-1.5 block text-xs font-medium text-slate-300">
                    Confirm New Password <span className="text-red-400">*</span>
                  </label>
                  <div className="relative">
                    <input
                      type={showPassword ? 'text' : 'password'}
                      required
                      placeholder="Re-enter new password"
                      className="w-full rounded-xl border border-slate-700 bg-slate-900/90 pl-10 pr-3 py-2.5 text-sm text-slate-100 outline-none focus:border-cyan-400"
                      value={confirmPassword}
                      onChange={(e) => setConfirmPassword(e.target.value)}
                    />
                    <ShieldCheck size={16} className="absolute left-3.5 top-3 text-slate-500 pointer-events-none" />
                  </div>
                </div>

                <button
                  type="submit"
                  disabled={loading}
                  className="w-full rounded-xl bg-gradient-to-r from-cyan-400 to-blue-500 py-3 text-sm font-semibold text-slate-950 hover:from-cyan-300 hover:to-blue-400 shadow-lg shadow-cyan-500/20 disabled:opacity-60 flex items-center justify-center gap-2"
                >
                  {loading ? 'Updating Password...' : 'Save New Password'}
                </button>
              </form>
            </>
          )}
        </div>
      </div>
    </div>
  )
}
