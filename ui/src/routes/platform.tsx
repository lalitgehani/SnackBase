import { Routes, Route, Navigate } from 'react-router';
import LoginPage from '@/pages/platform/LoginPage';
import RegisterPage from '@/pages/platform/RegisterPage';
import AcceptInvitationPage from '@/pages/platform/AcceptInvitationPage';
import OrganizationsPage from '@/pages/platform/OrganizationsPage';
import CreateOrganizationPage from '@/pages/platform/CreateOrganizationPage';
import ProjectsPage from '@/pages/platform/ProjectsPage';
import CreateProjectPage from '@/pages/platform/CreateProjectPage';
import EnvironmentsPage from '@/pages/platform/EnvironmentsPage';
import AccountSettingsPage from '@/pages/platform/AccountSettingsPage';
import ConsoleLayout from '@/layouts/platform/ConsoleLayout';
import PlatformStudioLayout from '@/layouts/platform/PlatformStudioLayout';
import ProtectedRoute from '@/components/platform/ProtectedRoute';
import { ProjectStudioRoot, PlatformAdminRedirect } from '@/routes/ProjectStudioRoot';
import { StudioChildRoutes } from '@/routes/studioRoutes';
import { Toaster } from '@/components/ui/toaster';
import { PLATFORM_SENTINEL } from '@/lib/__platform_sentinel__';

export default function PlatformRoutes() {
  return (
    <>
      <div hidden data-platform-sentinel={PLATFORM_SENTINEL} />
      <Routes>
        <Route path="/login" element={<LoginPage />} />
        <Route path="/register" element={<RegisterPage />} />
        <Route path="/accept-invitation" element={<AcceptInvitationPage />} />

        <Route
          path="/"
          element={
            <ProtectedRoute>
              <ConsoleLayout />
            </ProtectedRoute>
          }
        >
          <Route index element={<Navigate to="/organizations" replace />} />
          <Route path="organizations" element={<OrganizationsPage />} />
          <Route path="organizations/new" element={<CreateOrganizationPage />} />
          <Route
            path="organizations/:orgId"
            element={<Navigate to="projects" replace />}
          />
          <Route path="organizations/:orgId/projects" element={<ProjectsPage />} />
          <Route
            path="organizations/:orgId/projects/new"
            element={<CreateProjectPage />}
          />
          <Route
            path="organizations/:orgId/projects/:projectId"
            element={<Navigate to="environments" replace />}
          />
          <Route
            path="organizations/:orgId/projects/:projectId/environments"
            element={<EnvironmentsPage />}
          />
          <Route path="account" element={<AccountSettingsPage />} />
        </Route>

        <Route
          path="/project/:ref"
          element={
            <ProtectedRoute>
              <ProjectStudioRoot>
                <PlatformStudioLayout />
              </ProjectStudioRoot>
            </ProtectedRoute>
          }
        >
          <StudioChildRoutes />
        </Route>

        <Route path="/admin/*" element={<PlatformAdminRedirect />} />

        <Route path="*" element={<Navigate to="/organizations" replace />} />
      </Routes>
      <Toaster />
    </>
  );
}
