import rawData from './studentResultsData.json'

export interface StudentResult {
  Roll_Number: string
  Student_Name: string
  Compiler_Design_Total: number | null
  Compiler_Design_Grade: string | null
  Adv_Networks_Total: number | null
  Adv_Networks_Grade: string | null
  Management_OB_Total: number | null
  Management_OB_Grade: string | null
  ME3_Data_Analytics_Total: number | null
  ME3_Data_Analytics_Grade: string | null
  ME4_Security_Mining_Total: number | null
  ME4_Security_Mining_Grade: string | null
  Analytics_Lab_Total: number | null
  Analytics_Lab_Grade: string | null
  Capstone_Project_Total: number | null
  Capstone_Project_Grade: string | null
  Total_Marks: number
  SGPA: number | null
  Result_Status: string
  Performance_Tier: string
  Remarks: string
  Rank: number
}

export const STUDENT_RESULTS: StudentResult[] = (rawData as unknown) as StudentResult[]

export const COHORT_STATS = {
  totalStudents: 68,
  passCount: 63,
  passRate: 92.65,
  reappearCount: 4,
  umcCount: 1,
  absentCount: 0,
  averageSgpa: 8.33,
  medianSgpa: 8.31,
  highestSgpa: 9.56,
  distinctionCount: 27,
  distinctionRate: 39.71,
  outstandingCount: 9,
  outstandingRate: 13.24,
  kapil: {
    rollNumber: '23UGBCE09130',
    name: 'Kapil',
    sgpa: 8.91,
    rank: 11,
    percentile: 84.8,
    tier: 'Distinction (8.5 - 8.99)',
    compilerDesign: 84.0,
    advNetworks: 89.0,
    managementOB: 63.0,
    dataAnalytics: 84.0,
    securityMining: 84.0,
    capstone: 89.0,
    totalMarks: 493.0,
  },
  topper: {
    name: 'Kanishka',
    rollNumber: '23UGBCE09131',
    sgpa: 9.56,
    rank: 1,
  },
  secondRankers: [
    { name: 'Bhumi Sharma', rollNumber: '23UGBCE09109', sgpa: 9.31, rank: 2 },
    { name: 'Riya', rollNumber: '23UGBCE09149', sgpa: 9.31, rank: 2 },
  ],
  subjectAverages: [
    { name: 'Capstone Project Phase-I', code: 'PROJ-601', avg: 84.0, max: 93, toughScore: 'High Scoring', color: '#10b981' },
    { name: 'ME4: Info & Network Security / Mining', code: 'PEC-IV', avg: 78.0, max: 97, toughScore: 'Strong Performance', color: '#06b6d4' },
    { name: 'ME3: Data Analytics & Warehousing', code: 'PEC-III', avg: 77.5, max: 96, toughScore: 'Strong Performance', color: '#3b82f6' },
    { name: 'Advanced Computer Networks', code: 'PCC-602', avg: 77.2, max: 97, toughScore: 'Strong Performance', color: '#6366f1' },
    { name: 'Compiler Design', code: 'PCC-601', avg: 63.8, max: 89, toughScore: 'Challenging (Theory)', color: '#f59e0b' },
    { name: 'Management & Org. Behavior', code: 'HSMC-601', avg: 57.1, max: 79, toughScore: 'Most Stringent', color: '#ef4444' },
    { name: 'Data Analytics Lab', code: 'PCC-601P', avg: 44.6, max: 48, toughScore: 'Practical / 50', color: '#8b5cf6' },
  ],
  tierDistribution: [
    { label: 'Outstanding (≥ 9.0)', count: 9, percentage: 13.2, color: '#38bdf8', badge: 'bg-sky-500/15 text-sky-300 border-sky-500/30' },
    { label: 'Distinction (8.5 - 8.99)', count: 18, percentage: 26.5, color: '#34d399', badge: 'bg-emerald-500/15 text-emerald-300 border-emerald-500/30' },
    { label: 'First Class Merit (8.0 - 8.49)', count: 21, percentage: 30.9, color: '#818cf8', badge: 'bg-indigo-500/15 text-indigo-300 border-indigo-500/30' },
    { label: 'First Class (7.5 - 7.99)', count: 13, percentage: 19.1, color: '#fbbf24', badge: 'bg-amber-500/15 text-amber-300 border-amber-500/30' },
    { label: 'Second Class (< 7.5)', count: 2, percentage: 2.9, color: '#f97316', badge: 'bg-orange-500/15 text-orange-300 border-orange-500/30' },
    { label: 'Re-appear (Backlog)', count: 4, percentage: 5.9, color: '#f43f5e', badge: 'bg-rose-500/15 text-rose-300 border-rose-500/30' },
    { label: 'UMC Disciplinary', count: 1, percentage: 1.5, color: '#a855f7', badge: 'bg-purple-500/15 text-purple-300 border-purple-500/30' },
  ],
}
