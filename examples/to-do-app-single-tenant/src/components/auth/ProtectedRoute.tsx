/**
 * Protected route wrapper
 * Redirects to login if user is not authenticated
 */

import { useEffect } from 'react';
import { Navigate, useLocation } from 'react-router';
import { useAuthStore } from '@/stores/auth.store';
import { Loader2 } from 'lucide-react';

interface ProtectedRouteProps {
  children: React.ReactNode;
}

export default function ProtectedRoute({ children }: ProtectedRouteProps) {
  const location = useLocation();
  const { isAuthenticated, isLoading, restoreSession } = useAuthStore();

  useEffect(() => {
    // Restore session on mount
    restoreSession();
  }, [restoreSession]);

  // Show loading state while checking authentication
  if (isLoading) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-gray-50">
        <div className="text-center">
          <Loader2 className="h-8 w-8 animate-spin text-blue-600 mx-auto" />
          <p className="mt-4 text-gray-600">Loading...</p>
        </div>
      </div>
    );
  }

  // Redirect to login if not authenticated
  if (!isAuthenticated) {
    return <Navigate to="/login" state={{ from: location }} replace />;
  }

  return <>{children}</>;
}
