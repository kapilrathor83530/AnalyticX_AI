import {
  Activity,
  Archive,
  BarChart3,
  Bell,
  Brain,
  CheckCheck,
  Code2,
  Database,
  FileCheck,
  FileText,
  HeartPulse,
  LayoutDashboard,
  Lightbulb,
  LineChart,
  LogIn,
  LogOut,
  Mail,
  Menu,
  Presentation,
  Settings,
  ShieldCheck,
  Sparkles,
  TrendingDown,
  TrendingUp,
  UploadCloud,
  User,
  UserPlus,
  Wand2,
} from 'lucide-react'
import { useCallback, useEffect, useState } from 'react'
import { NavLink, Outlet, useNavigate } from 'react-router-dom'
import VerifyEmailModal from './auth/VerifyEmailModal'
import { useAuth } from '../contexts/AuthContext'
import { AppMode, MODES, useAppMode } from '../contexts/ModeContext'
import UniversalCopilotModal from '../copilot/UniversalCopilotModal'
import { authService } from '../services/authService'
import type { NotificationItem } from '../types/auth'

const navItems = [
  { to: '/workspace', label: 'Upload Center', icon: UploadCloud },
  { to: '/datasets/1', label: 'Data Explorer', icon: Database },
  { to: '/analytics/1', label: 'Analytics', icon: BarChart3 },
  { to: '/studio/1', label: 'Visual Studio', icon: LineChart },
  { to: '/insights/1', label: 'Project Insights', icon: Lightbulb },
  { to: '/forecasting/1', label: 'Forecasting Lab', icon: TrendingUp },
  { to: '/data-prep/1', label: 'AI Prep Studio', icon: Wand2 },
  { to: '/dashboards', label: 'Saved Dashboards', icon: LayoutDashboard },
  { to: '/reports', label: 'Report Center', icon: Archive },
  { to: '/models', label: 'Model Management', icon: Brain },
  { to: '/settings', label: 'Account Settings', icon: Settings },
  { to: '/health', label: 'System Health', icon: HeartPulse },
]

export default function Layout() {
  const { user, isAuthenticated, logout } = useAuth()
  const { mode, setMode, config } = useAppMode()
  const navigate = useNavigate()

  const [notifications, setNotifications] = useState<NotificationItem[]>([])
  const [unreadCount, setUnreadCount] = useState<number>(0)
  const [notifsOpen, setNotifsOpen] = useState(false)
  const [verifyModalOpen, setVerifyModalOpen] = useState(false)

  const loadNotifications = useCallback(async () => {
    if (!isAuthenticated) return
    try {
      const data = await authService.getNotifications()
      setNotifications(data.items)
      setUnreadCount(data.unread_count)
    } catch {
      // non-blocking
    }
  }, [isAuthenticated])

  useEffect(() => {
    loadNotifications()
    const interval = setInterval(loadNotifications, 30000)
    return () => clearInterval(interval)
  }, [loadNotifications])

  const [sidebarOpen, setSidebarOpen] = useState<boolean>(() => {
    try {
      const saved = localStorage.getItem('analyticx_sidebar_open')
      return saved !== null ? JSON.parse(saved) : true
    } catch {
      return true
    }
  })

  const [copilotOpen, setCopilotOpen] = useState(false)

  function toggleSidebar() {
    setSidebarOpen((prev) => {
      const next = !prev
      try {
        localStorage.setItem('analyticx_sidebar_open', JSON.stringify(next))
      } catch {
        // ignore
      }
      return next
    })
  }

  // Trigger window resize event on transition so grid layouts and charts reflow smoothly
  useEffect(() => {
    window.dispatchEvent(new Event('resize'))
    const t1 = setTimeout(() => window.dispatchEvent(new Event('resize')), 100)
    const t2 = setTimeout(() => window.dispatchEvent(new Event('resize')), 320)
    return () => {
      clearTimeout(t1)
      clearTimeout(t2)
    }
  }, [sidebarOpen])

  return (
    <div className="min-h-screen text-slate-100 relative">
      {/* Mobile backdrop overlay */}
      {sidebarOpen && (
        <div
          onClick={() => toggleSidebar()}
          className="fixed inset-0 z-30 bg-black/60 backdrop-blur-sm lg:hidden transition-opacity"
        />
      )}

      {/* Collapsible Left Sidebar */}
      <aside
        className={`fixed left-0 top-0 z-40 h-screen w-72 border-r border-slate-800/80 bg-slate-950/95 p-6 backdrop-blur-xl transition-transform duration-300 ease-in-out flex flex-col justify-between overflow-y-auto ${
          sidebarOpen ? 'translate-x-0' : '-translate-x-full'
        }`}
      >
        <div className="space-y-6">
          <div className="flex items-center justify-between">
            <NavLink to="/" className="flex items-center gap-3 group">
              <div className="rounded-2xl bg-cyan-400/10 p-2.5 text-cyan-300 group-hover:scale-105 transition-transform">
                <Activity size={22} />
              </div>
              <div>
                <h1 className="text-xl font-bold tracking-tight text-slate-100">Analyticx AI</h1>
                <p className="text-[11px] text-slate-400">Business Intelligence</p>
              </div>
            </NavLink>
            <button
              onClick={toggleSidebar}
              className="flex items-center justify-center rounded-xl border border-slate-800 bg-slate-900/80 p-2 text-slate-400 hover:border-cyan-400 hover:bg-slate-800 hover:text-cyan-300 transition"
              title="Hide options menu"
            >
              <Menu size={18} />
            </button>
          </div>

          {/* Sidebar Active Mode Badge & Goal Card */}
          <div className={`rounded-2xl border p-3.5 space-y-2.5 transition-all ${config.badgeColor}`}>
            <div className="flex items-center justify-between">
              <span className="text-[10px] font-bold uppercase tracking-wider opacity-80">Active Mode</span>
              <span className="rounded-full bg-slate-950/40 px-2 py-0.5 text-[10px] font-semibold border border-current/20">
                {config.title}
              </span>
            </div>
            <p className="text-xs font-semibold leading-snug">{config.subtitle}</p>
            <p className="text-[11px] leading-relaxed opacity-80">{config.goal}</p>

            {/* Mode switch radio pills */}
            <div className="grid grid-cols-3 gap-1 pt-1">
              {(['basic', 'pro', 'advanced'] as AppMode[]).map((m) => (
                <button
                  key={m}
                  onClick={() => setMode(m)}
                  className={`rounded-lg py-1 text-[10px] font-bold uppercase transition ${
                    mode === m
                      ? 'bg-slate-100 text-slate-950 shadow-sm'
                      : 'bg-slate-900/60 text-slate-400 hover:bg-slate-800 hover:text-slate-200'
                  }`}
                >
                  {m}
                </button>
              ))}
            </div>
          </div>

          {/* Navigation Links */}
          <div className="space-y-1">
            <span className="text-[10px] font-bold uppercase tracking-wider text-slate-500 px-3">
              Core Platform
            </span>
            <nav className="space-y-1 pt-1">
              {navItems.map((item) => {
                const Icon = item.icon
                return (
                  <NavLink
                    key={item.to}
                    to={item.to}
                    className={({ isActive }) =>
                      `flex items-center gap-3 rounded-xl px-4 py-2.5 text-xs transition ${
                        isActive
                          ? 'bg-cyan-400/10 text-cyan-200 font-semibold border border-cyan-400/20'
                          : 'text-slate-400 hover:bg-slate-800/60 hover:text-slate-100'
                      }`
                    }
                  >
                    <Icon size={16} />
                    {item.label}
                  </NavLink>
                )
              })}
            </nav>
          </div>

          {/* Mode-Specific Highlighted Capabilities */}
          <div className="space-y-2 border-t border-slate-800/80 pt-4">
            <span className="text-[10px] font-bold uppercase tracking-wider text-slate-500 px-3">
              {config.title} Workflows
            </span>

            {mode === 'basic' && (
              <div className="space-y-1 text-xs text-slate-400 px-2">
                <div className="flex items-center gap-2 p-2 rounded-xl bg-slate-900/40 border border-slate-800/60">
                  <FileCheck size={14} className="text-emerald-400 shrink-0" />
                  <span>Missing Values & Duplicates</span>
                </div>
                <div className="flex items-center gap-2 p-2 rounded-xl bg-slate-900/40 border border-slate-800/60">
                  <Wand2 size={14} className="text-emerald-400 shrink-0" />
                  <span>Outlier Detection & Rename</span>
                </div>
                <div className="flex items-center gap-2 p-2 rounded-xl bg-slate-900/40 border border-slate-800/60">
                  <Activity size={14} className="text-emerald-400 shrink-0" />
                  <span>Before/After Quality Stats</span>
                </div>
              </div>
            )}

            {mode === 'pro' && (
              <div className="space-y-1 text-xs text-slate-400 px-2">
                <div className="flex items-center gap-2 p-2 rounded-xl bg-slate-900/40 border border-slate-800/60">
                  <BarChart3 size={14} className="text-cyan-400 shrink-0" />
                  <span>Visuals (Bar, Scatter, Box)</span>
                </div>
                <div className="flex items-center gap-2 p-2 rounded-xl bg-slate-900/40 border border-slate-800/60">
                  <Activity size={14} className="text-cyan-400 shrink-0" />
                  <span>Correlation & Heatmaps</span>
                </div>
                <div className="flex items-center gap-2 p-2 rounded-xl bg-slate-900/40 border border-slate-800/60">
                  <Code2 size={14} className="text-cyan-400 shrink-0" />
                  <span>Interactive SQL Query Studio</span>
                </div>
              </div>
            )}

            {mode === 'advanced' && (
              <div className="space-y-1 text-xs text-slate-400 px-2">
                <div className="flex items-center gap-2 p-2 rounded-xl bg-slate-900/40 border border-slate-800/60">
                  <Lightbulb size={14} className="text-purple-400 shrink-0" />
                  <span>Project Insights & Executive EDA</span>
                </div>
                <div className="flex items-center gap-2 p-2 rounded-xl bg-slate-900/40 border border-slate-800/60">
                  <TrendingUp size={14} className="text-purple-400 shrink-0" />
                  <span>Forecasting Lab & Scenarios</span>
                </div>
                <div className="flex items-center gap-2 p-2 rounded-xl bg-slate-900/40 border border-slate-800/60">
                  <Presentation size={14} className="text-purple-400 shrink-0" />
                  <span>PDF, Word & PPTX Board Decks</span>
                </div>
              </div>
            )}
          </div>
        </div>

        {/* Sidebar Bottom Auth & System Status */}
        <div className="space-y-3 pt-6 border-t border-slate-800/60">
          {isAuthenticated && user ? (
            <div className="rounded-2xl border border-slate-800 bg-slate-900/60 p-3 flex items-center justify-between">
              <NavLink to="/settings" className="flex items-center gap-2.5 overflow-hidden group">
                <div className="flex h-8 w-8 items-center justify-center rounded-xl bg-cyan-400/20 text-cyan-300 font-bold text-xs uppercase shrink-0 group-hover:scale-105 transition-transform">
                  {user.full_name ? user.full_name.charAt(0) : user.email.charAt(0)}
                </div>
                <div className="overflow-hidden">
                  <p className="text-xs font-medium text-slate-200 truncate group-hover:text-cyan-300 transition">
                    {user.full_name || user.email.split('@')[0]}
                  </p>
                  <p className="text-[10px] text-slate-400 truncate">{user.email}</p>
                </div>
              </NavLink>
              <button
                onClick={logout}
                className="rounded-lg p-1.5 text-slate-400 hover:text-red-300 hover:bg-slate-800 transition shrink-0"
                title="Sign Out"
              >
                <LogOut size={15} />
              </button>
            </div>
          ) : (
            <div className="rounded-2xl border border-cyan-500/20 bg-gradient-to-b from-cyan-950/20 to-slate-900/60 p-3 space-y-2">
              <div className="flex items-center gap-1.5 text-xs font-semibold text-cyan-300">
                <Sparkles size={13} />
                <span>Analyticx Account</span>
              </div>
              <p className="text-[11px] leading-relaxed text-slate-400">
                Sign in to save dashboards, track history, and sync work.
              </p>
              <div className="flex gap-2 pt-1">
                <NavLink
                  to="/login"
                  className="flex-1 text-center rounded-xl border border-slate-700 bg-slate-800/90 py-1.5 text-[11px] font-medium text-slate-200 hover:border-cyan-400 hover:text-cyan-200 transition"
                >
                  Sign In
                </NavLink>
                <NavLink
                  to="/register"
                  className="flex-1 text-center rounded-xl bg-cyan-400 py-1.5 text-[11px] font-semibold text-slate-950 hover:bg-cyan-300 transition"
                >
                  Sign Up
                </NavLink>
              </div>
            </div>
          )}

          <div className="rounded-2xl border border-slate-800 bg-slate-900/40 p-2.5 text-[10px] text-slate-400 flex items-center gap-2">
            <Database size={13} className="text-cyan-400 shrink-0" />
            <span>Local mode active • No paid APIs</span>
          </div>
        </div>
      </aside>

      {/* Main Content Area */}
      <main
        className={`min-h-screen p-8 transition-all duration-300 ease-in-out ${
          sidebarOpen ? 'lg:ml-72' : 'ml-0'
        }`}
      >
        {/* Unverified Email Warning Banner */}
        {isAuthenticated && user && !user.is_verified && (
          <div className="mb-6 rounded-2xl border border-amber-500/30 bg-gradient-to-r from-amber-950/40 via-amber-900/20 to-slate-900/60 p-4 shadow-xl flex flex-wrap items-center justify-between gap-4 animate-in fade-in duration-300">
            <div className="flex items-center gap-3">
              <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-amber-500/20 text-amber-300 shrink-0">
                <Mail size={20} />
              </div>
              <div>
                <p className="text-sm font-semibold text-amber-200">Email Verification Required</p>
                <p className="text-xs text-slate-300">
                  Your email address <strong className="text-cyan-300">{user.email}</strong> is not yet verified. Please verify your email to secure your account.
                </p>
              </div>
            </div>
            <button
              onClick={() => setVerifyModalOpen(true)}
              className="rounded-xl bg-gradient-to-r from-amber-400 to-amber-500 hover:from-amber-300 hover:to-amber-400 text-slate-950 px-4 py-2 text-xs font-bold transition shadow-lg shadow-amber-500/20 flex items-center gap-1.5"
            >
              <ShieldCheck size={14} />
              <span>Verify Email with Code</span>
            </button>
          </div>
        )}

        <header className="mb-8 flex flex-wrap items-center justify-between gap-4">
          <div className="flex items-center gap-4">
            {!sidebarOpen && (
              <button
                onClick={toggleSidebar}
                className="flex items-center justify-center rounded-2xl border border-cyan-400/30 bg-slate-900/90 p-3 text-cyan-300 hover:border-cyan-400 hover:bg-cyan-400/10 hover:text-cyan-200 transition shadow-lg shadow-cyan-950/40 group"
                title="Show menu options"
              >
                <Menu size={22} className="group-hover:scale-110 transition-transform" />
              </button>
            )}
            <div>
              <p className="text-sm font-medium text-cyan-300">Analyticx AI</p>
              <h2 className="text-2xl font-bold tracking-tight">Business Analytics Workspace</h2>
            </div>
          </div>

          {/* Three Modes Switcher Bar */}
          <div className="flex items-center rounded-2xl border border-slate-800 bg-slate-950/80 p-1 backdrop-blur-md shadow-lg shadow-slate-950/40">
            {(['basic', 'pro', 'advanced'] as AppMode[]).map((m) => {
              const item = MODES[m]
              const isActive = mode === m
              return (
                <button
                  key={m}
                  onClick={() => setMode(m)}
                  className={`flex items-center gap-2 rounded-xl px-3.5 py-1.5 text-xs font-semibold transition ${
                    isActive
                      ? `${item.activeTabColor} shadow-md`
                      : 'text-slate-400 hover:text-slate-200 hover:bg-slate-900/60'
                  }`}
                  title={item.goal}
                >
                  <span
                    className={`h-2 w-2 rounded-full ${
                      m === 'basic' ? 'bg-emerald-400' : m === 'pro' ? 'bg-cyan-400' : 'bg-purple-400'
                    }`}
                  />
                  <span>{item.title}</span>
                </button>
              )
            })}
          </div>

          <div className="flex items-center gap-3">
            {/* Analyticx Multilingual Copilot Button */}
            <button
              onClick={() => setCopilotOpen((prev) => !prev)}
              className="inline-flex items-center gap-2 rounded-2xl border border-cyan-500/40 bg-gradient-to-r from-cyan-950/60 to-blue-950/60 px-4 py-2 text-sm font-semibold text-cyan-300 hover:border-cyan-400 hover:from-cyan-900/80 hover:to-blue-900/80 transition shadow-lg shadow-cyan-950/30"
              title="Open Analyticx AI Multilingual Copilot"
            >
              <Sparkles size={16} className="text-cyan-400 animate-pulse" />
              <span>Analyticx Copilot</span>
              <span className="rounded-full bg-cyan-400/20 px-2 py-0.5 text-[10px] font-medium text-cyan-200 border border-cyan-400/30">
                Multilingual
              </span>
            </button>

            {/* Notifications Bell */}
            {isAuthenticated && (
              <div className="relative">
                <button
                  onClick={() => setNotifsOpen((p) => !p)}
                  className="relative flex items-center justify-center rounded-2xl border border-slate-800 bg-slate-900/80 p-2.5 text-slate-300 hover:border-cyan-400 hover:text-cyan-300 transition"
                  title="Notifications"
                >
                  <Bell size={18} />
                  {unreadCount > 0 && (
                    <span className="absolute -top-1 -right-1 flex h-4.5 min-w-4.5 items-center justify-center rounded-full bg-cyan-400 px-1 text-[10px] font-bold text-slate-950">
                      {unreadCount}
                    </span>
                  )}
                </button>

                {/* Notifications Dropdown Panel */}
                {notifsOpen && (
                  <div className="absolute right-0 top-12 z-50 w-80 sm:w-96 rounded-2xl border border-slate-800 bg-slate-950 p-4 shadow-2xl backdrop-blur-2xl space-y-3">
                    <div className="flex items-center justify-between pb-2 border-b border-slate-800">
                      <div className="flex items-center gap-2">
                        <Bell size={15} className="text-cyan-400" />
                        <span className="text-xs font-bold text-slate-100">Notifications ({unreadCount})</span>
                      </div>
                      {unreadCount > 0 && (
                        <button
                          onClick={async () => {
                            await authService.markAllNotificationsRead()
                            setUnreadCount(0)
                            setNotifications((prev) => prev.map((n) => ({ ...n, is_read: true })))
                          }}
                          className="inline-flex items-center gap-1 text-[10px] font-medium text-cyan-400 hover:text-cyan-300"
                        >
                          <CheckCheck size={12} />
                          <span>Mark all read</span>
                        </button>
                      )}
                    </div>

                    <div className="max-h-72 overflow-y-auto space-y-2 pr-1">
                      {notifications.length === 0 ? (
                        <p className="text-center py-6 text-xs text-slate-500">No notifications yet.</p>
                      ) : (
                        notifications.map((n) => (
                          <div
                            key={n.id}
                            onClick={async () => {
                              if (!n.is_read) {
                                await authService.markNotificationRead(n.id)
                                setUnreadCount((c) => Math.max(0, c - 1))
                                setNotifications((prev) =>
                                  prev.map((item) => (item.id === n.id ? { ...item, is_read: true } : item))
                                )
                              }
                              if (n.link) {
                                setNotifsOpen(false)
                                navigate(n.link)
                              }
                            }}
                            className={`cursor-pointer rounded-xl border p-2.5 text-xs transition ${
                              n.is_read
                                ? 'border-slate-800/60 bg-slate-900/30 text-slate-400'
                                : 'border-cyan-500/30 bg-cyan-950/20 text-slate-200'
                            }`}
                          >
                            <p className="font-semibold text-slate-200">{n.title}</p>
                            <p className="text-[11px] text-slate-400 mt-0.5 line-clamp-2">{n.message}</p>
                            {n.created_at && (
                              <p className="text-[9px] text-slate-500 mt-1">
                                {new Date(n.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                              </p>
                            )}
                          </div>
                        ))
                      )}
                    </div>
                  </div>
                )}
              </div>
            )}

            {/* Authentication Header Widget */}
            {isAuthenticated && user ? (
              <div className="flex items-center gap-2.5 rounded-2xl border border-slate-800 bg-slate-900/80 pl-2.5 pr-2 py-1.5 text-xs text-slate-200">
                <NavLink
                  to="/settings"
                  className="flex items-center gap-2 hover:opacity-90 transition group"
                  title="View Account Settings"
                >
                  <div className="flex h-7 w-7 items-center justify-center rounded-xl bg-cyan-400/20 text-cyan-300 font-bold text-xs uppercase group-hover:scale-105 transition-transform">
                    {user.full_name ? user.full_name.charAt(0) : user.email.charAt(0)}
                  </div>
                  <div className="hidden sm:block text-left">
                    <p className="font-medium text-slate-100 truncate max-w-[130px] group-hover:text-cyan-300 transition">
                      {user.full_name || user.email.split('@')[0]}
                    </p>
                    <p className="text-[10px] text-slate-400 truncate max-w-[130px]">
                      {user.role || user.email}
                    </p>
                  </div>
                </NavLink>
                <button
                  onClick={logout}
                  className="rounded-lg p-1.5 text-slate-400 hover:text-red-300 hover:bg-slate-800 transition"
                  title="Sign Out"
                >
                  <LogOut size={15} />
                </button>
              </div>
            ) : (
              <div className="flex items-center gap-2">
                <NavLink
                  to="/login"
                  className="inline-flex items-center gap-1.5 rounded-2xl border border-slate-700 bg-slate-900/80 px-3.5 py-2 text-xs font-medium text-slate-200 hover:border-cyan-400/50 hover:text-cyan-200 transition"
                >
                  <LogIn size={14} />
                  <span>Sign In</span>
                </NavLink>
                <NavLink
                  to="/register"
                  className="inline-flex items-center gap-1.5 rounded-2xl bg-cyan-400 px-3.5 py-2 text-xs font-semibold text-slate-950 hover:bg-cyan-300 transition shadow-md shadow-cyan-950/40"
                >
                  <UserPlus size={14} />
                  <span>Sign Up</span>
                </NavLink>
              </div>
            )}

            {sidebarOpen && (
              <button
                onClick={toggleSidebar}
                className="hidden sm:inline-flex items-center gap-2 rounded-2xl border border-slate-800 bg-slate-900/70 px-3 py-2 text-xs text-slate-400 hover:border-cyan-500/50 hover:bg-slate-800 hover:text-cyan-300 transition"
                title="Hide menu options"
              >
                <Menu size={16} />
                <span>Hide menu</span>
              </button>
            )}
          </div>
        </header>

        <Outlet />

        {/* Global Floating Copilot Trigger (when modal is closed) */}
        {!copilotOpen && (
          <button
            onClick={() => setCopilotOpen(true)}
            className="fixed bottom-6 right-6 z-40 flex items-center gap-2.5 rounded-full border border-cyan-400/40 bg-slate-950/90 px-4 py-3 text-sm font-medium text-cyan-200 shadow-2xl backdrop-blur-xl hover:border-cyan-300 hover:bg-slate-900 hover:scale-105 transition duration-200 group"
          >
            <div className="flex h-7 w-7 items-center justify-center rounded-full bg-gradient-to-tr from-cyan-400 to-blue-500 text-slate-950 shadow">
              <Sparkles size={16} className="group-hover:rotate-12 transition-transform" />
            </div>
            <span>Ask Copilot</span>
          </button>
        )}

        {/* Universal Multilingual Copilot Modal */}
        <UniversalCopilotModal
          isOpen={copilotOpen}
          onClose={() => setCopilotOpen(false)}
        />

        {/* Email Verification Modal */}
        <VerifyEmailModal
          isOpen={verifyModalOpen}
          onClose={() => setVerifyModalOpen(false)}
        />
      </main>
    </div>
  )
}
