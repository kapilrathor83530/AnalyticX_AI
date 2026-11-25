import { RefreshCw } from 'lucide-react'
import { useLLM } from '../hooks/useLLM'

export default function ModelManagementPage() {
  const { status, loading, refresh } = useLLM()

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-semibold">LLM & Model Management</h1>
          <p className="text-sm text-slate-400">
            Local inference runtime status. The analytics engine works without the LLM.
          </p>
        </div>
        <button
          onClick={refresh}
          className="inline-flex items-center gap-2 rounded-xl border border-slate-700 px-4 py-2 text-sm text-slate-200 hover:border-cyan-400/50"
        >
          <RefreshCw size={14} />
          Refresh
        </button>
      </div>

      {loading || !status ? (
        <div className="text-slate-400">Loading model status...</div>
      ) : (
        <div className="glass space-y-4 rounded-3xl p-6">
          <div className="grid grid-cols-2 gap-4">
            <div>
              <div className="text-xs uppercase text-slate-400">Runtime</div>
              <div className={status.available ? 'text-emerald-300' : 'text-red-300'}>
                {status.available ? 'Available' : 'Unavailable'}
              </div>
            </div>
            <div>
              <div className="text-xs uppercase text-slate-400">Active Model</div>
              <div className="text-slate-100">{status.active_model}</div>
            </div>
            <div>
              <div className="text-xs uppercase text-slate-400">Active Model Installed</div>
              <div className={status.active_model_installed ? 'text-emerald-300' : 'text-amber-300'}>
                {status.active_model_installed ? 'Yes' : 'No'}
              </div>
            </div>
          </div>

          {status.error && (
            <div className="rounded-xl border border-red-500/30 bg-red-500/10 p-3 text-sm text-red-200">
              {status.error}
            </div>
          )}

          <div>
            <div className="mb-2 text-xs uppercase text-slate-400">Installed Models</div>
            {status.installed_models.length === 0 ? (
              <div className="text-sm text-slate-500">No models installed.</div>
            ) : (
              <ul className="space-y-1 text-sm">
                {status.installed_models.map((model) => (
                  <li key={model.name} className="rounded-lg border border-slate-800 bg-slate-900/40 px-3 py-2">
                    {model.name}
                  </li>
                ))}
              </ul>
            )}
          </div>

          <div className="rounded-xl border border-slate-800 bg-slate-900/40 p-4 text-xs text-slate-400">
            <p className="mb-2 text-slate-300">Setup commands (Windows PowerShell):</p>
            <pre className="whitespace-pre-wrap text-cyan-300">
{`# Install Ollama from https://ollama.com
ollama pull qwen2.5:3b-instruct-q4_K_M
ollama serve
# Then set DEFAULT_MODEL=qwen2.5:3b-instruct-q4_K_M in backend .env`}
            </pre>
          </div>
        </div>
      )}
    </div>
  )
}
