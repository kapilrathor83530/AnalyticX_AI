import { useEffect, useState } from 'react'
import { Link, useSearchParams } from 'react-router-dom'
import { ArrowLeft, CheckCircle2, ShieldAlert, Sparkles } from 'lucide-react'
import { getErrorMessage } from '../api/client'
import { authService } from '../services/authService'

export default function VerifyEmailPage() {
  const [searchParams] = useSearchParams()
  const token = searchParams.get('token') || ''

  const [loading, setLoading] = useState(true)
  const [success, setSuccess] = useState(false)
  const [message, setMessage] = useState('')

  useEffect(() => {
    if (!token) {
      setLoading(false)
      setMessage('Verification link is invalid or incomplete.')
      return
    }

    authService
      .verifyEmail(token)
      .then((res) => {
        setSuccess(true)
        setMessage(res.message || 'Your email address has been successfully verified.')
      })
      .catch((err) => {
        setSuccess(false)
        setMessage(getErrorMessage(err))
      })
      .finally(() => {
        setLoading(false)
      })
  }, [token])

  return (
    <div className="min-h-[85vh] flex flex-col justify-center items-center px-4 py-12">
      <div className="w-full max-w-md">
        <Link
          to="/workspace"
          className="inline-flex items-center gap-1.5 text-xs text-slate-400 hover:text-cyan-300 transition mb-6"
        >
          <ArrowLeft size={14} />
          <span>Back to Workspace</span>
        </Link>

        <div className="glass rounded-3xl border border-slate-800 bg-slate-950/85 p-8 shadow-2xl backdrop-blur-2xl text-center space-y-4">
          {loading ? (
            <div className="py-8 space-y-3">
              <div className="h-10 w-10 mx-auto rounded-full border-3 border-cyan-400 border-t-transparent animate-spin" />
              <p className="text-sm font-semibold text-slate-200">Verifying your email address...</p>
            </div>
          ) : success ? (
            <div className="space-y-4 py-4">
              <div className="inline-flex h-14 w-14 items-center justify-center rounded-2xl bg-emerald-500/20 text-emerald-400 mb-2">
                <CheckCircle2 size={32} />
              </div>
              <h2 className="text-2xl font-bold text-slate-100">Email Address Verified!</h2>
              <p className="text-xs text-slate-300">{message}</p>
              <div className="pt-2">
                <Link
                  to="/workspace"
                  className="inline-block w-full rounded-xl bg-cyan-400 py-2.5 text-xs font-semibold text-slate-950 hover:bg-cyan-300 transition"
                >
                  Enter Your Workspace →
                </Link>
              </div>
            </div>
          ) : (
            <div className="space-y-4 py-4">
              <div className="inline-flex h-14 w-14 items-center justify-center rounded-2xl bg-red-500/20 text-red-400 mb-2">
                <ShieldAlert size={32} />
              </div>
              <h2 className="text-2xl font-bold text-slate-100">Verification Failed</h2>
              <p className="text-xs text-slate-300">{message}</p>
              <div className="pt-2">
                <Link
                  to="/settings"
                  className="inline-block w-full rounded-xl border border-slate-700 bg-slate-900 py-2.5 text-xs font-medium text-slate-200 hover:border-cyan-400 transition"
                >
                  Go to Account Settings
                </Link>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
