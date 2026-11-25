import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import {
  AlertTriangle,
  Brain,
  CheckCircle2,
  Download,
  KeyRound,
  Languages,
  LogOut,
  Mail,
  Palette,
  RotateCcw,
  Shield,
  ShieldAlert,
  ShieldCheck,
  Sparkles,
  Trash2,
  User,
} from 'lucide-react'
import VerifyEmailModal from '../components/auth/VerifyEmailModal'
import { getErrorMessage } from '../api/client'
import { useAuth } from '../contexts/AuthContext'
import { authService } from '../services/authService'
import type { UserPreferences } from '../types/auth'

type SettingsTab = 'profile' | 'security' | 'preferences' | 'data'

export default function SettingsPage() {
  const { user, setUser, logout } = useAuth()
  const navigate = useNavigate()

  const [activeTab, setActiveTab] = useState<SettingsTab>('profile')
  const [message, setMessage] = useState('')
  const [errorMessage, setErrorMessage] = useState('')

  // Profile Form State
  const [fullName, setFullName] = useState(user?.full_name || '')
  const [role, setRole] = useState(user?.role || 'Data Analyst')
  const [experienceLevel, setExperienceLevel] = useState(user?.experience_level || 'Intermediate')
  const [profileSaving, setProfileSaving] = useState(false)
  const [resendingVerification, setResendingVerification] = useState(false)
  const [verifyModalOpen, setVerifyModalOpen] = useState(false)

  // Security Form State
  const [currentPassword, setCurrentPassword] = useState('')
  const [newPassword, setNewPassword] = useState('')
  const [confirmNewPassword, setConfirmNewPassword] = useState('')
  const [passwordSaving, setPasswordSaving] = useState(false)

  // Preferences State
  const userPrefs: UserPreferences = user?.preferences || {}
  const [theme, setTheme] = useState<'dark' | 'light'>(userPrefs.theme || 'dark')
  const [language, setLanguage] = useState(userPrefs.language || 'en')
  const [explanationLevel, setExplanationLevel] = useState<'executive' | 'standard' | 'technical'>(
    userPrefs.explanation_level || 'standard',
  )
  const [emailNotifications, setEmailNotifications] = useState(userPrefs.email_notifications ?? true)
  const [prefsSaving, setPrefsSaving] = useState(false)

  // Data & Privacy State
  const [deleteConfirmText, setDeleteConfirmText] = useState('')
  const [deleteModalOpen, setDeleteModalOpen] = useState(false)
  const [deleting, setDeleting] = useState(false)

  useEffect(() => {
    if (user) {
      setFullName(user.full_name || '')
      setRole(user.role || 'Data Analyst')
      setExperienceLevel(user.experience_level || 'Intermediate')
      setTheme(user.preferences?.theme || 'dark')
      setLanguage(user.preferences?.language || 'en')
      setExplanationLevel(user.preferences?.explanation_level || 'standard')
      setEmailNotifications(user.preferences?.email_notifications ?? true)
    }
  }, [user])

  function showBanner(msg: string, isError: boolean = false) {
    if (isError) {
      setErrorMessage(msg)
      setTimeout(() => setErrorMessage(''), 4000)
    } else {
      setMessage(msg)
      setTimeout(() => setMessage(''), 3000)
    }
  }

  async function handleProfileSave(e: React.FormEvent) {
    e.preventDefault()
    setProfileSaving(true)
    try {
      const updated = await authService.updateProfile({
        full_name: fullName.trim(),
        role,
        experience_level: experienceLevel,
      })
      setUser(updated)
      showBanner('Profile information successfully updated.')
    } catch (err) {
      showBanner(getErrorMessage(err), true)
    } finally {
      setProfileSaving(false)
    }
  }

  async function handleResendVerification() {
    if (!user?.email) return
    setResendingVerification(true)
    try {
      const res = await authService.resendVerification(user.email)
      showBanner(res.message || 'Verification link sent to your inbox.')
    } catch (err) {
      showBanner(getErrorMessage(err), true)
    } finally {
      setResendingVerification(false)
    }
  }

  async function handlePasswordChange(e: React.FormEvent) {
    e.preventDefault()
    if (newPassword.length < 8) {
      showBanner('New password must be at least 8 characters long.', true)
      return
    }
    if (newPassword !== confirmNewPassword) {
      showBanner('New passwords do not match.', true)
      return
    }
    setPasswordSaving(true)
    try {
      const res = await authService.changePassword(currentPassword, newPassword)
      showBanner(res.message || 'Password successfully updated.')
      setCurrentPassword('')
      setNewPassword('')
      setConfirmNewPassword('')
    } catch (err) {
      showBanner(getErrorMessage(err), true)
    } finally {
      setPasswordSaving(false)
    }
  }

  async function handlePreferencesSave(e: React.FormEvent) {
    e.preventDefault()
    setPrefsSaving(true)
    try {
      const updated = await authService.updatePreferences({
        theme,
        language,
        explanation_level: explanationLevel,
        email_notifications: emailNotifications,
      })
      setUser(updated)
      document.documentElement.classList.toggle('light', theme === 'light')
      showBanner('Workspace preferences saved.')
    } catch (err) {
      showBanner(getErrorMessage(err), true)
    } finally {
      setPrefsSaving(false)
    }
  }

  async function handleExportData() {
    try {
      await authService.exportUserData()
      showBanner('Account archive downloaded.')
    } catch (err) {
      showBanner(getErrorMessage(err), true)
    }
  }

  async function handleDeleteAccount() {
    if (deleteConfirmText.trim() !== 'DELETE') {
      showBanner("Type 'DELETE' to confirm account deletion.", true)
      return
    }
    setDeleting(true)
    try {
      await authService.deleteAccount('DELETE')
      logout()
      navigate('/login')
    } catch (err) {
      showBanner(getErrorMessage(err), true)
      setDeleting(false)
    }
  }

  const tabs = [
    { id: 'profile', label: 'User Profile', icon: User },
    { id: 'security', label: 'Security & Auth', icon: Shield },
    { id: 'preferences', label: 'Preferences', icon: Palette },
    { id: 'data', label: 'Data & Privacy', icon: Download },
  ]

  return (
    <div className="space-y-6 max-w-5xl mx-auto pb-12">
      {/* Header */}
      <div className="flex flex-wrap items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-slate-100">Account & Workspace Settings</h1>
          <p className="text-xs text-slate-400 mt-0.5">
            Manage your personal profile, security credentials, preferences, and private data.
          </p>
        </div>
        <button
          onClick={() => navigate('/onboarding')}
          className="inline-flex items-center gap-2 rounded-xl border border-slate-700 bg-slate-900/80 px-3.5 py-2 text-xs font-medium text-cyan-300 hover:border-cyan-400 transition"
        >
          <RotateCcw size={14} />
          <span>Restart Onboarding Wizard</span>
        </button>
      </div>

      {/* Notifications / Alerts */}
      {message && (
        <div className="rounded-xl border border-emerald-500/30 bg-emerald-500/10 px-4 py-3 text-xs text-emerald-300 flex items-center gap-2">
          <CheckCircle2 size={15} className="shrink-0 text-emerald-400" />
          <span>{message}</span>
        </div>
      )}
      {errorMessage && (
        <div className="rounded-xl border border-red-500/30 bg-red-500/10 px-4 py-3 text-xs text-red-300 flex items-center gap-2">
          <AlertTriangle size={15} className="shrink-0 text-red-400" />
          <span>{errorMessage}</span>
        </div>
      )}

      {/* Navigation Tabs */}
      <div className="flex border-b border-slate-800 space-x-1">
        {tabs.map((t) => {
          const Icon = t.icon
          const isActive = activeTab === t.id
          return (
            <button
              key={t.id}
              onClick={() => setActiveTab(t.id as SettingsTab)}
              className={`flex items-center gap-2 px-4 py-3 text-xs font-semibold border-b-2 transition -mb-px ${
                isActive
                  ? 'border-cyan-400 text-cyan-300'
                  : 'border-transparent text-slate-400 hover:text-slate-200'
              }`}
            >
              <Icon size={15} />
              <span>{t.label}</span>
            </button>
          )
        })}
      </div>

      {/* TAB 1: USER PROFILE */}
      {activeTab === 'profile' && (
        <div className="glass rounded-3xl border border-slate-800 bg-slate-950/70 p-6 space-y-6">
          <div className="flex items-center gap-4 pb-4 border-b border-slate-800/80">
            <div className="h-16 w-16 rounded-2xl bg-gradient-to-tr from-cyan-400 to-blue-500 text-slate-950 font-bold text-2xl flex items-center justify-center uppercase shadow-lg shadow-cyan-500/20">
              {user?.full_name ? user.full_name.charAt(0) : user?.email?.charAt(0) || 'U'}
            </div>
            <div>
              <h2 className="text-lg font-bold text-slate-100">{user?.full_name || 'Analyticx User'}</h2>
              <p className="text-xs text-slate-400">{user?.email}</p>
              <div className="flex items-center gap-2 mt-1.5">
                <span className="rounded-full bg-cyan-400/10 border border-cyan-400/30 px-2 py-0.5 text-[10px] font-semibold text-cyan-300">
                  {user?.role || 'Data Analyst'}
                </span>
                {user?.is_verified ? (
                  <span className="inline-flex items-center gap-1 rounded-full bg-emerald-500/10 border border-emerald-500/30 px-2 py-0.5 text-[10px] font-semibold text-emerald-400">
                    <CheckCircle2 size={10} /> Verified Account
                  </span>
                ) : (
                  <span className="inline-flex items-center gap-1 rounded-full bg-amber-500/10 border border-amber-500/30 px-2 py-0.5 text-[10px] font-semibold text-amber-400">
                    <ShieldAlert size={10} /> Unverified Email
                  </span>
                )}
              </div>
            </div>
          </div>

          <form onSubmit={handleProfileSave} className="space-y-4 max-w-xl">
            <div>
              <label className="block text-xs font-medium text-slate-300 mb-1.5">Full Name</label>
              <input
                type="text"
                placeholder="e.g. Kapil Sharma"
                value={fullName}
                onChange={(e) => setFullName(e.target.value)}
                className="w-full rounded-xl border border-slate-700 bg-slate-900 px-3.5 py-2.5 text-xs text-slate-100 outline-none focus:border-cyan-400 transition"
              />
            </div>

            <div>
              <label className="block text-xs font-medium text-slate-300 mb-1.5">Email Address</label>
              <div className="flex items-center gap-2">
                <input
                  type="email"
                  disabled
                  value={user?.email || ''}
                  className="flex-1 rounded-xl border border-slate-800 bg-slate-900/50 px-3.5 py-2.5 text-xs text-slate-400 cursor-not-allowed"
                />
                {!user?.is_verified && (
                  <button
                    type="button"
                    onClick={() => setVerifyModalOpen(true)}
                    className="rounded-xl border border-amber-500/40 bg-amber-500/10 px-3 py-2 text-xs font-semibold text-amber-300 hover:bg-amber-500/20 transition shrink-0 flex items-center gap-1.5 shadow-sm"
                  >
                    <ShieldCheck size={13} />
                    <span>Verify with OTP</span>
                  </button>
                )}
              </div>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <div>
                <label className="block text-xs font-medium text-slate-300 mb-1.5">Primary Role</label>
                <select
                  value={role}
                  onChange={(e) => setRole(e.target.value)}
                  className="w-full rounded-xl border border-slate-700 bg-slate-900 px-3 py-2.5 text-xs text-slate-100 outline-none focus:border-cyan-400"
                >
                  <option value="Data Analyst">Data Analyst</option>
                  <option value="Data Scientist / ML Engineer">Data Scientist / ML Engineer</option>
                  <option value="Business Owner / Manager">Business Owner / Manager</option>
                  <option value="Student / Learner">Student / Learner</option>
                  <option value="Other">Other</option>
                </select>
              </div>

              <div>
                <label className="block text-xs font-medium text-slate-300 mb-1.5">Experience Level</label>
                <select
                  value={experienceLevel}
                  onChange={(e) => setExperienceLevel(e.target.value)}
                  className="w-full rounded-xl border border-slate-700 bg-slate-900 px-3 py-2.5 text-xs text-slate-100 outline-none focus:border-cyan-400"
                >
                  <option value="Beginner">Beginner</option>
                  <option value="Intermediate">Intermediate</option>
                  <option value="Advanced">Advanced</option>
                </select>
              </div>
            </div>

            <div className="pt-2">
              <button
                type="submit"
                disabled={profileSaving}
                className="rounded-xl bg-cyan-400 px-5 py-2.5 text-xs font-semibold text-slate-950 hover:bg-cyan-300 transition disabled:opacity-50"
              >
                {profileSaving ? 'Saving Changes...' : 'Save Profile Changes'}
              </button>
            </div>
          </form>
        </div>
      )}

      {/* TAB 2: SECURITY & AUTH */}
      {activeTab === 'security' && (
        <div className="glass rounded-3xl border border-slate-800 bg-slate-950/70 p-6 space-y-6">
          <div>
            <h2 className="text-base font-bold text-slate-100">Change Account Password</h2>
            <p className="text-xs text-slate-400 mt-0.5">
              Securely update your password. All other active sessions will remain protected.
            </p>
          </div>

          <form onSubmit={handlePasswordChange} className="space-y-4 max-w-xl">
            <div>
              <label className="block text-xs font-medium text-slate-300 mb-1.5">Current Password</label>
              <input
                type="password"
                required
                placeholder="••••••••"
                value={currentPassword}
                onChange={(e) => setCurrentPassword(e.target.value)}
                className="w-full rounded-xl border border-slate-700 bg-slate-900 px-3.5 py-2.5 text-xs text-slate-100 outline-none focus:border-cyan-400"
              />
            </div>

            <div>
              <label className="block text-xs font-medium text-slate-300 mb-1.5">New Password (8+ chars)</label>
              <input
                type="password"
                required
                placeholder="••••••••"
                value={newPassword}
                onChange={(e) => setNewPassword(e.target.value)}
                className="w-full rounded-xl border border-slate-700 bg-slate-900 px-3.5 py-2.5 text-xs text-slate-100 outline-none focus:border-cyan-400"
              />
            </div>

            <div>
              <label className="block text-xs font-medium text-slate-300 mb-1.5">Confirm New Password</label>
              <input
                type="password"
                required
                placeholder="••••••••"
                value={confirmNewPassword}
                onChange={(e) => setConfirmNewPassword(e.target.value)}
                className="w-full rounded-xl border border-slate-700 bg-slate-900 px-3.5 py-2.5 text-xs text-slate-100 outline-none focus:border-cyan-400"
              />
            </div>

            <div className="pt-2">
              <button
                type="submit"
                disabled={passwordSaving}
                className="rounded-xl bg-cyan-400 px-5 py-2.5 text-xs font-semibold text-slate-950 hover:bg-cyan-300 transition disabled:opacity-50"
              >
                {passwordSaving ? 'Updating Password...' : 'Update Password'}
              </button>
            </div>
          </form>

          {/* Session Overview */}
          <div className="pt-6 border-t border-slate-800 space-y-3">
            <h3 className="text-sm font-semibold text-slate-200">Active Authentication Session</h3>
            <div className="rounded-2xl border border-slate-800 bg-slate-900/50 p-4 flex items-center justify-between">
              <div>
                <p className="text-xs font-medium text-slate-100">Current Web Session (Bearer JWT)</p>
                <p className="text-[11px] text-slate-400">
                  Last login recorded: {user?.last_login_at ? new Date(user.last_login_at).toLocaleString() : 'Recent'}
                </p>
              </div>
              <button
                onClick={() => {
                  logout()
                  navigate('/login')
                }}
                className="inline-flex items-center gap-1.5 rounded-xl border border-red-500/30 bg-red-500/10 px-3 py-1.5 text-xs font-semibold text-red-300 hover:bg-red-500/20 transition"
              >
                <LogOut size={13} />
                <span>Sign Out</span>
              </button>
            </div>
          </div>
        </div>
      )}

      {/* TAB 3: WORKSPACE PREFERENCES */}
      {activeTab === 'preferences' && (
        <div className="glass rounded-3xl border border-slate-800 bg-slate-950/70 p-6 space-y-6">
          <div>
            <h2 className="text-base font-bold text-slate-100">Personalized Workspace Preferences</h2>
            <p className="text-xs text-slate-400 mt-0.5">
              Customize visual themes, natural language responses, and AI explanation depth.
            </p>
          </div>

          <form onSubmit={handlePreferencesSave} className="space-y-6 max-w-xl">
            {/* Theme */}
            <div className="space-y-2">
              <label className="block text-xs font-semibold text-slate-300">Theme Appearance</label>
              <div className="grid grid-cols-2 gap-3">
                <button
                  type="button"
                  onClick={() => setTheme('dark')}
                  className={`rounded-2xl border p-4 text-left transition ${
                    theme === 'dark' ? 'border-cyan-400 bg-cyan-950/30 text-slate-100' : 'border-slate-800 bg-slate-900/40 text-slate-400'
                  }`}
                >
                  <div className="font-semibold text-xs text-slate-200">Obsidian Dark</div>
                  <div className="text-[10px] text-slate-400 mt-0.5">High-contrast dark mode for data work</div>
                </button>
                <button
                  type="button"
                  onClick={() => setTheme('light')}
                  className={`rounded-2xl border p-4 text-left transition ${
                    theme === 'light' ? 'border-cyan-400 bg-cyan-950/30 text-slate-100' : 'border-slate-800 bg-slate-900/40 text-slate-400'
                  }`}
                >
                  <div className="font-semibold text-xs text-slate-200">Daylight Light</div>
                  <div className="text-[10px] text-slate-400 mt-0.5">Clean light palette</div>
                </button>
              </div>
            </div>

            {/* Language */}
            <div className="space-y-2">
              <label className="block text-xs font-semibold text-slate-300">Default Response Language</label>
              <select
                value={language}
                onChange={(e) => setLanguage(e.target.value)}
                className="w-full rounded-xl border border-slate-700 bg-slate-900 px-3.5 py-2.5 text-xs text-slate-100 outline-none focus:border-cyan-400"
              >
                <option value="en">English (Universal)</option>
                <option value="es">Español (Spanish)</option>
                <option value="fr">Français (French)</option>
                <option value="de">Deutsch (German)</option>
                <option value="zh">中文 (Chinese)</option>
                <option value="hi">हिंदी (Hindi)</option>
                <option value="pa">ਪੰਜਾਬੀ (Punjabi)</option>
              </select>
            </div>

            {/* AI Explanation Depth */}
            <div className="space-y-2">
              <label className="block text-xs font-semibold text-slate-300">AI Copilot Explanation Depth</label>
              <div className="space-y-2">
                {[
                  { id: 'executive', title: 'Executive Summary', desc: 'Bottom-line business impact, ROI, key findings in bullet points.' },
                  { id: 'standard', title: 'Standard Business Intelligence', desc: 'Balanced commercial analysis, metrics, charts, and recommendations.' },
                  { id: 'technical', title: 'Technical & Statistical', desc: 'Detailed distributions, p-values, hypothesis tests, and formula breakdowns.' },
                ].map((lvl) => (
                  <div
                    key={lvl.id}
                    onClick={() => setExplanationLevel(lvl.id as any)}
                    className={`cursor-pointer rounded-2xl border p-3.5 transition flex items-center justify-between ${
                      explanationLevel === lvl.id
                        ? 'border-cyan-400 bg-cyan-950/30 text-slate-100'
                        : 'border-slate-800 bg-slate-900/40 text-slate-400 hover:border-slate-700'
                    }`}
                  >
                    <div>
                      <p className="text-xs font-semibold text-slate-200">{lvl.title}</p>
                      <p className="text-[11px] text-slate-400">{lvl.desc}</p>
                    </div>
                    {explanationLevel === lvl.id && <CheckCircle2 size={16} className="text-cyan-400 shrink-0" />}
                  </div>
                ))}
              </div>
            </div>

            {/* Notification Toggles */}
            <div className="pt-2">
              <label className="flex items-center gap-2 cursor-pointer select-none">
                <input
                  type="checkbox"
                  checked={emailNotifications}
                  onChange={(e) => setEmailNotifications(e.target.checked)}
                  className="h-4 w-4 rounded border-slate-700 bg-slate-900 text-cyan-400"
                />
                <span className="text-xs text-slate-300">Enable in-app analysis and forecasting event alerts</span>
              </label>
            </div>

            <div className="pt-2">
              <button
                type="submit"
                disabled={prefsSaving}
                className="rounded-xl bg-cyan-400 px-5 py-2.5 text-xs font-semibold text-slate-950 hover:bg-cyan-300 transition disabled:opacity-50"
              >
                {prefsSaving ? 'Saving Preferences...' : 'Save Preferences'}
              </button>
            </div>
          </form>
        </div>
      )}

      {/* TAB 4: DATA & PRIVACY */}
      {activeTab === 'data' && (
        <div className="glass rounded-3xl border border-slate-800 bg-slate-950/70 p-6 space-y-6">
          <div>
            <h2 className="text-base font-bold text-slate-100">Personal Data & Workspace Portability</h2>
            <p className="text-xs text-slate-400 mt-0.5">
              Download your complete personal records or permanently delete your account and private assets.
            </p>
          </div>

          {/* Export Personal Data */}
          <div className="rounded-2xl border border-slate-800 bg-slate-900/50 p-5 flex flex-wrap items-center justify-between gap-4">
            <div>
              <h3 className="text-xs font-bold text-slate-200">Export All Account Data</h3>
              <p className="text-[11px] text-slate-400 mt-0.5">
                Download a machine-readable JSON archive of your user profile, dataset metadata, dashboards, and activity log.
              </p>
            </div>
            <button
              onClick={handleExportData}
              className="inline-flex items-center gap-2 rounded-xl bg-cyan-400 px-4 py-2 text-xs font-semibold text-slate-950 hover:bg-cyan-300 transition"
            >
              <Download size={14} />
              <span>Download Archive</span>
            </button>
          </div>

          {/* Account Deletion */}
          <div className="rounded-2xl border border-red-500/20 bg-red-950/10 p-5 space-y-3">
            <div className="flex items-center gap-2 text-red-400 font-bold text-xs uppercase tracking-wider">
              <AlertTriangle size={15} />
              <span>Danger Zone: Permanent Account Deletion</span>
            </div>
            <p className="text-xs text-slate-300 leading-relaxed">
              Deleting your account will permanently purge your owned datasets, saved dashboards, reports, and activity history. This action is irreversible.
            </p>
            <div>
              <button
                onClick={() => setDeleteModalOpen(true)}
                className="inline-flex items-center gap-2 rounded-xl bg-red-500/20 border border-red-500/40 px-4 py-2 text-xs font-semibold text-red-300 hover:bg-red-500/30 transition"
              >
                <Trash2 size={14} />
                <span>Delete Account & Data</span>
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Delete Confirmation Modal */}
      {deleteModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/80 backdrop-blur-md p-4">
          <div className="glass w-full max-w-md rounded-3xl border border-red-500/40 bg-slate-950 p-6 shadow-2xl space-y-4">
            <div className="flex items-center gap-2 text-red-400">
              <AlertTriangle size={20} />
              <h3 className="font-bold text-slate-100">Confirm Account Deletion</h3>
            </div>
            <p className="text-xs text-slate-300 leading-relaxed">
              To confirm that you wish to permanently delete your Analyticx AI account (<span className="text-cyan-300">{user?.email}</span>), please type <span className="font-bold text-red-400">DELETE</span> below:
            </p>

            <input
              type="text"
              placeholder="DELETE"
              value={deleteConfirmText}
              onChange={(e) => setDeleteConfirmText(e.target.value)}
              className="w-full rounded-xl border border-red-500/40 bg-slate-900 px-3 py-2 text-sm text-slate-100 outline-none focus:border-red-400 font-mono"
            />

            <div className="flex justify-end gap-2 pt-2">
              <button
                type="button"
                onClick={() => {
                  setDeleteModalOpen(false)
                  setDeleteConfirmText('')
                }}
                className="rounded-xl border border-slate-800 px-4 py-2 text-xs text-slate-400 hover:bg-slate-900"
              >
                Cancel
              </button>
              <button
                type="button"
                onClick={handleDeleteAccount}
                disabled={deleteConfirmText !== 'DELETE' || deleting}
                className="rounded-xl bg-red-500 px-4 py-2 text-xs font-semibold text-white hover:bg-red-600 disabled:opacity-40"
              >
                {deleting ? 'Purging Account...' : 'Permanently Delete'}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Verify Email Modal */}
      <VerifyEmailModal
        isOpen={verifyModalOpen}
        onClose={() => setVerifyModalOpen(false)}
      />
    </div>
  )
}
