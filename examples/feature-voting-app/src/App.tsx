import { Routes, Route, Navigate } from 'react-router'
import ProtectedRoute from '@/components/auth/ProtectedRoute'
import LoginPage from '@/components/auth/LoginPage'
import RegisterPage from '@/components/auth/RegisterPage'
import FeatureList from '@/components/features/FeatureList'

function App() {
  return (
    <Routes>
      <Route path="/login" element={<LoginPage />} />
      <Route path="/register" element={<RegisterPage />} />
      <Route path="/" element={
        <ProtectedRoute>
          <Navigate to="/features" replace />
        </ProtectedRoute>
      } />
      <Route path="/features" element={
        <ProtectedRoute>
          <FeatureList />
        </ProtectedRoute>
      } />
    </Routes>
  )
}

export default App
