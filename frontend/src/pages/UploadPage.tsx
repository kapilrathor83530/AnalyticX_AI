import {
  Activity,
  Archive,
  BarChart3,
  Brain,
  CheckCircle2,
  Clock,
  Database,
  FileSpreadsheet,
  FileText,
  FolderPlus,
  LayoutDashboard,
  Lightbulb,
  LineChart,
  MessageSquare,
  Plus,
  RotateCcw,
  Sparkles,
  Trash2,
  TrendingUp,
  UploadCloud,
  User,
  Wand2,
} from 'lucide-react'
import { useEffect, useRef, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { api, getErrorMessage } from '../api/client'
import { useAuth } from '../contexts/AuthContext'
import { authService } from '../services/authService'
import type { ActivityItem, Workspace } from '../types/auth'
import type { Dataset } from '../types'

export default function UploadPage() {
  const { user, isAuthenticated } = useAuth()
  const navigate = useNavigate()

  const [datasets, setDatasets] = useState<Dataset[]>([])
  const [workspaces, setWorkspaces] = useState<Workspace[]>([])
  const [activities, setActivities] = useState<ActivityItem[]>([])
  const [error, setError] = useState('')
  const [uploading, setUploading] = useState(false)
  const [selectedWorkspaceId, setSelectedWorkspaceId] = useState<number | undefined>(undefined)

  // New Project Modal State
  const [newProjectModalOpen, setNewProjectModalOpen] = useState(false)
  const [newProjectName, setNewProjectName] = useState('')
  const [newProjectDesc, setNewProjectDesc] = useState('')
  const [projectCreating, setProjectCreating] = useState(false)

  const inputRef = useRef<HTMLInputElement>(null)

  // Determine greeting based on current local hour
  const hour = new Date().getHours()
  const greeting = hour < 12 ? 'Good morning' : hour < 17 ? 'Good afternoon' : 'Good evening'
  const displayName = user?.full_name || (user?.email ? user.email.split('@')[0] : 'Analyst')

  async function loadAllData() {
    try {
      const [dsRes, wsRes] = await Promise.all([
        api.get<Dataset[]>('/datasets'),
        authService.listWorkspaces().catch(() => [] as Workspace[]),
      ])
      setDatasets(dsRes.data)
      setWorkspaces(wsRes)
    } catch (err) {
      setError(getErrorMessage(err))
    }

    if (isAuthenticated) {
      try {
        const actList = await authService.getActivity(8)
        setActivities(actList)
      } catch {
        // Non-blocking
      }
    }
  }

  useEffect(() => {
    loadAllData()
  }, [isAuthenticated])

  async function uploadFile(file: File) {
    setError('')
    setUploading(true)
    const form = new FormData()
    form.append('file', file)
    if (selectedWorkspaceId) {
      form.append('workspace_id', String(selectedWorkspaceId))
    }

    try {
      await api.post('/datasets/upload', form, {
        headers: { 'Content-Type': 'multipart/form-data' },
      })
      await loadAllData()
    } catch (err) {
      setError(getErrorMessage(err))
    } finally {
      setUploading(false)
    }
  }

  async function deleteDataset(id: number) {
    if (!window.confirm('Are you sure you want to delete this dataset? This action is permanent.')) return
    try {
      await api.delete(`/datasets/${id}`)
      await loadAllData()
    } catch (err) {
      setError(getErrorMessage(err))
    }
  }

  async function handleCreateProject(e: React.FormEvent) {
    e.preventDefault()
    if (!newProjectName.trim()) return
    setProjectCreating(true)
    try {
      await authService.createWorkspace(newProjectName.trim(), newProjectDesc.trim() || undefined)
      setNewProjectName('')
      setNewProjectDesc('')
      setNewProjectModalOpen(false)
      await loadAllData()
    } catch (err) {
      setError(getErrorMessage(err))
    } finally {
      setProjectCreating(false)
    }
  }

  async function handleDeleteProject(id: number) {
    if (!window.confirm('Are you sure you want to remove this project?')) return
    try {
      await authService.deleteWorkspace(id)
      await loadAllData()
    } catch (err) {
      setError(getErrorMessage(err))
    }
  }

  // Count user-owned datasets vs sample datasets
  const myDatasets = datasets.filter((d) => (d as any).user_id === user?.id || (!(d as any).is_sample && isAuthenticated))
  const sampleDatasets = datasets.filter((d) => (d as any).is_sample)
  const activeDsId = datasets[0]?.id || 1

  return (
    <div className="space-y-8 pb-12">
      {/* 1. PERSONALIZED WELCOME HEADER */}
      <section className="glass rounded-3xl border border-slate-800/90 bg-gradient-to-r from-slate-950 via-slate-900/90 to-cyan-950/20 p-6 md:p-8 shadow-2xl relative overflow-hidden">
        <div className="absolute top-0 right-0 h-64 w-64 rounded-full bg-cyan-500/10 blur-3xl pointer-events-none" />

        <div className="flex flex-col md:flex-row md:items-center justify-between gap-6 relative z-10">
          <div className="flex items-start sm:items-center gap-4">
            <div className="h-14 w-14 sm:h-16 sm:w-16 rounded-2xl bg-gradient-to-tr from-cyan-400 to-blue-500 text-slate-950 font-bold text-2xl flex items-center justify-center uppercase shadow-lg shadow-cyan-500/20 shrink-0">
              {displayName.charAt(0)}
            </div>
            <div>
              <div className="flex flex-wrap items-center gap-2">
                <h1 className="text-2xl sm:text-3xl font-extrabold tracking-tight text-slate-100">
                  {greeting}, {displayName}!
                </h1>
                <span className="rounded-full bg-cyan-400/15 border border-cyan-400/30 px-2.5 py-0.5 text-[11px] font-semibold text-cyan-300">
                  {user?.role || 'Data Analyst'}
                </span>
                {user?.is_verified && (
                  <span className="inline-flex items-center gap-1 rounded-full bg-emerald-500/15 border border-emerald-500/30 px-2 py-0.5 text-[10px] font-medium text-emerald-400">
                    <CheckCircle2 size={10} /> Verified
                  </span>
                )}
              </div>
              <p className="text-xs text-slate-400 mt-1 max-w-xl">
                Welcome to your <span className="text-cyan-300 font-medium">Analyticx AI</span> command center. Your datasets, dashboards, models, and forecasts remain strictly private and isolated.
              </p>
            </div>
          </div>

          {/* Quick Metrics Bar */}
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-2.5">
            <div className="rounded-2xl border border-slate-800 bg-slate-900/80 p-3 text-center">
              <div className="text-xl font-bold text-slate-100">{datasets.length}</div>
              <div className="text-[10px] uppercase font-semibold text-slate-400">Datasets</div>
            </div>
            <div className="rounded-2xl border border-slate-800 bg-slate-900/80 p-3 text-center">
              <div className="text-xl font-bold text-cyan-300">{workspaces.length}</div>
              <div className="text-[10px] uppercase font-semibold text-slate-400">Projects</div>
            </div>
            <div className="rounded-2xl border border-slate-800 bg-slate-900/80 p-3 text-center">
              <div className="text-xl font-bold text-purple-300">Active</div>
              <div className="text-[10px] uppercase font-semibold text-slate-400">Copilot</div>
            </div>
            <div className="rounded-2xl border border-slate-800 bg-slate-900/80 p-3 text-center">
              <div className="text-xl font-bold text-emerald-300">100%</div>
              <div className="text-[10px] uppercase font-semibold text-slate-400">Data Privacy</div>
            </div>
          </div>
        </div>

        {/* Action Pills */}
        <div className="flex flex-wrap items-center gap-2 pt-6 mt-6 border-t border-slate-800/60">
          <button
            onClick={() => inputRef.current?.click()}
            className="inline-flex items-center gap-2 rounded-xl bg-cyan-400 px-4 py-2 text-xs font-bold text-slate-950 hover:bg-cyan-300 transition shadow-md shadow-cyan-950/40"
          >
            <UploadCloud size={14} />
            <span>Upload Dataset</span>
          </button>
          <button
            onClick={() => setNewProjectModalOpen(true)}
            className="inline-flex items-center gap-2 rounded-xl border border-slate-700 bg-slate-900/80 px-3.5 py-2 text-xs font-semibold text-slate-200 hover:border-cyan-400/50 hover:text-cyan-300 transition"
          >
            <FolderPlus size={14} />
            <span>New Project</span>
          </button>
          <Link
            to={`/data-prep/${activeDsId}`}
            className="inline-flex items-center gap-1.5 rounded-xl border border-slate-800 bg-slate-900/60 px-3.5 py-2 text-xs font-medium text-teal-300 hover:border-teal-400/40 transition"
          >
            <Wand2 size={14} />
            <span>AI Prep</span>
          </Link>
          <Link
            to={`/datasets/${activeDsId}`}
            className="inline-flex items-center gap-1.5 rounded-xl border border-slate-800 bg-slate-900/60 px-3.5 py-2 text-xs font-medium text-slate-300 hover:border-slate-700 hover:text-slate-100 transition"
          >
            <Database size={14} />
            <span>Explorer</span>
          </Link>
          <Link
            to={`/analytics/${activeDsId}`}
            className="inline-flex items-center gap-1.5 rounded-xl border border-slate-800 bg-slate-900/60 px-3.5 py-2 text-xs font-medium text-cyan-300 hover:border-cyan-400/40 transition"
          >
            <BarChart3 size={14} />
            <span>Analytics</span>
          </Link>
          <Link
            to={`/studio/${activeDsId}`}
            className="inline-flex items-center gap-1.5 rounded-xl border border-slate-800 bg-slate-900/60 px-3.5 py-2 text-xs font-medium text-emerald-300 hover:border-emerald-400/40 transition"
          >
            <LineChart size={14} />
            <span>Visual Studio</span>
          </Link>
          <Link
            to={`/insights/${activeDsId}`}
            className="inline-flex items-center gap-1.5 rounded-xl border border-slate-800 bg-slate-900/60 px-3.5 py-2 text-xs font-medium text-purple-300 hover:border-purple-400/40 transition"
          >
            <Lightbulb size={14} />
            <span>Insight</span>
          </Link>
          <Link
            to={`/forecasting/${activeDsId}`}
            className="inline-flex items-center gap-1.5 rounded-xl border border-slate-800 bg-slate-900/60 px-3.5 py-2 text-xs font-medium text-amber-300 hover:border-amber-400/40 transition"
          >
            <TrendingUp size={14} />
            <span>Forecast</span>
          </Link>
          <Link
            to="/dashboards"
            className="inline-flex items-center gap-1.5 rounded-xl border border-slate-800 bg-slate-900/60 px-3.5 py-2 text-xs font-medium text-slate-300 hover:border-slate-700 hover:text-slate-100 transition"
          >
            <LayoutDashboard size={14} />
            <span>Dashboards</span>
          </Link>
          <Link
            to="/reports"
            className="inline-flex items-center gap-1.5 rounded-xl border border-slate-800 bg-slate-900/60 px-3.5 py-2 text-xs font-medium text-slate-300 hover:border-slate-700 hover:text-slate-100 transition"
          >
            <Archive size={14} />
            <span>Report Center</span>
          </Link>
        </div>
      </section>

      {/* 2. RECENT PROJECTS SECTION */}
      {workspaces.length > 0 && (
        <section className="space-y-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2 text-slate-100 font-bold text-base">
              <FolderPlus size={18} className="text-cyan-400" />
              <h2>Authorized Projects ({workspaces.length})</h2>
            </div>
            <button
              onClick={() => setNewProjectModalOpen(true)}
              className="inline-flex items-center gap-1.5 text-xs text-cyan-400 hover:text-cyan-300 font-medium"
            >
              <Plus size={14} />
              <span>Create Project</span>
            </button>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
            {workspaces.map((ws) => (
              <div
                key={ws.id}
                className="glass rounded-2xl border border-slate-800 bg-slate-900/50 p-5 hover:border-cyan-400/40 transition space-y-3 flex flex-col justify-between"
              >
                <div>
                  <div className="flex items-center justify-between gap-2">
                    <h3 className="font-bold text-sm text-slate-100 truncate">{ws.name}</h3>
                    <button
                      onClick={() => handleDeleteProject(ws.id)}
                      className="text-slate-500 hover:text-red-400 p-1"
                      title="Delete Project"
                    >
                      <Trash2 size={13} />
                    </button>
                  </div>
                  <p className="text-xs text-slate-400 mt-1 line-clamp-2">
                    {ws.description || 'No description provided.'}
                  </p>
                </div>
                <div className="flex items-center justify-between pt-3 border-t border-slate-800/60 text-[11px] text-slate-400">
                  <span>Created {new Date(ws.created_at).toLocaleDateString()}</span>
                  <Link
                    to="/insights/1"
                    className="text-cyan-400 hover:text-cyan-300 font-semibold"
                  >
                    Open Project →
                  </Link>
                </div>
              </div>
            ))}
          </div>
        </section>
      )}

      {/* 3. DRAG & DROP UPLOAD ZONE */}
      <section
        className="glass rounded-3xl p-8 md:p-10 text-center border border-slate-800/90 bg-slate-950/80 relative"
        onDragOver={(event) => event.preventDefault()}
        onDrop={(event) => {
          event.preventDefault()
          const file = event.dataTransfer.files?.[0]
          if (file) uploadFile(file)
        }}
      >
        <div className="mx-auto mb-4 flex h-16 w-16 items-center justify-center rounded-3xl bg-cyan-400/10 text-cyan-300">
          <UploadCloud size={32} />
        </div>
        <h2 className="text-2xl font-bold tracking-tight text-slate-100">Upload Dataset to Personal Workspace</h2>
        <p className="mx-auto mt-2 max-w-xl text-xs text-slate-400 leading-relaxed">
          Drop CSV, XLSX, XLS, or PDF files up to 200 MB. Analyticx AI will parse tabular structures, inspect data quality, calculate statistics, and prepare interactive EDA.
        </p>

        {/* Project association selector if workspaces exist */}
        {workspaces.length > 0 && (
          <div className="mt-4 flex items-center justify-center gap-2 text-xs">
            <span className="text-slate-400">Attach to Project:</span>
            <select
              value={selectedWorkspaceId || ''}
              onChange={(e) => setSelectedWorkspaceId(e.target.value ? Number(e.target.value) : undefined)}
              className="rounded-xl border border-slate-700 bg-slate-900 px-3 py-1.5 text-xs text-slate-200 outline-none focus:border-cyan-400"
            >
              <option value="">Default Workspace</option>
              {workspaces.map((w) => (
                <option key={w.id} value={w.id}>
                  {w.name}
                </option>
              ))}
            </select>
          </div>
        )}

        <input
          ref={inputRef}
          type="file"
          accept=".csv,.xlsx,.xls,.pdf"
          className="hidden"
          onChange={(event) => {
            const file = event.target.files?.[0]
            if (file) uploadFile(file)
          }}
        />

        <button
          onClick={() => inputRef.current?.click()}
          disabled={uploading}
          className="mt-6 inline-flex items-center gap-2 rounded-2xl bg-cyan-400 px-6 py-3 text-xs font-bold text-slate-950 transition hover:bg-cyan-300 disabled:opacity-50 shadow-lg shadow-cyan-950/40"
        >
          <UploadCloud size={16} />
          {uploading ? 'Validating & Uploading Dataset…' : 'Choose Data File (CSV, Excel, PDF)'}
        </button>

        {error && (
          <div className="mx-auto mt-4 max-w-xl rounded-xl border border-red-500/30 bg-red-500/10 px-4 py-3 text-xs text-red-200">
            {error}
          </div>
        )}
      </section>

      {/* 4. REGISTERED DATASETS TABLE */}
      <section className="glass rounded-3xl border border-slate-800 bg-slate-950/70 p-6 space-y-5">
        <div className="flex flex-wrap items-center justify-between gap-4">
          <div className="flex items-center gap-3">
            <Database size={20} className="text-cyan-400" />
            <h2 className="text-lg font-bold text-slate-100">
              Workspace Datasets ({datasets.length})
            </h2>
          </div>
          <div className="flex items-center gap-2 text-xs">
            <span className="rounded-full bg-cyan-400/10 border border-cyan-400/30 px-2.5 py-0.5 text-[11px] font-semibold text-cyan-300">
              {myDatasets.length} Personal
            </span>
            <span className="rounded-full bg-slate-800 border border-slate-700 px-2.5 py-0.5 text-[11px] font-semibold text-slate-400">
              {sampleDatasets.length} Sample Data
            </span>
          </div>
        </div>

        {datasets.length === 0 ? (
          <div className="rounded-2xl border border-dashed border-slate-800 p-8 text-center text-xs text-slate-400 space-y-3">
            <p>No datasets in your authorized workspace yet.</p>
            <div className="flex justify-center gap-3">
              <button
                onClick={() => inputRef.current?.click()}
                className="rounded-xl bg-cyan-400 px-4 py-2 text-xs font-bold text-slate-950 hover:bg-cyan-300"
              >
                Upload First Dataset
              </button>
            </div>
          </div>
        ) : (
          <div className="grid gap-3.5">
            {datasets.map((dataset) => {
              const isPdf = dataset.original_filename?.toLowerCase().endsWith('.pdf')
              const score = dataset.quality_score
              const isSample = (dataset as any).is_sample

              return (
                <div
                  key={dataset.id}
                  className="flex flex-col gap-4 rounded-2xl border border-slate-800/80 bg-slate-900/50 p-4 md:flex-row md:items-center md:justify-between hover:border-slate-700 transition"
                >
                  <div className="flex items-start gap-3.5">
                    <div className="rounded-xl bg-slate-800 p-2.5 text-cyan-300 shrink-0">
                      {isPdf ? <FileText size={20} className="text-rose-400" /> : <FileSpreadsheet size={20} />}
                    </div>
                    <div>
                      <div className="flex flex-wrap items-center gap-2">
                        <h3 className="font-bold text-sm text-slate-100">{dataset.name}</h3>
                        {isSample ? (
                          <span className="rounded-full bg-slate-800 border border-slate-700 px-2 py-0.5 text-[10px] font-semibold text-slate-300">
                            Sample Data
                          </span>
                        ) : (
                          <span className="rounded-full bg-cyan-400/10 border border-cyan-400/30 px-2 py-0.5 text-[10px] font-semibold text-cyan-300">
                            Personal Dataset
                          </span>
                        )}
                        {score !== null && score !== undefined && (
                          <span
                            className={`rounded-full border px-2 py-0.5 text-[10px] font-semibold ${
                              score >= 80
                                ? 'bg-emerald-500/10 border-emerald-500/30 text-emerald-300'
                                : score >= 50
                                ? 'bg-amber-500/10 border-amber-500/30 text-amber-300'
                                : 'bg-rose-500/10 border-rose-500/30 text-rose-300'
                            }`}
                          >
                            Quality: {score}%
                          </span>
                        )}
                      </div>
                      <p className="text-xs text-slate-400 mt-1">
                        {dataset.row_count.toLocaleString()} rows · {dataset.column_count} columns ·{' '}
                        {(dataset.size_bytes / 1024).toFixed(1)} KB · Uploaded {new Date(dataset.created_at).toLocaleDateString()}
                      </p>
                    </div>
                  </div>

                  <div className="flex flex-wrap items-center gap-1.5">
                    {/* 1. AI Prep */}
                    <Link
                      to={`/data-prep/${dataset.id}`}
                      className="inline-flex items-center gap-1.5 rounded-xl bg-gradient-to-r from-teal-500 to-cyan-500 px-3 py-1.5 text-xs font-bold text-slate-950 hover:brightness-110 transition shadow-sm"
                      title="AI Data Prep Studio: Clean, Transform & Impute"
                    >
                      <Wand2 size={13} />
                      <span>AI Prep</span>
                    </Link>

                    {/* 2. Explorer */}
                    <Link
                      to={`/datasets/${dataset.id}`}
                      className="inline-flex items-center gap-1.5 rounded-xl border border-slate-700 bg-slate-900/80 px-3 py-1.5 text-xs font-semibold text-slate-300 hover:border-slate-600 hover:text-slate-100 transition"
                      title="Dataset Table Explorer & Schema Inspection"
                    >
                      <Database size={13} />
                      <span>Explorer</span>
                    </Link>

                    {/* 3. Analytics */}
                    <Link
                      to={`/analytics/${dataset.id}`}
                      className="inline-flex items-center gap-1.5 rounded-xl border border-slate-700 bg-slate-900/80 px-3 py-1.5 text-xs font-semibold text-cyan-300 hover:border-cyan-400/50 hover:text-cyan-200 transition"
                      title="Advanced Statistical Analytics & Hypothesis Testing"
                    >
                      <BarChart3 size={13} />
                      <span>Analytics</span>
                    </Link>

                    {/* 4. Visual Studio */}
                    <Link
                      to={`/studio/${dataset.id}`}
                      className="inline-flex items-center gap-1.5 rounded-xl border border-slate-700 bg-slate-900/80 px-3 py-1.5 text-xs font-semibold text-emerald-300 hover:border-emerald-400/50 hover:text-emerald-200 transition"
                      title="Visualization Studio & Chart Builder"
                    >
                      <LineChart size={13} />
                      <span>Visual Studio</span>
                    </Link>

                    {/* 5. Insight */}
                    <Link
                      to={`/insights/${dataset.id}`}
                      className="inline-flex items-center gap-1.5 rounded-xl border border-slate-700 bg-slate-900/80 px-3 py-1.5 text-xs font-semibold text-purple-300 hover:border-purple-400/50 hover:text-purple-200 transition"
                      title="Project Insights & Executive Driver Discovery"
                    >
                      <Lightbulb size={13} />
                      <span>Insight</span>
                    </Link>

                    {/* 6. Forecast */}
                    <Link
                      to={`/forecasting/${dataset.id}`}
                      className="inline-flex items-center gap-1.5 rounded-xl border border-slate-700 bg-slate-900/80 px-3 py-1.5 text-xs font-semibold text-amber-300 hover:border-amber-400/50 hover:text-amber-200 transition"
                      title="Forecasting Lab & Predictive Modeling"
                    >
                      <TrendingUp size={13} />
                      <span>Forecast</span>
                    </Link>

                    {!isSample && (
                      <button
                        onClick={() => deleteDataset(dataset.id)}
                        className="rounded-xl border border-red-500/20 bg-slate-900/80 p-2 text-xs text-red-400 hover:bg-red-500/10 hover:border-red-500/40 transition ml-1"
                        title="Delete Dataset"
                      >
                        <Trash2 size={14} />
                      </button>
                    )}
                  </div>
                </div>
              )
            })}
          </div>
        )}
      </section>

      {/* 5. RECENT ACTIVITY STREAM */}
      {activities.length > 0 && (
        <section className="glass rounded-3xl border border-slate-800 bg-slate-950/70 p-6 space-y-4">
          <div className="flex items-center gap-2 text-slate-100 font-bold text-base">
            <Activity size={18} className="text-cyan-400" />
            <h2>Recent Workspace Activity</h2>
          </div>

          <div className="space-y-2.5">
            {activities.map((act) => (
              <div
                key={act.id}
                className="rounded-xl border border-slate-800/80 bg-slate-900/40 px-4 py-3 flex items-center justify-between text-xs"
              >
                <div className="flex items-center gap-3">
                  <div className="h-2 w-2 rounded-full bg-cyan-400 shrink-0" />
                  <div>
                    <span className="font-semibold text-slate-200">{act.title}</span>
                    {act.description && (
                      <span className="text-slate-400 ml-2 font-normal hidden sm:inline">
                        — {act.description}
                      </span>
                    )}
                  </div>
                </div>
                <div className="flex items-center gap-1.5 text-slate-500 shrink-0 font-mono text-[11px]">
                  <Clock size={12} />
                  <span>{new Date(act.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}</span>
                </div>
              </div>
            ))}
          </div>
        </section>
      )}

      {/* New Project Modal */}
      {newProjectModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 backdrop-blur-md p-4">
          <div className="glass w-full max-w-md rounded-3xl border border-slate-800 bg-slate-950 p-6 shadow-2xl space-y-4">
            <div className="flex items-center gap-2.5 text-cyan-300">
              <FolderPlus size={20} />
              <h3 className="font-bold text-slate-100">Create New Project</h3>
            </div>
            <p className="text-xs text-slate-400">
              Projects organize related datasets, custom dashboards, and forecasting scenarios under a single workspace.
            </p>

            <form onSubmit={handleCreateProject} className="space-y-4">
              <div>
                <label className="block text-xs font-medium text-slate-300 mb-1">Project Name <span className="text-red-400">*</span></label>
                <input
                  type="text"
                  required
                  placeholder="e.g. Q4 Retail Expansion"
                  value={newProjectName}
                  onChange={(e) => setNewProjectName(e.target.value)}
                  className="w-full rounded-xl border border-slate-700 bg-slate-900 px-3 py-2 text-xs text-slate-100 outline-none focus:border-cyan-400"
                />
              </div>

              <div>
                <label className="block text-xs font-medium text-slate-300 mb-1">Description (Optional)</label>
                <textarea
                  rows={3}
                  placeholder="Goals, target KPIs, and assumptions..."
                  value={newProjectDesc}
                  onChange={(e) => setNewProjectDesc(e.target.value)}
                  className="w-full rounded-xl border border-slate-700 bg-slate-900 px-3 py-2 text-xs text-slate-100 outline-none focus:border-cyan-400 resize-none"
                />
              </div>

              <div className="flex justify-end gap-2 pt-2">
                <button
                  type="button"
                  onClick={() => setNewProjectModalOpen(false)}
                  className="rounded-xl border border-slate-800 px-4 py-2 text-xs text-slate-400 hover:bg-slate-900"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={projectCreating}
                  className="rounded-xl bg-cyan-400 px-5 py-2 text-xs font-bold text-slate-950 hover:bg-cyan-300 disabled:opacity-50"
                >
                  {projectCreating ? 'Creating Project...' : 'Create Project'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  )
}
