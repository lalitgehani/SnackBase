/**
 * Authentication service
 * Handles login, token refresh, and user info retrieval
 */

import { apiClient } from '@/lib/api';
import type {
  LoginRequest,
  AuthResponse,
  TokenRefreshResponse,
  CurrentUserResponse,
} from '@/types/auth.types';

// System account ID for superadmin
const SYSTEM_ACCOUNT_ID = 'SY0000';

/**
 * Login with superadmin credentials
 */
export const login = async (email: string, password: string): Promise<AuthResponse> => {
  const response = await apiClient.post<AuthResponse>('/auth/login', {
    account: SYSTEM_ACCOUNT_ID,
    email,
    password,
  } as LoginRequest & { account: string });
  
  return response.data;
};

/**
 * Refresh access token
 */
export const refreshToken = async (refreshToken: string): Promise<TokenRefreshResponse> => {
  const response = await apiClient.post<TokenRefreshResponse>('/auth/refresh', {
    refresh_token: refreshToken,
  });
  
  return response.data;
};

/**
 * Get current user info
 */
export const getCurrentUser = async (): Promise<CurrentUserResponse> => {
  const response = await apiClient.get<CurrentUserResponse>('/auth/me');
  return response.data;
};

/**
 * Logout (client-side only - clears local state)
 */
export const logout = (): void => {
  // In the future, we could call a backend logout endpoint to revoke tokens
  // For now, just clear local storage
  localStorage.removeItem('auth-storage');
};
