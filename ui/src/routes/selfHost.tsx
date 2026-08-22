import { Routes, Route, Navigate } from 'react-router';
import LoginPage from '@/pages/LoginPage';
import AcceptInvitationPage from '@/pages/AcceptInvitationPage';
import ProtectedRoute from '@/components/ProtectedRoute';
import { InstanceClientProvider } from '@/lib/snackbase/InstanceClientProvider';
import { AdminLayout, studioChildRouteElements } from '@/routes/studioRoutes';
import { Toaster } from '@/components/ui/toaster';
import { DemoBanner } from '@/components/DemoBanner';

export default function SelfHostRoutes() {
  return (
    <>
      <DemoBanner />
      <InstanceClientProvider>
        <Routes>
          <Route path="/" element={<Navigate to="/admin/dashboard" replace />} />

          <Route path="/admin/login" element={<LoginPage />} />
          <Route path="/accept-invitation" element={<AcceptInvitationPage />} />

          <Route
            path="/admin"
            element={
              <ProtectedRoute>
                <AdminLayout />
              </ProtectedRoute>
            }
          >
            {studioChildRouteElements()}
          </Route>

          <Route path="*" element={<Navigate to="/admin/dashboard" replace />} />
        </Routes>
      </InstanceClientProvider>
      <Toaster />
    </>
  );
}
