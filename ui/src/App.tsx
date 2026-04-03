import './App.css';
import { Routes, Route, Navigate } from 'react-router';
import LoginPage from '@/pages/LoginPage';
import DashboardPage from '@/pages/DashboardPage';
import AccountsPage from '@/pages/AccountsPage';
import UsersPage from '@/pages/UsersPage';
import InvitationsPage from '@/pages/InvitationsPage';
import GroupsPage from '@/pages/GroupsPage';
import CollectionsPage from '@/pages/CollectionsPage';
import RecordsPage from '@/pages/RecordsPage';
import AnalyticsPage from '@/pages/AnalyticsPage';
import RolesPage from '@/pages/RolesPage';
import AuditLogsPage from '@/pages/AuditLogsPage';
import MigrationsPage from '@/pages/MigrationsPage';
import MacrosPage from '@/pages/MacrosPage';
import AcceptInvitationPage from '@/pages/AcceptInvitationPage';
import ConfigurationDashboardPage from '@/pages/ConfigurationDashboardPage';
import ApiKeysPage from '@/pages/ApiKeys/ApiKeysPage';
import WebhooksPage from '@/pages/Webhooks/WebhooksPage';
import JobsPage from '@/pages/Jobs/JobsPage';
import ScheduledTasksPage from '@/pages/ScheduledTasks/ScheduledTasksPage';
import HooksPage from '@/pages/Hooks/HooksPage';
import AdminLayout from '@/layouts/AdminLayout';
import ProtectedRoute from '@/components/ProtectedRoute';
import { Toaster } from '@/components/ui/toaster';
import { DemoBanner } from '@/components/DemoBanner';

function App() {
  return (
    <>
      <DemoBanner />
      <Routes>
        {/* Redirect root to admin */}
        <Route path="/" element={<Navigate to="/admin/dashboard" replace />} />


        {/* Public routes */}
        <Route path="/admin/login" element={<LoginPage />} />
        <Route path="/accept-invitation" element={<AcceptInvitationPage />} />

        {/* Protected admin routes */}
        <Route
          path="/admin"
          element={
            <ProtectedRoute>
              <AdminLayout />
            </ProtectedRoute>
          }
        >
          <Route index element={<Navigate to="/admin/dashboard" replace />} />
          <Route path="dashboard" element={<DashboardPage />} />
          <Route path="accounts" element={<AccountsPage />} />
          <Route path="users" element={<UsersPage />} />
          <Route path="invitations" element={<InvitationsPage />} />
          <Route path="groups" element={<GroupsPage />} />
          <Route path="collections" element={<CollectionsPage />} />
          <Route path="collections/:collectionName/records" element={<RecordsPage />} />
          <Route path="collections/:collectionName/analytics" element={<AnalyticsPage />} />
          <Route path="roles" element={<RolesPage />} />
          <Route path="audit-logs" element={<AuditLogsPage />} />
          <Route path="migrations" element={<MigrationsPage />} />
          <Route path="macros" element={<MacrosPage />} />
          <Route path="configuration" element={<ConfigurationDashboardPage />} />
          <Route path="api-keys" element={<ApiKeysPage />} />
          <Route path="webhooks" element={<WebhooksPage />} />
          <Route path="jobs" element={<JobsPage />} />
          <Route path="scheduled-tasks" element={<ScheduledTasksPage />} />
          <Route path="hooks" element={<HooksPage />} />
        </Route>

        {/* Catch all - redirect to dashboard */}
        <Route path="*" element={<Navigate to="/admin/dashboard" replace />} />
      </Routes>
      <Toaster />
    </>
  );
}

export default App;
