import { Trash2 } from 'lucide-react'
import { useEffect, useState } from 'react'
import { getErrorMessage } from '../api/client'
import { useAuth } from '../contexts/AuthContext'
import { authService } from '../services/authService'
import type { Workspace } from '../types/auth'

export default function WorkspaceManagementPage() {
  const { user, isAuthenticated } = useAuth()
  const [workspaces, setWorkspaces] = useState<Workspace[]>([])
  const [name, setName] = useState('')
  const [description, setDescription] = useState('')
  const [error, setError] = useState('')

  async function load() {
    try {
      const list = await authService.listWorkspaces()
      setWorkspaces(list)
    } catch (err) {
      setError(getErrorMessage(err))
    }
  }

  useEffect(() => {
    load()
  }, [])

  async function create() {
    if (!name.trim()) return
    try {
      await authService.createWorkspace(name, description)
      setName('')
      setDescription('')
      await load()
    } catch (err) {
      setError(getErrorMessage(err))
    }
  }

  async function remove(id: number) {
    try {
      await authService.deleteWorkspace(id)
      setWorkspaces((prev) => prev.filter((w) => w.id !== id))
    } catch (err) {
      setError(getErrorMessage(err))
    }
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold">Workspaces</h1>
        <p className="text-sm text-slate-400">
          {isAuthenticated ? `Signed in as ${user?.email}` : 'Local mode — workspaces are not user-scoped.'}
        </p>
      </div>

      {error && (
        <div className="rounded-2xl border border-red-500/30 bg-red-500/10 px-4 py-3 text-sm text-red-200">
          {error}
        </div>
      )}

      <div className="glass space-y-4 rounded-3xl p-6">
        <h2 className="text-lg font-semibold">Create Workspace</h2>
        <div className="grid gap-3 md:grid-cols-3">
          <input
            className="rounded-xl border border-slate-700 bg-slate-900 px-3 py-2 text-sm"
            placeholder="Name"
            value={name}
            onChange={(e) => setName(e.target.value)}
          />
          <input
            className="rounded-xl border border-slate-700 bg-slate-900 px-3 py-2 text-sm"
            placeholder="Description"
            value={description}
            onChange={(e) => setDescription(e.target.value)}
          />
          <button
            onClick={create}
            className="rounded-xl bg-cyan-400 px-4 py-2 text-sm font-semibold text-slate-950 hover:bg-cyan-300"
          >
            Create
          </button>
        </div>
      </div>

      <div className="glass rounded-3xl p-6">
        <h2 className="mb-4 text-lg font-semibold">Your Workspaces</h2>
        {workspaces.length === 0 ? (
          <p className="text-sm text-slate-500">No workspaces yet.</p>
        ) : (
          <ul className="space-y-2">
            {workspaces.map((workspace) => (
              <li
                key={workspace.id}
                className="flex items-center justify-between rounded-xl border border-slate-800 bg-slate-900/40 px-4 py-3"
              >
                <div>
                  <div className="text-sm font-medium text-slate-100">{workspace.name}</div>
                  {workspace.description && (
                    <div className="text-xs text-slate-400">{workspace.description}</div>
                  )}
                </div>
                <button
                  onClick={() => remove(workspace.id)}
                  className="rounded-lg p-2 text-slate-400 hover:bg-red-500/10 hover:text-red-300"
                >
                  <Trash2 size={16} />
                </button>
              </li>
            ))}
          </ul>
        )}
      </div>
    </div>
  )
}
