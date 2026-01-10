/**
 * Authentication store using Zustand
 * Manages authentication state, login, register, logout, and session persistence
 */

import { create } from 'zustand';
import { persist } from 'zustand/middleware';
import * as authService from '@/services/auth.service';
import * as oauthService from '@/services/oauth.service';
import type { UserInfo, AccountInfo, OAuthCallbackResponse } from '@/types';

interface AuthState {
  // State
  user: UserInfo | null;
  account: AccountInfo | null;
  token: string | null;
  refreshToken: string | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  error: string | null;
  registrationEmail: string | null; // Track email for pending verification

  // Actions
  login: (account: string, email: string, password: string) => Promise<void>;
  register: (accountName: string, accountSlug: string | undefined, email: string, password: string) => Promise<{ message: string; accountSlug: string }>;
  oauthLogin: (provider?: 'google' | 'github' | 'microsoft' | 'apple', account?: string, accountName?: string) => Promise<void>;
  logout: () => void;
  clearError: () => void;
  restoreSession: () => Promise<void>;
}

export const useAuthStore = create<AuthState>()(
  persist(
    (set, get) => ({
      // Initial state
      user: null,
      account: null,
      token: null,
      refreshToken: null,
      isAuthenticated: false,
      isLoading: false,
      error: null,
      registrationEmail: null,

      // Login action
      login: async (account: string, email: string, password: string) => {
        set({ isLoading: true, error: null });

        try {
          const response = await authService.login(account, email, password);

          set({
            user: response.user,
            account: response.account,
            token: response.token,
            refreshToken: response.refresh_token,
            isAuthenticated: true,
            isLoading: false,
            error: null,
            registrationEmail: null,
          });
        } catch (error) {
          const errorMessage = error instanceof Error ? error.message : 'Login failed';

          set({
            user: null,
            account: null,
            token: null,
            refreshToken: null,
            isAuthenticated: false,
            isLoading: false,
            error: errorMessage,
          });

          throw error;
        }
      },

      // Register action - now returns registration info without tokens
      register: async (accountName: string, accountSlug: string | undefined, email: string, password: string) => {
        set({ isLoading: true, error: null });

        try {
          const response = await authService.register(accountName, accountSlug, email, password);

          // Store email for verification flow, but don't authenticate
          set({
            registrationEmail: email,
            isLoading: false,
            error: null,
          });

          return {
            message: response.message,
            accountSlug: response.account.slug,
          };
        } catch (error) {
          const errorMessage = error instanceof Error ? error.message : 'Registration failed';

          set({
            isLoading: false,
            error: errorMessage,
            registrationEmail: null,
          });

          throw error;
        }
      },

      // OAuth login action
      oauthLogin: async (provider = 'google', account?: string, accountName?: string) => {
        set({ isLoading: true, error: null });

        try {
          const response: OAuthCallbackResponse = await oauthService.signInWithOAuth(provider, account, accountName);

          set({
            user: response.user,
            account: response.account,
            token: response.token,
            refreshToken: response.refresh_token,
            isAuthenticated: true,
            isLoading: false,
            error: null,
          });
        } catch (error) {
          const errorMessage = error instanceof Error ? error.message : 'OAuth login failed';

          set({
            user: null,
            account: null,
            token: null,
            refreshToken: null,
            isAuthenticated: false,
            isLoading: false,
            error: errorMessage,
          });

          throw error;
        }
      },

      // Logout action
      logout: () => {
        authService.logout();

        set({
          user: null,
          account: null,
          token: null,
          refreshToken: null,
          isAuthenticated: false,
          isLoading: false,
          error: null,
        });
      },

      // Clear error
      clearError: () => {
        set({ error: null });
      },

      // Restore session (called on app load)
      restoreSession: async () => {
        const { token, isAuthenticated } = get();

        // If we have a token, verify it's still valid
        if (token && isAuthenticated) {
          try {
            // Try to get current user info to verify token
            await authService.getCurrentUser();

            // Token is valid, session restored
            set({ isLoading: false });
          } catch (error) {
            // Token is invalid, clear session
            console.error('Session restoration failed:', error);
            get().logout();
          }
        }
      },
    }),
    {
      name: 'auth-storage',
      partialize: (state) => ({
        user: state.user,
        account: state.account,
        token: state.token,
        refreshToken: state.refreshToken,
        isAuthenticated: state.isAuthenticated,
      }),
    }
  )
);
