import { BrowserRouter, Routes, Route, Navigate } from 'react-router';
import ProtectedRoute from '@/components/auth/ProtectedRoute';
import LoginPage from '@/components/auth/LoginPage';
import RegisterPage from '@/components/auth/RegisterPage';
import VerifyEmailPage from '@/components/auth/VerifyEmailPage';
import OAuthCallback from '@/components/auth/OAuthCallback';
import TodoList from '@/components/todos/TodoList';

function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/login" element={<LoginPage />} />
        <Route path="/register" element={<RegisterPage />} />
        <Route path="/verify-email" element={<VerifyEmailPage />} />
        <Route path="/oauth/callback" element={<OAuthCallback />} />
        <Route path="/" element={
          <ProtectedRoute>
            <Navigate to="/todos" replace />
          </ProtectedRoute>
        } />
        <Route path="/todos" element={
          <ProtectedRoute>
            <TodoList />
          </ProtectedRoute>
        } />
      </Routes>
    </BrowserRouter>
  );
}

export default App;
