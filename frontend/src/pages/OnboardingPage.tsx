import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import {
  ArrowRight,
  BarChart3,
  Brain,
  CheckCircle2,
  ChevronRight,
  Database,
  GraduationCap,
  Languages,
  LayoutDashboard,
  Lightbulb,
  LineChart,
  Palette,
  ShieldAlert,
  Sparkles,
  TrendingUp,
  UserCheck,
  Wand2,
} from 'lucide-react'
import { useAuth } from '../contexts/AuthContext'
import { authService } from '../services/authService'

const ROLES = [
  { id: 'Data Analyst', label: 'Data Analyst', icon: BarChart3, desc: 'Exploratory data analysis, SQL queries, visualizations & reporting' },
  { id: 'Data Scientist / ML Engineer', label: 'Data Scientist / ML Engineer', icon: Brain, desc: 'Advanced predictive modeling, forecasting, stats & ML algorithms' },
  { id: 'Business Owner / Manager', label: 'Business Owner / Manager', icon: TrendingUp, desc: 'Executive summaries, high-level KPIs, bottom-line ROI & decision simulation' },
  { id: 'Student / Learner', label: 'Student / Learner', icon: GraduationCap, desc: 'Learning analytics, practicing statistical techniques & exploratory charts' },
  { id: 'Other', label: 'Other', icon: Sparkles, desc: 'General exploration and cross-functional operations' },
]

const GOALS = [
  { id: 'Automate exploratory data analysis', label: 'Automate Exploratory Data Analysis', icon: Sparkles },
  { id: 'Clean and prepare datasets', label: 'Clean & Preprocess Messy Data', icon: Wand2 },
  { id: 'Build interactive dashboards', label: 'Build Interactive Dashboards & Charts', icon: LayoutDashboard },
  { id: 'Discover business insights', label: 'Discover Empirical Business Insights', icon: Lightbulb },
  { id: 'Forecast future metrics', label: 'Forecast Time-Series Metrics', icon: LineChart },
  { id: 'Simulate business decisions', label: 'Simulate Business & Pricing Decisions', icon: Database },
  { id: 'Explore data using AI', label: 'Converse with AI Business Copilot', icon: Brain },
]

const LEVELS = [
  { id: 'Beginner', label: 'Beginner', desc: 'New to analytics. I prefer clear, plain English explanations and automated guidance.' },
  { id: 'Intermediate', label: 'Intermediate', desc: 'Familiar with data concepts, charts, and business metrics. I want balanced analysis.' },
  { id: 'Advanced', label: 'Advanced', desc: 'Data professional. Give me full statistical tests, p-values, correlations, and raw models.' },
]

export default function OnboardingPage() {
  const { user, setUser } = useAuth()
  const navigate = useNavigate()

  const [step, setStep] = useState(1)
  const [role, setRole] = useState(user?.role || 'Data Analyst')
  const [selectedGoals, setSelectedGoals] = useState<string[]>(
    user?.primary_goal?.length ? user.primary_goal : ['Automate exploratory data analysis', 'Discover business insights'],
  )
  const [experienceLevel, setExperienceLevel] = useState(user?.experience_level || 'Intermediate')

  // Step 5 Preferences
  const [theme, setTheme] = useState<'dark' | 'light'>('dark')
  const [language, setLanguage] = useState('en')
  const [explanationLevel, setExplanationLevel] = useState<'executive' | 'standard' | 'technical'>('standard')
  const [loading, setLoading] = useState(false)

  function toggleGoal(goalId: string) {
    setSelectedGoals((prev) =>
      prev.includes(goalId) ? prev.filter((g) => g !== goalId) : [...prev, goalId],
    )
  }

  async function handleComplete() {
    setLoading(true)
    try {
      const updatedUser = await authService.saveOnboarding({
        role,
        primary_goal: selectedGoals,
        experience_level: experienceLevel,
        preferences: {
          theme,
          language,
          explanation_level: explanationLevel,
          email_notifications: true,
        },
      })
      setUser(updatedUser)
      navigate('/workspace')
    } catch {
      navigate('/workspace')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="min-h-[85vh] flex flex-col justify-center items-center px-4 py-8 max-w-3xl mx-auto">
      {/* Progress Stepper */}
      <div className="w-full mb-8">
        <div className="flex items-center justify-between mb-3 text-xs font-semibold text-slate-400">
          <span>STEP {step} OF 5</span>
          <span className="text-cyan-400">Personalizing Your Analyticx AI Workspace</span>
        </div>
        <div className="flex gap-2">
          {[1, 2, 3, 4, 5].map((s) => (
            <div
              key={s}
              className={`h-1.5 flex-1 rounded-full transition-all duration-300 ${
                s <= step ? 'bg-cyan-400' : 'bg-slate-800'
              }`}
            />
          ))}
        </div>
      </div>

      {/* Main Card */}
      <div className="glass w-full rounded-3xl border border-slate-800 bg-slate-950/90 p-8 shadow-2xl backdrop-blur-2xl relative overflow-hidden">
        {/* Step 1: Welcome */}
        {step === 1 && (
          <div className="space-y-6 text-center py-6">
            <div className="inline-flex h-16 w-16 items-center justify-center rounded-3xl bg-gradient-to-tr from-cyan-400 to-blue-500 text-slate-950 shadow-xl shadow-cyan-500/20">
              <Sparkles size={32} />
            </div>
            <div className="space-y-2">
              <h2 className="text-3xl font-extrabold tracking-tight text-slate-100">
                Welcome to Analyticx AI{user?.full_name ? `, ${user.full_name}` : ''}!
              </h2>
              <p className="text-sm text-slate-300 max-w-lg mx-auto leading-relaxed">
                Your enterprise workspace is ready. In just a few moments, you will be able to clean data, build dashboards, discover hidden insights, and generate forecasts.
              </p>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-3 gap-3 pt-4 text-left">
              <div className="rounded-2xl border border-slate-800 bg-slate-900/60 p-4 space-y-1">
                <div className="text-cyan-400 font-bold text-xs uppercase tracking-wider">1. Prepare Data</div>
                <p className="text-xs text-slate-300">Automated cleaning, missing values, duplicates & outlier handling.</p>
              </div>
              <div className="rounded-2xl border border-slate-800 bg-slate-900/60 p-4 space-y-1">
                <div className="text-cyan-400 font-bold text-xs uppercase tracking-wider">2. Explore & Visualize</div>
                <p className="text-xs text-slate-300">Interactive dashboards, heatmaps, scatter plots & SQL queries.</p>
              </div>
              <div className="rounded-2xl border border-slate-800 bg-slate-900/60 p-4 space-y-1">
                <div className="text-cyan-400 font-bold text-xs uppercase tracking-wider">3. AI & Forecasting</div>
                <p className="text-xs text-slate-300">Predict future metrics, run scenarios & export executive PDF reports.</p>
              </div>
            </div>

            <div className="pt-6 flex justify-end">
              <button
                onClick={() => setStep(2)}
                className="rounded-xl bg-cyan-400 px-6 py-3 text-sm font-semibold text-slate-950 hover:bg-cyan-300 transition flex items-center gap-2"
              >
                <span>Let's Get Started</span>
                <ArrowRight size={16} />
              </button>
            </div>
          </div>
        )}

        {/* Step 2: Role */}
        {step === 2 && (
          <div className="space-y-6">
            <div>
              <div className="inline-flex items-center gap-2 text-xs font-semibold uppercase tracking-wider text-cyan-400 mb-1">
                <UserCheck size={14} />
                <span>Professional Role</span>
              </div>
              <h2 className="text-2xl font-bold text-slate-100">What best describes your primary role?</h2>
              <p className="text-xs text-slate-400 mt-1">This helps tailor AI recommendations and default analysis templates.</p>
            </div>

            <div className="space-y-2.5">
              {ROLES.map((r) => {
                const Icon = r.icon
                const isSelected = role === r.id
                return (
                  <div
                    key={r.id}
                    onClick={() => setRole(r.id)}
                    className={`cursor-pointer rounded-2xl border p-4 transition flex items-center gap-4 ${
                      isSelected
                        ? 'border-cyan-400 bg-cyan-950/30 text-slate-100'
                        : 'border-slate-800 bg-slate-900/40 text-slate-300 hover:border-slate-700 hover:bg-slate-900/70'
                    }`}
                  >
                    <div
                      className={`h-10 w-10 rounded-xl flex items-center justify-center shrink-0 ${
                        isSelected ? 'bg-cyan-400 text-slate-950' : 'bg-slate-800 text-slate-400'
                      }`}
                    >
                      <Icon size={20} />
                    </div>
                    <div className="flex-1">
                      <div className="font-semibold text-sm">{r.label}</div>
                      <div className="text-xs text-slate-400">{r.desc}</div>
                    </div>
                    {isSelected && <CheckCircle2 size={18} className="text-cyan-400" />}
                  </div>
                )
              })}
            </div>

            <div className="flex justify-between pt-4">
              <button
                onClick={() => setStep(1)}
                className="rounded-xl border border-slate-800 px-5 py-2.5 text-xs text-slate-400 hover:bg-slate-900"
              >
                Back
              </button>
              <button
                onClick={() => setStep(3)}
                className="rounded-xl bg-cyan-400 px-6 py-2.5 text-xs font-semibold text-slate-950 hover:bg-cyan-300 flex items-center gap-1.5"
              >
                <span>Continue</span>
                <ChevronRight size={16} />
              </button>
            </div>
          </div>
        )}

        {/* Step 3: Goals */}
        {step === 3 && (
          <div className="space-y-6">
            <div>
              <div className="inline-flex items-center gap-2 text-xs font-semibold uppercase tracking-wider text-cyan-400 mb-1">
                <Sparkles size={14} />
                <span>Primary Objectives</span>
              </div>
              <h2 className="text-2xl font-bold text-slate-100">What do you want to accomplish in Analyticx AI?</h2>
              <p className="text-xs text-slate-400 mt-1">Select all workflows that interest you (multiple selection supported).</p>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-2.5">
              {GOALS.map((g) => {
                const Icon = g.icon
                const isSelected = selectedGoals.includes(g.id)
                return (
                  <div
                    key={g.id}
                    onClick={() => toggleGoal(g.id)}
                    className={`cursor-pointer rounded-2xl border p-3.5 transition flex items-center gap-3 ${
                      isSelected
                        ? 'border-cyan-400 bg-cyan-950/30 text-slate-100'
                        : 'border-slate-800 bg-slate-900/40 text-slate-300 hover:border-slate-700 hover:bg-slate-900/70'
                    }`}
                  >
                    <div
                      className={`h-8 w-8 rounded-lg flex items-center justify-center shrink-0 ${
                        isSelected ? 'bg-cyan-400 text-slate-950' : 'bg-slate-800 text-slate-400'
                      }`}
                    >
                      <Icon size={16} />
                    </div>
                    <span className="text-xs font-medium flex-1">{g.label}</span>
                    {isSelected && <CheckCircle2 size={16} className="text-cyan-400 shrink-0" />}
                  </div>
                )
              })}
            </div>

            <div className="flex justify-between pt-4">
              <button
                onClick={() => setStep(2)}
                className="rounded-xl border border-slate-800 px-5 py-2.5 text-xs text-slate-400 hover:bg-slate-900"
              >
                Back
              </button>
              <button
                onClick={() => setStep(4)}
                disabled={selectedGoals.length === 0}
                className="rounded-xl bg-cyan-400 px-6 py-2.5 text-xs font-semibold text-slate-950 hover:bg-cyan-300 disabled:opacity-50 flex items-center gap-1.5"
              >
                <span>Continue</span>
                <ChevronRight size={16} />
              </button>
            </div>
          </div>
        )}

        {/* Step 4: Experience Level */}
        {step === 4 && (
          <div className="space-y-6">
            <div>
              <div className="inline-flex items-center gap-2 text-xs font-semibold uppercase tracking-wider text-cyan-400 mb-1">
                <Brain size={14} />
                <span>Expertise</span>
              </div>
              <h2 className="text-2xl font-bold text-slate-100">What is your analytics experience level?</h2>
              <p className="text-xs text-slate-400 mt-1">We adjust the level of statistical detail in our automated narratives.</p>
            </div>

            <div className="space-y-3">
              {LEVELS.map((l) => {
                const isSelected = experienceLevel === l.id
                return (
                  <div
                    key={l.id}
                    onClick={() => setExperienceLevel(l.id)}
                    className={`cursor-pointer rounded-2xl border p-4 transition flex items-center justify-between ${
                      isSelected
                        ? 'border-cyan-400 bg-cyan-950/30 text-slate-100'
                        : 'border-slate-800 bg-slate-900/40 text-slate-300 hover:border-slate-700 hover:bg-slate-900/70'
                    }`}
                  >
                    <div>
                      <div className="font-semibold text-sm">{l.label}</div>
                      <div className="text-xs text-slate-400 mt-0.5">{l.desc}</div>
                    </div>
                    {isSelected && <CheckCircle2 size={18} className="text-cyan-400 shrink-0" />}
                  </div>
                )
              })}
            </div>

            <div className="flex justify-between pt-4">
              <button
                onClick={() => setStep(3)}
                className="rounded-xl border border-slate-800 px-5 py-2.5 text-xs text-slate-400 hover:bg-slate-900"
              >
                Back
              </button>
              <button
                onClick={() => setStep(5)}
                className="rounded-xl bg-cyan-400 px-6 py-2.5 text-xs font-semibold text-slate-950 hover:bg-cyan-300 flex items-center gap-1.5"
              >
                <span>Preferences</span>
                <ChevronRight size={16} />
              </button>
            </div>
          </div>
        )}

        {/* Step 5: Optional Preferences */}
        {step === 5 && (
          <div className="space-y-6">
            <div>
              <div className="inline-flex items-center gap-2 text-xs font-semibold uppercase tracking-wider text-cyan-400 mb-1">
                <Palette size={14} />
                <span>Display & Tone</span>
              </div>
              <h2 className="text-2xl font-bold text-slate-100">Customize Your Workspace Experience</h2>
              <p className="text-xs text-slate-400 mt-1">These settings can always be modified in Account Settings.</p>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {/* Theme */}
              <div className="rounded-2xl border border-slate-800 bg-slate-900/50 p-4 space-y-2">
                <label className="text-xs font-semibold text-slate-300 flex items-center gap-2">
                  <Palette size={14} className="text-cyan-400" />
                  <span>Theme Preference</span>
                </label>
                <div className="grid grid-cols-2 gap-2 pt-1">
                  <button
                    type="button"
                    onClick={() => setTheme('dark')}
                    className={`rounded-xl py-2 text-xs font-medium border transition ${
                      theme === 'dark' ? 'border-cyan-400 bg-cyan-950/40 text-cyan-200' : 'border-slate-800 text-slate-400'
                    }`}
                  >
                    Dark (Obsidian)
                  </button>
                  <button
                    type="button"
                    onClick={() => setTheme('light')}
                    className={`rounded-xl py-2 text-xs font-medium border transition ${
                      theme === 'light' ? 'border-cyan-400 bg-cyan-950/40 text-cyan-200' : 'border-slate-800 text-slate-400'
                    }`}
                  >
                    Light (Daylight)
                  </button>
                </div>
              </div>

              {/* Language */}
              <div className="rounded-2xl border border-slate-800 bg-slate-900/50 p-4 space-y-2">
                <label className="text-xs font-semibold text-slate-300 flex items-center gap-2">
                  <Languages size={14} className="text-cyan-400" />
                  <span>Default Language</span>
                </label>
                <select
                  value={language}
                  onChange={(e) => setLanguage(e.target.value)}
                  className="w-full rounded-xl border border-slate-700 bg-slate-900 px-3 py-2 text-xs text-slate-200 outline-none focus:border-cyan-400"
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

              {/* Explanation Level */}
              <div className="col-span-1 md:col-span-2 rounded-2xl border border-slate-800 bg-slate-900/50 p-4 space-y-2">
                <label className="text-xs font-semibold text-slate-300 flex items-center gap-2">
                  <Brain size={14} className="text-cyan-400" />
                  <span>AI Copilot Explanation Tone</span>
                </label>
                <div className="grid grid-cols-1 sm:grid-cols-3 gap-2 pt-1">
                  {[
                    { id: 'executive', label: 'Executive', desc: 'Bottom-line ROI & bullet points' },
                    { id: 'standard', label: 'Standard', desc: 'Balanced business intelligence' },
                    { id: 'technical', label: 'Technical', desc: 'In-depth stats & p-values' },
                  ].map((lvl) => (
                    <button
                      key={lvl.id}
                      type="button"
                      onClick={() => setExplanationLevel(lvl.id as any)}
                      className={`rounded-xl p-2.5 text-left border transition ${
                        explanationLevel === lvl.id
                          ? 'border-cyan-400 bg-cyan-950/40 text-slate-100'
                          : 'border-slate-800 text-slate-400 hover:bg-slate-900'
                      }`}
                    >
                      <div className="text-xs font-semibold text-slate-200">{lvl.label}</div>
                      <div className="text-[10px] text-slate-400 mt-0.5">{lvl.desc}</div>
                    </button>
                  ))}
                </div>
              </div>
            </div>

            <div className="flex justify-between items-center pt-4">
              <button
                type="button"
                onClick={handleComplete}
                className="text-xs text-slate-400 hover:text-slate-200 underline"
              >
                Skip for now
              </button>
              <div className="flex gap-2">
                <button
                  type="button"
                  onClick={() => setStep(4)}
                  className="rounded-xl border border-slate-800 px-5 py-2.5 text-xs text-slate-400 hover:bg-slate-900"
                >
                  Back
                </button>
                <button
                  type="button"
                  onClick={handleComplete}
                  disabled={loading}
                  className="rounded-xl bg-gradient-to-r from-cyan-400 to-blue-500 px-6 py-2.5 text-xs font-bold text-slate-950 hover:from-cyan-300 hover:to-blue-400 shadow-lg shadow-cyan-500/20 disabled:opacity-50 flex items-center gap-2"
                >
                  {loading ? 'Activating Workspace...' : 'Complete Workspace Setup'}
                  <Sparkles size={14} />
                </button>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
