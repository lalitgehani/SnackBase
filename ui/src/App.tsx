import './App.css';
import { Routes, Route, Navigate } from 'react-router';
import LoginPage from '@/pages/LoginPage';
import DashboardPage from '@/pages/DashboardPage';
import AccountsPage from '@/pages/AccountsPage';
import UsersPage from '@/pages/UsersPage';
import GroupsPage from '@/pages/GroupsPage';
import CollectionsPage from '@/pages/CollectionsPage';
import RecordsPage from '@/pages/RecordsPage';
import RolesPage from '@/pages/RolesPage';
import AuditLogsPage from '@/pages/AuditLogsPage';
import MigrationsPage from '@/pages/MigrationsPage';
import AdminLayout from '@/layouts/AdminLayout';
import ProtectedRoute from '@/components/ProtectedRoute';

function App() {
  return (
    <Routes>
      {/* Redirect root to admin */}
      <Route path="/" element={<Navigate to="/admin/dashboard" replace />} />

      {/* Public routes */}
      <Route path="/admin/login" element={<LoginPage />} />

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
        <Route path="groups" element={<GroupsPage />} />
        <Route path="collections" element={<CollectionsPage />} />
        <Route path="collections/:collectionName/records" element={<RecordsPage />} />
        <Route path="roles" element={<RolesPage />} />
        <Route path="audit-logs" element={<AuditLogsPage />} />
        <Route path="migrations" element={<MigrationsPage />} />
      </Route>

      {/* Catch all - redirect to dashboard */}
      <Route path="*" element={<Navigate to="/admin/dashboard" replace />} />
    </Routes>
  );
}

export default App;
