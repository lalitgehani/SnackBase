/**
 * Authentication service
 * Handles register, login, token refresh, and user info retrieval
 */

import { apiClient } from '@/lib/api';
import type {
  LoginRequest,
  RegisterRequest,
  RegisterResponse,
  AuthResponse,
} from '@/types';

/**
 * Register a new account with first user
 */
export const register = async (
  email: string,
  password: string
): Promise<RegisterResponse> => {
  const payload: RegisterRequest = {
    email,
    password,
  };

  const response = await apiClient.post<RegisterResponse>('/auth/register', payload);
  return response.data;
};

/**
 * Login with email and password
 */
export const login = async (email: string, password: string): Promise<AuthResponse> => {
  const payload: LoginRequest = {
    email,
    password,
  };

  const response = await apiClient.post<AuthResponse>('/auth/login', payload);
  return response.data;
};

/**
 * Get current user info
 */
export const getCurrentUser = async (): Promise<{ user_id: string; account_id: string; email: string; role: string }> => {
  const response = await apiClient.get('/auth/me');
  return response.data;
};

/**
 * Verify email with token
 */
export const verifyEmail = async (token: string): Promise<{ message: string; user: { id: string; email: string; email_verified: boolean } }> => {
  const response = await apiClient.post('/auth/verify-email', { token });
  return response.data;
};

/**
 * Resend verification email (public endpoint)
 */
export const resendVerification = async (email: string): Promise<{ message: string; email: string }> => {
  const response = await apiClient.post('/auth/resend-verification', { email });
  return response.data;
};

/**
 * Logout (client-side only - clears local state)
 */
export const logout = (): void => {
  localStorage.removeItem('auth-storage');
};
