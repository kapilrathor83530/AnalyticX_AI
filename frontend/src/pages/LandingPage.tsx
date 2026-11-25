import {
  ArrowRight,
  BarChart3,
  Brain,
  Code2,
  Database,
  FileCheck,
  FileSpreadsheet,
  LogIn,
  Presentation,
  Sparkles,
  TrendingDown,
  TrendingUp,
  UserPlus,
  Wand2,
} from 'lucide-react'
import { Link } from 'react-router-dom'
import LazyScene from '../components/three/LazyScene'
import { useAppMode } from '../contexts/ModeContext'

const modes = [
  {
    mode: 'basic' as const,
    badge: 'Basic Mode',
    badgeClass: 'border-emerald-500/30 bg-emerald-500/10 text-emerald-300',
    title: 'Data Cleaning & Preprocessing',
    goal: 'Turn messy raw data into clean, analysis-ready data.',
    points: [
      'Upload CSV and Excel (.xlsx, .xls) files',
      'Detect missing values, duplicates & inconsistent data types',
      'Impute nulls (mean, median, mode, constant, ffill/bfill)',
      'Detect outliers and normalize text/formatting',
      'Rename columns, convert types & remove unwanted fields',
      'Live before-and-after quality statistics & preview',
      'Download cleaned CSV and preprocessing quality report',
    ],
    example: 'Output: cleaned_sales_data.csv + data quality report',
    link: '/workspace',
    linkText: 'Start Basic Cleaning',
    btnClass: 'bg-emerald-400 text-slate-950 hover:bg-emerald-300',
  },
  {
    mode: 'pro' as const,
    badge: 'Pro Mode',
    badgeClass: 'border-cyan-500/30 bg-cyan-500/10 text-cyan-300',
    title: 'EDA & Visualization Studio',
    goal: 'In-depth exploratory analysis, visual charts, and live SQL.',
    points: [
      'Create bar, line, histogram, box plot & scatter charts',
      'Generate correlation matrices and distribution heatmaps',
      'Group & compare performance across categories and regions',
      'Perform trend analysis and segment comparisons',
      'Customize chart axes, dimensions, and color palettes',
      'Execute sandboxed SQL queries in in-memory SQLite sandbox',
      'Export interactive decision dashboards & charts',
    ],
    example: 'Output: Interactive sales, profit & regional performance dashboard',
    link: '/workspace',
    linkText: 'Explore & Visualize',
    btnClass: 'bg-cyan-400 text-slate-950 hover:bg-cyan-300',
  },
  {
    mode: 'advanced' as const,
    badge: 'Advanced Mode',
    badgeClass: 'border-purple-500/30 bg-purple-500/10 text-purple-300',
    title: 'Project Insights & Executive BI',
    goal: 'Context-aware project insights, automated EDA, ANOVA tests, and board reports.',
    points: [
      'Project Insights Workspace: proactive AI intelligence without manual prompting',
      'Executive Summary: verified KPIs, opportunities, risks & limitations',
      'Automated EDA: transparent data quality scoring, schema & correlations',
      'Advanced Business Insights: mathematically grounded evidence & confidence',
      'AI Analyst Chat: grounded Q&A citing exact dataset metrics',
      'ANOVA Hypothesis Testing & Z-Score statistical anomaly scanning',
      'Multi-Format Executive Decks: downloadable in PDF, Word (.docx) & PowerPoint (.pptx)',
      'Public Sharable Web Links: passwordless briefing links for board review',
    ],
    example: 'Output: Executive briefing report with ANOVA tests, verified findings & action plans',
    link: '/insights/1',
    linkText: 'Open Project Insights',
    btnClass: 'bg-purple-500 text-white hover:bg-purple-400',
  },
]

export default function LandingPage() {
  const { setMode } = useAppMode()

  return (
    <div className="space-y-16">
      {/* Hero Section */}
      <section className="grid gap-8 lg:grid-cols-2 lg:items-center">
        <div className="space-y-6">
          <div className="inline-flex items-center gap-2 rounded-full border border-cyan-400/30 bg-cyan-400/5 px-3 py-1 text-xs text-cyan-200">
            <Sparkles size={14} />
            Three Purpose-Built Modes · Enterprise Platform
          </div>
          <h1 className="text-5xl font-semibold leading-tight">
            Turn raw business data into <span className="text-cyan-300">verified executive decisions</span>.
          </h1>
          <p className="text-slate-300 leading-relaxed">
            Analyticx AI organizes your end-to-end data journey across <strong>Basic</strong> (Data Cleaning), <strong>Pro</strong> (Exploratory Data Analysis, Dashboards & SQL), and <strong>Advanced</strong> (Root-Cause Analysis, Predictive Forecasting & Scheduled Automation) modes.
          </p>
          <div className="flex flex-wrap items-center gap-3">
            <Link
              to="/workspace"
              className="inline-flex items-center gap-2 rounded-2xl bg-cyan-400 px-5 py-3 text-sm font-semibold text-slate-950 hover:bg-cyan-300 transition shadow-lg shadow-cyan-950/40"
            >
              Open Workspace
              <ArrowRight size={16} />
            </Link>
            <Link
              to="/register"
              className="inline-flex items-center gap-2 rounded-2xl border border-cyan-400/40 bg-cyan-950/30 px-5 py-3 text-sm font-semibold text-cyan-300 hover:bg-cyan-900/40 transition"
            >
              <UserPlus size={16} />
              Sign Up Free
            </Link>
            <Link
              to="/login"
              className="inline-flex items-center gap-2 rounded-2xl border border-slate-700 bg-slate-900/60 px-5 py-3 text-sm font-medium text-slate-200 hover:border-cyan-400/50 hover:text-cyan-200 transition"
            >
              <LogIn size={16} />
              Sign In
            </Link>
          </div>
        </div>
        <div className="h-[380px]">
          <LazyScene />
        </div>
      </section>

      {/* Three Modes Showcase */}
      <section className="space-y-6">
        <div>
          <h2 className="text-3xl font-bold tracking-tight text-slate-100">Three Modes Architecture</h2>
          <p className="text-sm text-slate-400 mt-1">
            Tailored workflows for data preparers, business analysts, and executive decision-makers.
          </p>
        </div>

        <div className="grid gap-6 lg:grid-cols-3">
          {modes.map((m) => (
            <div
              key={m.mode}
              className="glass rounded-3xl p-6 flex flex-col justify-between space-y-6 hover:border-slate-700 transition"
            >
              <div className="space-y-4">
                <div className="flex items-center justify-between">
                  <span className={`rounded-full border px-2.5 py-0.5 text-xs font-semibold ${m.badgeClass}`}>
                    {m.badge}
                  </span>
                </div>
                <div>
                  <h3 className="text-xl font-bold text-slate-100">{m.title}</h3>
                  <p className="text-xs text-slate-300 mt-1 font-medium">{m.goal}</p>
                </div>

                <ul className="space-y-2 text-xs text-slate-400 border-t border-slate-800/80 pt-4">
                  {m.points.map((pt, i) => (
                    <li key={i} className="flex items-start gap-2">
                      <span className="text-cyan-400 font-bold">•</span>
                      <span>{pt}</span>
                    </li>
                  ))}
                </ul>
              </div>

              <div className="space-y-3 pt-3 border-t border-slate-800/80">
                <p className="text-[11px] font-mono text-cyan-200/80 bg-slate-900/80 p-2 rounded-xl border border-slate-800">
                  {m.example}
                </p>
                <Link
                  to={m.link}
                  onClick={() => setMode(m.mode)}
                  className={`w-full inline-flex items-center justify-center gap-2 rounded-xl py-2.5 text-xs font-semibold transition shadow-md ${m.btnClass}`}
                >
                  {m.linkText}
                  <ArrowRight size={14} />
                </Link>
              </div>
            </div>
          ))}
        </div>
      </section>

      {/* Footer */}
      <footer className="border-t border-slate-800 pt-8 text-sm text-slate-500">
        Analyticx AI · Local-first, enterprise-grade business analytics platform with deterministic Python grounding.
      </footer>
    </div>
  )
}
