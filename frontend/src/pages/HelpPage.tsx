export default function HelpPage() {
  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-semibold">Help & Documentation</h1>

      <section className="glass rounded-3xl p-6">
        <h2 className="mb-3 text-lg font-semibold">Getting started</h2>
        <ol className="list-decimal space-y-2 pl-5 text-sm text-slate-300">
          <li>Open Workspace and upload a CSV or Excel file.</li>
          <li>Inspect columns, missing values, and preview rows.</li>
          <li>Run Analytics for KPI, trends, and correlations.</li>
          <li>Use Studio to design a chart, then Save to Dashboard.</li>
          <li>Open the Dashboard editor to arrange charts and add filters.</li>
          <li>Ask questions in AI Analyst. Enable the local LLM in Model Management.</li>
          <li>Forecast a time series in the Forecasting Center.</li>
          <li>Explore price/cost scenarios in the Simulator.</li>
        </ol>
      </section>

      <section className="glass rounded-3xl p-6">
        <h2 className="mb-3 text-lg font-semibold">Local LLM setup</h2>
        <pre className="whitespace-pre-wrap rounded-xl border border-slate-800 bg-slate-900/40 p-4 text-xs text-cyan-300">
{`# Install Ollama (https://ollama.com)
ollama pull qwen2.5:3b-instruct-q4_K_M
ollama serve
# Set DEFAULT_MODEL in backend .env if you used a different tag.`}
        </pre>
      </section>

      <section className="glass rounded-3xl p-6">
        <h2 className="mb-3 text-lg font-semibold">Keyboard & shortcuts</h2>
        <ul className="list-disc space-y-1 pl-5 text-sm text-slate-300">
          <li>Enter in the command bar → run</li>
          <li>Undo / Redo icons in dashboard editor</li>
          <li>Drag dashboard widget header to move; corner to resize</li>
        </ul>
      </section>

      <section className="glass rounded-3xl p-6">
        <h2 className="mb-3 text-lg font-semibold">Known limitations</h2>
        <ul className="list-disc space-y-1 pl-5 text-sm text-slate-300">
          <li>Fine-tuning requires Colab or a GPU machine.</li>
          <li>Some advanced charts show a "not yet rendered" message.</li>
          <li>PDF reports are basic; charts are embedded as PNG images.</li>
          <li>Cross-filtering applies equality filters only.</li>
        </ul>
      </section>
    </div>
  )
}
