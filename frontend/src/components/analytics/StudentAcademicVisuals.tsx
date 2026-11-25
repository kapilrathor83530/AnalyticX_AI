import {
  Award,
  BarChart3,
  BookOpen,
  CheckCircle2,
  ChevronDown,
  ChevronUp,
  Database,
  ExternalLink,
  GraduationCap,
  Info,
  Lightbulb,
  LineChart,
  Search,
  Sparkles,
  Star,
  TrendingUp,
  Trophy,
  Users,
  XCircle,
} from 'lucide-react'
import { useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import { COHORT_STATS, STUDENT_RESULTS, type StudentResult } from '../../data/studentAnalytics'

interface Props {
  datasetId?: number
  onClose?: () => void
}

export default function StudentAcademicVisuals({ datasetId = 505, onClose }: Props) {
  const [searchQuery, setSearchQuery] = useState('')
  const [tierFilter, setTierFilter] = useState('ALL')
  const [selectedStudent, setSelectedStudent] = useState<StudentResult | null>(null)
  const [activeTab, setActiveTab] = useState<'overview' | 'subjects' | 'toppers' | 'students'>('overview')

  // Filter students based on search and selected tier
  const filteredStudents = useMemo(() => {
    return STUDENT_RESULTS.filter((student) => {
      const matchesSearch =
        student.Student_Name.toLowerCase().includes(searchQuery.toLowerCase()) ||
        student.Roll_Number.toLowerCase().includes(searchQuery.toLowerCase())

      if (!matchesSearch) return false

      if (tierFilter === 'ALL') return true
      if (tierFilter === 'OUTSTANDING') return (student.SGPA || 0) >= 9.0
      if (tierFilter === 'DISTINCTION') return (student.SGPA || 0) >= 8.5 && (student.SGPA || 0) < 9.0
      if (tierFilter === 'FIRST_CLASS') return (student.SGPA || 0) >= 8.0 && (student.SGPA || 0) < 8.5
      if (tierFilter === 'BACKLOG') return student.Result_Status !== 'Pass'
      return true
    })
  }, [searchQuery, tierFilter])

  const top10Students = useMemo(() => {
    return [...STUDENT_RESULTS]
      .filter((s) => s.SGPA !== null)
      .sort((a, b) => (b.SGPA || 0) - (a.SGPA || 0))
      .slice(0, 10)
  }, [])

  return (
    <div className="space-y-6">
      {/* 1. HERO BANNER */}
      <div className="relative overflow-hidden rounded-3xl border border-cyan-500/30 bg-gradient-to-br from-slate-950 via-slate-900 to-cyan-950/40 p-6 md:p-8 shadow-2xl">
        <div className="absolute top-0 right-0 h-96 w-96 rounded-full bg-cyan-500/10 blur-3xl pointer-events-none" />
        <div className="absolute -bottom-10 -left-10 h-72 w-72 rounded-full bg-blue-500/10 blur-3xl pointer-events-none" />

        <div className="relative z-10 flex flex-col lg:flex-row lg:items-center justify-between gap-6">
          <div className="space-y-2">
            <div className="flex flex-wrap items-center gap-2">
              <span className="inline-flex items-center gap-1.5 rounded-full bg-cyan-400/15 border border-cyan-400/30 px-3 py-1 text-xs font-bold text-cyan-300">
                <GraduationCap size={14} /> B.Tech Computer Engineering (AI/ML)
              </span>
              <span className="rounded-full bg-slate-800/80 border border-slate-700/80 px-2.5 py-1 text-xs font-medium text-slate-300">
                Sixth Semester (Regular) · June-2026
              </span>
              <span className="inline-flex items-center gap-1 rounded-full bg-emerald-500/15 border border-emerald-500/30 px-2.5 py-1 text-xs font-semibold text-emerald-400">
                <CheckCircle2 size={13} /> {COHORT_STATS.passRate}% Pass Rate
              </span>
            </div>

            <h1 className="text-2xl sm:text-3xl font-extrabold tracking-tight text-white flex items-center gap-3">
              Student Examination & Academic Intelligence
            </h1>
            <p className="text-xs sm:text-sm text-slate-400 max-w-2xl leading-relaxed">
              Real-time analytics for 68 students across 7 core subjects. SGPA distribution, subject difficulty benchmarks,
              toppers leaderboard, and personalized cohort ranking.
            </p>
          </div>

          {/* Quick Studio Nav Actions */}
          <div className="flex flex-wrap items-center gap-2 shrink-0">
            <Link
              to={`/studio/${datasetId}`}
              className="inline-flex items-center gap-1.5 rounded-xl bg-cyan-400 px-3.5 py-2 text-xs font-bold text-slate-950 hover:bg-cyan-300 transition shadow-lg shadow-cyan-950/40"
            >
              <LineChart size={14} />
              <span>Visual Studio</span>
            </Link>
            <Link
              to={`/insights/${datasetId}`}
              className="inline-flex items-center gap-1.5 rounded-xl border border-slate-700 bg-slate-900/90 px-3.5 py-2 text-xs font-semibold text-purple-300 hover:border-purple-400/50 hover:text-purple-200 transition"
            >
              <Lightbulb size={14} />
              <span>Project Insights</span>
            </Link>
            <Link
              to={`/datasets/${datasetId}`}
              className="inline-flex items-center gap-1.5 rounded-xl border border-slate-700 bg-slate-900/90 px-3.5 py-2 text-xs font-semibold text-slate-300 hover:border-slate-600 hover:text-white transition"
            >
              <Database size={14} />
              <span>Raw Explorer</span>
            </Link>
          </div>
        </div>

        {/* Navigation Tabs */}
        <div className="flex flex-wrap items-center gap-2 mt-6 pt-5 border-t border-slate-800/80">
          <button
            onClick={() => setActiveTab('overview')}
            className={`px-3.5 py-1.5 rounded-xl text-xs font-semibold transition ${
              activeTab === 'overview'
                ? 'bg-cyan-400 text-slate-950 shadow-sm'
                : 'bg-slate-900/80 text-slate-300 hover:bg-slate-800'
            }`}
          >
            📊 Executive Overview
          </button>
          <button
            onClick={() => setActiveTab('subjects')}
            className={`px-3.5 py-1.5 rounded-xl text-xs font-semibold transition ${
              activeTab === 'subjects'
                ? 'bg-cyan-400 text-slate-950 shadow-sm'
                : 'bg-slate-900/80 text-slate-300 hover:bg-slate-800'
            }`}
          >
            📚 Subject Benchmarks
          </button>
          <button
            onClick={() => setActiveTab('toppers')}
            className={`px-3.5 py-1.5 rounded-xl text-xs font-semibold transition ${
              activeTab === 'toppers'
                ? 'bg-cyan-400 text-slate-950 shadow-sm'
                : 'bg-slate-900/80 text-slate-300 hover:bg-slate-800'
            }`}
          >
            🏆 Top 10 Leaderboard
          </button>
          <button
            onClick={() => setActiveTab('students')}
            className={`px-3.5 py-1.5 rounded-xl text-xs font-semibold transition ${
              activeTab === 'students'
                ? 'bg-cyan-400 text-slate-950 shadow-sm'
                : 'bg-slate-900/80 text-slate-300 hover:bg-slate-800'
            }`}
          >
            🔍 All 68 Students Search
          </button>
        </div>
      </div>

      {/* 2. EXECUTIVE KPI CARDS */}
      <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-3.5">
        {/* Cohort Size */}
        <div className="glass rounded-2xl border border-slate-800 bg-slate-950/70 p-4 space-y-1">
          <div className="flex items-center justify-between text-slate-400">
            <span className="text-[11px] font-semibold uppercase tracking-wider">Cohort Size</span>
            <Users size={16} className="text-cyan-400" />
          </div>
          <div className="text-2xl font-black text-slate-100">{COHORT_STATS.totalStudents}</div>
          <div className="text-[11px] text-cyan-400/90 font-medium">100% Evaluated</div>
        </div>

        {/* Overall Pass Rate */}
        <div className="glass rounded-2xl border border-emerald-500/30 bg-emerald-950/15 p-4 space-y-1">
          <div className="flex items-center justify-between text-emerald-400">
            <span className="text-[11px] font-semibold uppercase tracking-wider">Pass Rate</span>
            <CheckCircle2 size={16} className="text-emerald-400" />
          </div>
          <div className="text-2xl font-black text-emerald-300">{COHORT_STATS.passRate}%</div>
          <div className="text-[11px] text-emerald-400/90 font-medium">{COHORT_STATS.passCount} of 68 Cleared</div>
        </div>

        {/* Cohort Mean SGPA */}
        <div className="glass rounded-2xl border border-slate-800 bg-slate-950/70 p-4 space-y-1">
          <div className="flex items-center justify-between text-slate-400">
            <span className="text-[11px] font-semibold uppercase tracking-wider">Mean SGPA</span>
            <TrendingUp size={16} className="text-blue-400" />
          </div>
          <div className="text-2xl font-black text-slate-100">{COHORT_STATS.averageSgpa}</div>
          <div className="text-[11px] text-slate-400 font-medium">Median: {COHORT_STATS.medianSgpa}</div>
        </div>

        {/* Distinction Rate */}
        <div className="glass rounded-2xl border border-slate-800 bg-slate-950/70 p-4 space-y-1">
          <div className="flex items-center justify-between text-slate-400">
            <span className="text-[11px] font-semibold uppercase tracking-wider">Distinction+</span>
            <Award size={16} className="text-amber-400" />
          </div>
          <div className="text-2xl font-black text-amber-300">{COHORT_STATS.distinctionRate}%</div>
          <div className="text-[11px] text-slate-400 font-medium">{COHORT_STATS.distinctionCount} Students ≥ 8.5</div>
        </div>

        {/* Batch Topper */}
        <div className="glass rounded-2xl border border-amber-500/30 bg-amber-950/15 p-4 space-y-1">
          <div className="flex items-center justify-between text-amber-400">
            <span className="text-[11px] font-semibold uppercase tracking-wider">Cohort Rank #1</span>
            <Trophy size={16} className="text-amber-400" />
          </div>
          <div className="text-xl font-black text-amber-200 truncate">{COHORT_STATS.topper.name}</div>
          <div className="text-[11px] text-amber-300/90 font-bold">{COHORT_STATS.topper.sgpa} SGPA</div>
        </div>

        {/* Your Profile Card: Kapil */}
        <div className="glass rounded-2xl border border-cyan-400/50 bg-gradient-to-br from-cyan-950/40 via-slate-900 to-slate-950 p-4 space-y-1 shadow-lg shadow-cyan-950/50">
          <div className="flex items-center justify-between text-cyan-300">
            <span className="text-[11px] font-bold uppercase tracking-wider flex items-center gap-1">
              <Star size={12} className="fill-cyan-400 text-cyan-400" /> Kapil (You)
            </span>
            <span className="rounded-full bg-cyan-400/20 px-1.5 py-0.2 text-[9px] font-bold text-cyan-300">
              Rank #{COHORT_STATS.kapil.rank}
            </span>
          </div>
          <div className="text-2xl font-black text-cyan-300">{COHORT_STATS.kapil.sgpa}</div>
          <div className="text-[11px] text-cyan-200/80 font-medium">Top 16% · Distinction</div>
        </div>
      </div>

      {/* 3. CONDITIONAL TAB VIEWS */}
      {activeTab === 'overview' && (
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
          {/* Chart 1: Grade Tier Distribution (7 cols) */}
          <div className="lg:col-span-7 glass rounded-3xl border border-slate-800 bg-slate-950/70 p-6 space-y-5">
            <div className="flex items-center justify-between">
              <div>
                <h3 className="text-base font-bold text-slate-100 flex items-center gap-2">
                  <BarChart3 size={18} className="text-cyan-400" />
                  Cohort Grade Tier Distribution
                </h3>
                <p className="text-xs text-slate-400 mt-0.5">
                  Breakdown of all 68 students grouped by academic performance tier.
                </p>
              </div>
              <span className="rounded-full bg-slate-800 px-2.5 py-1 text-[11px] font-semibold text-slate-300">
                68 Students Total
              </span>
            </div>

            {/* Visual Bar Distribution */}
            <div className="space-y-3.5">
              {COHORT_STATS.tierDistribution.map((tier) => (
                <div key={tier.label} className="space-y-1.5">
                  <div className="flex items-center justify-between text-xs">
                    <span className="font-semibold text-slate-200">{tier.label}</span>
                    <div className="flex items-center gap-2">
                      <span className="font-bold text-slate-100">{tier.count} students</span>
                      <span className="text-slate-400 text-[11px]">({tier.percentage}%)</span>
                    </div>
                  </div>
                  {/* Progress track */}
                  <div className="h-3 w-full rounded-full bg-slate-900 border border-slate-800/80 overflow-hidden relative">
                    <div
                      className="h-full rounded-full transition-all duration-700 relative"
                      style={{
                        width: `${Math.max(tier.percentage * 2.5, 4)}%`,
                        backgroundColor: tier.color,
                      }}
                    >
                      {/* Shine effect */}
                      <div className="absolute inset-0 bg-gradient-to-r from-transparent via-white/20 to-transparent" />
                    </div>
                  </div>
                </div>
              ))}
            </div>

            {/* Mini Summary Footnote */}
            <div className="pt-3 border-t border-slate-800/60 flex items-center justify-between text-xs text-slate-400">
              <span className="flex items-center gap-1.5">
                <Info size={13} className="text-cyan-400" />
                40% of cohort achieved Distinction or Outstanding (SGPA ≥ 8.5)
              </span>
              <span className="text-emerald-400 font-semibold">63 Pass · 4 Reappear · 1 UMC</span>
            </div>
          </div>

          {/* Chart 2: Kapil's Score Breakdown & Cohort Status (5 cols) */}
          <div className="lg:col-span-5 space-y-6">
            {/* Kapil's Spotlight Card */}
            <div className="glass rounded-3xl border border-cyan-500/40 bg-gradient-to-br from-cyan-950/30 via-slate-900 to-slate-950 p-6 space-y-4 shadow-xl">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2.5">
                  <div className="h-10 w-10 rounded-2xl bg-cyan-400 text-slate-950 font-black text-lg flex items-center justify-center shadow-md">
                    K
                  </div>
                  <div>
                    <h4 className="font-extrabold text-sm text-slate-100">
                      Kapil — Student Analytics Profile
                    </h4>
                    <p className="text-[11px] text-slate-400 font-mono">Roll: 23UGBCE09130</p>
                  </div>
                </div>
                <div className="text-right">
                  <div className="text-xl font-black text-cyan-300">8.91 SGPA</div>
                  <div className="text-[10px] font-bold text-emerald-400 uppercase">Rank #11 in Cohort</div>
                </div>
              </div>

              {/* Subject Breakdown for Kapil */}
              <div className="grid grid-cols-2 gap-2 text-xs">
                <div className="rounded-xl border border-slate-800 bg-slate-900/70 p-2.5">
                  <div className="text-[10px] text-slate-400">Computer Networks</div>
                  <div className="text-sm font-bold text-emerald-300">89 / 100 (A+)</div>
                </div>
                <div className="rounded-xl border border-slate-800 bg-slate-900/70 p-2.5">
                  <div className="text-[10px] text-slate-400">Capstone Project</div>
                  <div className="text-sm font-bold text-emerald-300">89 / 100 (A+)</div>
                </div>
                <div className="rounded-xl border border-slate-800 bg-slate-900/70 p-2.5">
                  <div className="text-[10px] text-slate-400">Compiler Design</div>
                  <div className="text-sm font-bold text-cyan-300">84 / 100 (A)</div>
                </div>
                <div className="rounded-xl border border-slate-800 bg-slate-900/70 p-2.5">
                  <div className="text-[10px] text-slate-400">Data Analytics (ME3)</div>
                  <div className="text-sm font-bold text-cyan-300">84 / 100 (A)</div>
                </div>
                <div className="rounded-xl border border-slate-800 bg-slate-900/70 p-2.5">
                  <div className="text-[10px] text-slate-400">Security & Mining (ME4)</div>
                  <div className="text-sm font-bold text-cyan-300">84 / 100 (A)</div>
                </div>
                <div className="rounded-xl border border-slate-800 bg-slate-900/70 p-2.5">
                  <div className="text-[10px] text-slate-400">Management & OB</div>
                  <div className="text-sm font-bold text-amber-300">63 / 100 (B+)</div>
                </div>
              </div>

              <div className="pt-2 border-t border-slate-800/60 flex items-center justify-between text-[11px] text-slate-400">
                <span>Aggregate Total: <strong className="text-slate-200">493 Marks</strong></span>
                <span className="text-cyan-300 font-semibold">Distinction Tier (Top 16.1%)</span>
              </div>
            </div>

            {/* Exam Pass / Status Donut Breakdown */}
            <div className="glass rounded-3xl border border-slate-800 bg-slate-950/70 p-6 space-y-4">
              <h4 className="font-bold text-sm text-slate-100 flex items-center gap-2">
                <CheckCircle2 size={16} className="text-emerald-400" />
                Result Clearance Status
              </h4>

              <div className="grid grid-cols-3 gap-3 text-center">
                <div className="rounded-2xl border border-emerald-500/30 bg-emerald-950/20 p-3">
                  <div className="text-2xl font-black text-emerald-300">63</div>
                  <div className="text-[10px] font-bold text-emerald-400 uppercase mt-0.5">Passed (92.6%)</div>
                </div>
                <div className="rounded-2xl border border-rose-500/30 bg-rose-950/20 p-3">
                  <div className="text-2xl font-black text-rose-300">4</div>
                  <div className="text-[10px] font-bold text-rose-400 uppercase mt-0.5">Reappear (5.9%)</div>
                </div>
                <div className="rounded-2xl border border-purple-500/30 bg-purple-950/20 p-3">
                  <div className="text-2xl font-black text-purple-300">1</div>
                  <div className="text-[10px] font-bold text-purple-400 uppercase mt-0.5">UMC (1.5%)</div>
                </div>
              </div>

              {/* Status Visual Progress Bar */}
              <div className="h-3 w-full rounded-full bg-slate-900 border border-slate-800 overflow-hidden flex">
                <div style={{ width: '92.6%' }} className="bg-emerald-400 h-full" title="Pass 92.6%" />
                <div style={{ width: '5.9%' }} className="bg-rose-500 h-full" title="Reappear 5.9%" />
                <div style={{ width: '1.5%' }} className="bg-purple-500 h-full" title="UMC 1.5%" />
              </div>
            </div>
          </div>
        </div>
      )}

      {/* 4. SUBJECT BENCHMARKS TAB */}
      {activeTab === 'subjects' && (
        <div className="glass rounded-3xl border border-slate-800 bg-slate-950/70 p-6 space-y-6">
          <div className="flex flex-col md:flex-row md:items-center justify-between gap-3">
            <div>
              <h3 className="text-base font-bold text-slate-100 flex items-center gap-2">
                <BookOpen size={18} className="text-cyan-400" />
                Core Subject Performance & Difficulty Benchmark
              </h3>
              <p className="text-xs text-slate-400 mt-0.5">
                Cohort average score out of 100 across all 7 subjects in the 6th semester curriculum.
              </p>
            </div>
            <div className="text-xs text-slate-400">
              Evaluated across <strong className="text-cyan-300">68 students</strong>
            </div>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {COHORT_STATS.subjectAverages.map((subj) => (
              <div
                key={subj.code}
                className="rounded-2xl border border-slate-800 bg-slate-900/50 p-4 space-y-3 hover:border-slate-700 transition"
              >
                <div className="flex items-start justify-between gap-2">
                  <div>
                    <span className="text-[10px] font-mono font-bold text-cyan-400 uppercase tracking-wider">
                      {subj.code}
                    </span>
                    <h4 className="font-bold text-sm text-slate-100">{subj.name}</h4>
                  </div>
                  <span
                    className={`rounded-full px-2.5 py-0.5 text-[10px] font-bold border ${
                      subj.avg >= 75
                        ? 'bg-emerald-500/10 border-emerald-500/30 text-emerald-300'
                        : subj.avg >= 60
                        ? 'bg-amber-500/10 border-amber-500/30 text-amber-300'
                        : 'bg-rose-500/10 border-rose-500/30 text-rose-300'
                    }`}
                  >
                    {subj.toughScore}
                  </span>
                </div>

                {/* Score numbers */}
                <div className="flex items-baseline justify-between text-xs">
                  <span className="text-slate-400">Batch Average</span>
                  <div>
                    <span className="text-xl font-black text-slate-100">{subj.avg}</span>
                    <span className="text-slate-500 text-[11px] ml-1">/ {subj.max} Max</span>
                  </div>
                </div>

                {/* Meter Bar */}
                <div className="h-2.5 w-full rounded-full bg-slate-900 border border-slate-800 overflow-hidden">
                  <div
                    className="h-full rounded-full transition-all duration-700"
                    style={{
                      width: `${(subj.avg / 100) * 100}%`,
                      backgroundColor: subj.color,
                    }}
                  />
                </div>
              </div>
            ))}
          </div>

          <div className="rounded-2xl border border-amber-500/30 bg-amber-950/10 p-4 text-xs text-amber-200/90 leading-relaxed flex items-start gap-2.5">
            <Info size={16} className="text-amber-400 shrink-0 mt-0.5" />
            <div>
              <strong>Curriculum Difficulty Insights:</strong> Management & Organizational Behavior (HSMC-601) and Compiler Design (PCC-601) showed the strictest scoring with batch averages of 57.1 and 63.8 respectively. High-performance courses included Capstone Project (84.0 average) and Data Analytics (77.5 average).
            </div>
          </div>
        </div>
      )}

      {/* 5. TOPPERS LEADERBOARD TAB */}
      {activeTab === 'toppers' && (
        <div className="glass rounded-3xl border border-slate-800 bg-slate-950/70 p-6 space-y-6">
          <div className="flex items-center justify-between">
            <div>
              <h3 className="text-base font-bold text-slate-100 flex items-center gap-2">
                <Trophy size={18} className="text-amber-400" />
                Sixth Semester Top 10 Rankers
              </h3>
              <p className="text-xs text-slate-400 mt-0.5">
                Recognizing the highest achieving students in B.Tech Computer Engineering (AI/ML).
              </p>
            </div>
            <span className="rounded-full bg-amber-400/15 border border-amber-400/30 px-3 py-1 text-xs font-bold text-amber-300">
              Cutoff for Top 10: 8.97 SGPA
            </span>
          </div>

          {/* Top 3 Podium Cards */}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            {/* Rank 2 (Bhumi) */}
            <div className="glass rounded-2xl border border-slate-700/80 bg-slate-900/60 p-5 text-center space-y-2 order-2 md:order-1">
              <div className="inline-flex h-12 w-12 items-center justify-center rounded-2xl bg-slate-800 text-2xl font-bold border border-slate-600 shadow-md">
                🥈
              </div>
              <div className="text-xs font-bold uppercase tracking-wider text-slate-400">Rank #2</div>
              <h4 className="text-lg font-black text-slate-100">Bhumi Sharma</h4>
              <div className="text-2xl font-black text-cyan-300">9.31 <span className="text-xs font-normal text-slate-400">SGPA</span></div>
              <div className="text-[11px] text-slate-400 font-mono">23UGBCE09109</div>
            </div>

            {/* Rank 1 (Kanishka) - Elevated */}
            <div className="glass rounded-2xl border-2 border-amber-400/80 bg-gradient-to-b from-amber-950/40 via-slate-900 to-slate-950 p-6 text-center space-y-2.5 shadow-xl shadow-amber-950/40 order-1 md:order-2 transform md:-translate-y-2">
              <div className="inline-flex h-14 w-14 items-center justify-center rounded-2xl bg-amber-400/20 text-3xl font-bold border border-amber-400/40 shadow-lg">
                🥇
              </div>
              <div className="text-xs font-black uppercase tracking-wider text-amber-400">Cohort Champion · Rank #1</div>
              <h4 className="text-xl font-black text-white">Kanishka</h4>
              <div className="text-3xl font-black text-amber-300">9.56 <span className="text-xs font-normal text-slate-400">SGPA</span></div>
              <div className="text-[11px] text-amber-200/80 font-mono">23UGBCE09131 · 100% Distinction</div>
            </div>

            {/* Rank 2 (Riya) */}
            <div className="glass rounded-2xl border border-slate-700/80 bg-slate-900/60 p-5 text-center space-y-2 order-3">
              <div className="inline-flex h-12 w-12 items-center justify-center rounded-2xl bg-slate-800 text-2xl font-bold border border-slate-600 shadow-md">
                🥈
              </div>
              <div className="text-xs font-bold uppercase tracking-wider text-slate-400">Rank #2 (Tie)</div>
              <h4 className="text-lg font-black text-slate-100">Riya</h4>
              <div className="text-2xl font-black text-cyan-300">9.31 <span className="text-xs font-normal text-slate-400">SGPA</span></div>
              <div className="text-[11px] text-slate-400 font-mono">23UGBCE09149</div>
            </div>
          </div>

          {/* Ranks 4 to 10 + Kapil Table */}
          <div className="overflow-x-auto rounded-2xl border border-slate-800">
            <table className="w-full text-left text-xs text-slate-300">
              <thead className="bg-slate-900 text-slate-400 uppercase font-bold text-[10px] tracking-wider border-b border-slate-800">
                <tr>
                  <th className="px-4 py-3">Rank</th>
                  <th className="px-4 py-3">Roll Number</th>
                  <th className="px-4 py-3">Student Name</th>
                  <th className="px-4 py-3 text-right">SGPA</th>
                  <th className="px-4 py-3">Performance Tier</th>
                  <th className="px-4 py-3 text-right">Aggregate Total</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800/80 bg-slate-950/60">
                {top10Students.map((s, idx) => (
                  <tr key={s.Roll_Number} className="hover:bg-slate-900/60 transition">
                    <td className="px-4 py-3 font-bold text-slate-100">
                      {idx === 0 ? '🥇 #1' : idx === 1 || idx === 2 ? '🥈 #2' : `#${idx + 1}`}
                    </td>
                    <td className="px-4 py-3 font-mono text-cyan-300">{s.Roll_Number}</td>
                    <td className="px-4 py-3 font-semibold text-slate-100">{s.Student_Name}</td>
                    <td className="px-4 py-3 text-right font-black text-amber-300 text-sm">
                      {s.SGPA?.toFixed(2)}
                    </td>
                    <td className="px-4 py-3">
                      <span className="rounded-full bg-cyan-500/10 border border-cyan-500/30 px-2 py-0.5 text-[10px] font-semibold text-cyan-300">
                        {s.Performance_Tier}
                      </span>
                    </td>
                    <td className="px-4 py-3 text-right font-mono text-slate-300">
                      {s.Total_Marks} Marks
                    </td>
                  </tr>
                ))}

                {/* Kapil's Row Highlight */}
                <tr className="bg-cyan-950/40 border-t-2 border-cyan-400/50 hover:bg-cyan-950/60 transition">
                  <td className="px-4 py-3 font-black text-cyan-300">⭐ #11</td>
                  <td className="px-4 py-3 font-mono font-bold text-cyan-200">23UGBCE09130</td>
                  <td className="px-4 py-3 font-bold text-white flex items-center gap-2">
                    Kapil <span className="rounded-full bg-cyan-400 text-slate-950 px-2 py-0.5 text-[9px] font-black uppercase">You</span>
                  </td>
                  <td className="px-4 py-3 text-right font-black text-cyan-300 text-sm">8.91</td>
                  <td className="px-4 py-3">
                    <span className="rounded-full bg-emerald-500/20 border border-emerald-500/40 px-2 py-0.5 text-[10px] font-bold text-emerald-300">
                      Distinction (Top 16%)
                    </span>
                  </td>
                  <td className="px-4 py-3 text-right font-mono font-bold text-cyan-200">493 Marks</td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* 6. ALL 68 STUDENTS SEARCH & FILTER TAB */}
      {activeTab === 'students' && (
        <div className="glass rounded-3xl border border-slate-800 bg-slate-950/70 p-6 space-y-5">
          <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
            <div>
              <h3 className="text-base font-bold text-slate-100 flex items-center gap-2">
                <Search size={18} className="text-cyan-400" />
                Cohort Student Performance Explorer
              </h3>
              <p className="text-xs text-slate-400 mt-0.5">
                Search all 68 students by name, roll number, or filter by academic division.
              </p>
            </div>

            {/* Search Input */}
            <div className="relative w-full md:w-80">
              <Search size={15} className="absolute left-3.5 top-1/2 -translate-y-1/2 text-slate-400" />
              <input
                type="text"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                placeholder="Search student or roll number…"
                className="w-full rounded-xl border border-slate-700 bg-slate-900/90 pl-10 pr-4 py-2 text-xs text-slate-100 outline-none focus:border-cyan-400 transition"
              />
            </div>
          </div>

          {/* Filter Pills */}
          <div className="flex flex-wrap items-center gap-2">
            {[
              { id: 'ALL', label: `All (${STUDENT_RESULTS.length})` },
              { id: 'OUTSTANDING', label: `Outstanding ≥9.0 (${COHORT_STATS.outstandingCount})` },
              { id: 'DISTINCTION', label: `Distinction 8.5–8.99 (${COHORT_STATS.distinctionCount})` },
              { id: 'FIRST_CLASS', label: `First Class 8.0–8.49 (21)` },
              { id: 'BACKLOG', label: `Reappear / UMC (5)` },
            ].map((f) => (
              <button
                key={f.id}
                onClick={() => setTierFilter(f.id)}
                className={`px-3 py-1 rounded-xl text-xs font-semibold transition ${
                  tierFilter === f.id
                    ? 'bg-cyan-400 text-slate-950 font-bold'
                    : 'bg-slate-900 text-slate-400 hover:text-slate-200 border border-slate-800'
                }`}
              >
                {f.label}
              </button>
            ))}
          </div>

          {/* Results Table */}
          <div className="overflow-x-auto rounded-2xl border border-slate-800 max-h-[500px]">
            <table className="w-full text-left text-xs text-slate-300">
              <thead className="bg-slate-900 text-slate-400 uppercase font-bold text-[10px] tracking-wider sticky top-0 z-10 border-b border-slate-800">
                <tr>
                  <th className="px-4 py-3">Roll Number</th>
                  <th className="px-4 py-3">Student Name</th>
                  <th className="px-4 py-3 text-right">SGPA</th>
                  <th className="px-4 py-3">Result Status</th>
                  <th className="px-4 py-3">Performance Tier</th>
                  <th className="px-4 py-3 text-right">Total Marks</th>
                  <th className="px-4 py-3 text-center">Action</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800/80 bg-slate-950/60">
                {filteredStudents.map((s) => {
                  const isKapil = s.Roll_Number === '23UGBCE09130'
                  return (
                    <tr
                      key={s.Roll_Number}
                      className={`hover:bg-slate-900/60 transition ${
                        isKapil ? 'bg-cyan-950/30 border-l-4 border-cyan-400' : ''
                      }`}
                    >
                      <td className="px-4 py-3 font-mono text-cyan-300 font-semibold">{s.Roll_Number}</td>
                      <td className="px-4 py-3 font-medium text-slate-100 flex items-center gap-2">
                        {s.Student_Name}
                        {isKapil && (
                          <span className="rounded-full bg-cyan-400 text-slate-950 px-2 py-0.5 text-[9px] font-black uppercase">
                            You
                          </span>
                        )}
                      </td>
                      <td className="px-4 py-3 text-right font-black text-slate-100">
                        {s.SGPA !== null ? s.SGPA.toFixed(2) : '—'}
                      </td>
                      <td className="px-4 py-3">
                        <span
                          className={`rounded-full px-2 py-0.5 text-[10px] font-bold border ${
                            s.Result_Status === 'Pass'
                              ? 'bg-emerald-500/10 border-emerald-500/30 text-emerald-300'
                              : 'bg-rose-500/10 border-rose-500/30 text-rose-300'
                          }`}
                        >
                          {s.Result_Status}
                        </span>
                      </td>
                      <td className="px-4 py-3 text-slate-400">{s.Performance_Tier}</td>
                      <td className="px-4 py-3 text-right font-mono text-slate-300">
                        {s.Total_Marks ? `${s.Total_Marks}` : '—'}
                      </td>
                      <td className="px-4 py-3 text-center">
                        <button
                          onClick={() => setSelectedStudent(s)}
                          className="rounded-lg border border-slate-700 bg-slate-900/80 px-2.5 py-1 text-[11px] font-medium text-cyan-300 hover:border-cyan-400 transition"
                        >
                          View Details
                        </button>
                      </td>
                    </tr>
                  )
                })}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* 7. STUDENT DETAILS DRAWER / MODAL */}
      {selectedStudent && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/75 backdrop-blur-md p-4">
          <div className="glass w-full max-w-lg rounded-3xl border border-cyan-500/40 bg-slate-950 p-6 shadow-2xl space-y-5">
            <div className="flex items-start justify-between">
              <div>
                <span className="text-[10px] font-mono text-cyan-400 font-bold uppercase tracking-wider">
                  {selectedStudent.Roll_Number}
                </span>
                <h3 className="text-xl font-extrabold text-white">{selectedStudent.Student_Name}</h3>
                <p className="text-xs text-slate-400 mt-0.5">{selectedStudent.Performance_Tier}</p>
              </div>
              <div className="text-right">
                <div className="text-2xl font-black text-cyan-300">
                  {selectedStudent.SGPA !== null ? selectedStudent.SGPA.toFixed(2) : '—'}
                </div>
                <div className="text-[10px] text-slate-400 font-semibold uppercase">SGPA</div>
              </div>
            </div>

            {/* Subject Breakdown Grid */}
            <div className="space-y-2">
              <h4 className="text-xs font-bold text-slate-300 uppercase tracking-wider">
                Subject-wise Performance Breakdown
              </h4>
              <div className="grid grid-cols-2 gap-2 text-xs">
                <div className="rounded-xl border border-slate-800 bg-slate-900/70 p-2.5">
                  <div className="text-[10px] text-slate-400">Compiler Design</div>
                  <div className="text-sm font-bold text-slate-200">
                    {selectedStudent.Compiler_Design_Total ?? '—'} / 100 ({selectedStudent.Compiler_Design_Grade ?? '—'})
                  </div>
                </div>
                <div className="rounded-xl border border-slate-800 bg-slate-900/70 p-2.5">
                  <div className="text-[10px] text-slate-400">Advanced Computer Networks</div>
                  <div className="text-sm font-bold text-slate-200">
                    {selectedStudent.Adv_Networks_Total ?? '—'} / 100 ({selectedStudent.Adv_Networks_Grade ?? '—'})
                  </div>
                </div>
                <div className="rounded-xl border border-slate-800 bg-slate-900/70 p-2.5">
                  <div className="text-[10px] text-slate-400">Management & OB</div>
                  <div className="text-sm font-bold text-slate-200">
                    {selectedStudent.Management_OB_Total ?? '—'} / 100 ({selectedStudent.Management_OB_Grade ?? '—'})
                  </div>
                </div>
                <div className="rounded-xl border border-slate-800 bg-slate-900/70 p-2.5">
                  <div className="text-[10px] text-slate-400">ME3: Data Analytics</div>
                  <div className="text-sm font-bold text-slate-200">
                    {selectedStudent.ME3_Data_Analytics_Total ?? '—'} / 100 ({selectedStudent.ME3_Data_Analytics_Grade ?? '—'})
                  </div>
                </div>
                <div className="rounded-xl border border-slate-800 bg-slate-900/70 p-2.5">
                  <div className="text-[10px] text-slate-400">ME4: Security & Mining</div>
                  <div className="text-sm font-bold text-slate-200">
                    {selectedStudent.ME4_Security_Mining_Total ?? '—'} / 100 ({selectedStudent.ME4_Security_Mining_Grade ?? '—'})
                  </div>
                </div>
                <div className="rounded-xl border border-slate-800 bg-slate-900/70 p-2.5">
                  <div className="text-[10px] text-slate-400">Capstone Project Phase-I</div>
                  <div className="text-sm font-bold text-slate-200">
                    {selectedStudent.Capstone_Project_Total ?? '—'} / 100 ({selectedStudent.Capstone_Project_Grade ?? '—'})
                  </div>
                </div>
              </div>
            </div>

            <div className="flex justify-end pt-2">
              <button
                onClick={() => setSelectedStudent(null)}
                className="rounded-xl bg-cyan-400 px-5 py-2 text-xs font-bold text-slate-950 hover:bg-cyan-300 transition"
              >
                Close Details
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
