import { Navigate, Route, Routes } from 'react-router-dom'
import Layout from './components/Layout'
import ProtectedRoute from './components/auth/ProtectedRoute'
import { ModeProvider } from './contexts/ModeContext'
import AIBusinessAnalystPage from './pages/AIBusinessAnalystPage'
import AnalyticsPage from './pages/AnalyticsPage'
import DashboardEditorPage from './pages/DashboardEditorPage'
import DataPrepStudioPage from './pages/DataPrepStudioPage'
import ExplorerPage from './pages/ExplorerPage'
import ForecastingCenterPage from './pages/ForecastingCenterPage'
import HealthPage from './pages/HealthPage'
import LandingPage from './pages/LandingPage'
import LoginPage from './pages/LoginPage'
import ModelManagementPage from './pages/ModelManagementPage'
import OnboardingPage from './pages/OnboardingPage'
import ProjectInsightsPage from './pages/ProjectInsightsPage'
import RegisterPage from './pages/RegisterPage'
import ReportCenterPage from './pages/ReportCenterPage'
import ResetPasswordPage from './pages/ResetPasswordPage'
import SavedDashboardsPage from './pages/SavedDashboardsPage'
import ScenarioSimulatorPage from './pages/ScenarioSimulatorPage'
import SettingsPage from './pages/SettingsPage'
import SharedReportPage from './pages/SharedReportPage'
import SQLStudioPage from './pages/SQLStudioPage'
import UploadPage from './pages/UploadPage'
import VerifyEmailPage from './pages/VerifyEmailPage'
import VisualizationStudioPage from './pages/VisualizationStudioPage'
import WorkspaceManagementPage from './pages/WorkspaceManagementPage'

export default function App() {
  return (
    <ModeProvider>
      <Routes>
        <Route element={<Layout />}>
          {/* Public Routes */}
          <Route index element={<LandingPage />} />
          <Route path="login" element={<LoginPage />} />
          <Route path="register" element={<RegisterPage />} />
          <Route path="reset-password" element={<ResetPasswordPage />} />
          <Route path="verify-email" element={<VerifyEmailPage />} />
          <Route path="shared/report/:token" element={<SharedReportPage />} />
          <Route path="health" element={<HealthPage />} />

          {/* Protected Routes — Require Authenticated Session */}
          <Route element={<ProtectedRoute />}>
            <Route path="workspace" element={<UploadPage />} />
            <Route path="workspaces" element={<WorkspaceManagementPage />} />
            <Route path="onboarding" element={<OnboardingPage />} />
            <Route path="settings" element={<SettingsPage />} />
            <Route path="data-prep/:id" element={<DataPrepStudioPage />} />
            <Route path="datasets/:id" element={<ExplorerPage />} />
            <Route path="analytics/:id" element={<AnalyticsPage />} />
            <Route path="studio/:id" element={<VisualizationStudioPage />} />
            <Route path="sql/:id" element={<SQLStudioPage />} />
            <Route path="insights/:id" element={<ProjectInsightsPage />} />
            <Route path="project-insights/:id" element={<ProjectInsightsPage />} />
            <Route path="dashboard/:id/edit" element={<DashboardEditorPage />} />
            <Route path="dashboards" element={<SavedDashboardsPage />} />
            <Route path="reports" element={<ReportCenterPage />} />
            <Route path="ai-analyst/:id" element={<AIBusinessAnalystPage />} />
            <Route path="forecasting" element={<ForecastingCenterPage />} />
            <Route path="forecasting/:id" element={<ForecastingCenterPage />} />
            <Route path="simulator/:id" element={<ScenarioSimulatorPage />} />
            <Route path="models" element={<ModelManagementPage />} />
          </Route>

          {/* Catch-all Wildcard */}
          <Route path="*" element={<Navigate to="/" replace />} />
        </Route>
      </Routes>
    </ModeProvider>
  )
}
