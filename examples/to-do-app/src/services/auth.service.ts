/**
 * Authentication service
 * Handles register, login, token refresh, and user info retrieval
 */

import { apiClient } from '@/lib/api';
import type {
  LoginRequest,
  RegisterRequest,
  AuthResponse,
} from '@/types';

/**
 * Register a new account with first user
 */
export const register = async (
  accountName: string,
  accountSlug: string | undefined,
  email: string,
  password: string
): Promise<AuthResponse> => {
  const payload: RegisterRequest = {
    account_name: accountName,
    ...(accountSlug && { account_slug: accountSlug }),
    email,
    password,
  };

  const response = await apiClient.post<AuthResponse>('/auth/register', payload);
  return response.data;
};

/**
 * Login with email and password
 */
export const login = async (account: string, email: string, password: string): Promise<AuthResponse> => {
  const payload: LoginRequest = {
    account,
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
 * Logout (client-side only - clears local state)
 */
export const logout = (): void => {
  localStorage.removeItem('auth-storage');
};
