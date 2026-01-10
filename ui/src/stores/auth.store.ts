/**
 * Authentication store using Zustand
 * Manages authentication state, login, logout, and session persistence
 */

import { create } from 'zustand';
import { persist } from 'zustand/middleware';
import * as authService from '@/services/auth.service';
import type { AuthResponse, UserInfo, AccountInfo } from '@/types/auth.types';

interface AuthState {
  // State
  user: UserInfo | null;
  account: AccountInfo | null;
  token: string | null;
  refreshToken: string | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  error: string | null;

  // Actions
  login: (email: string, password: string) => Promise<void>;
  logout: () => void;
  clearError: () => void;
  restoreSession: () => Promise<void>;
  setAuth: (response: AuthResponse) => void;
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

      // Login action
      login: async (email: string, password: string) => {
        set({ isLoading: true, error: null });

        try {
          const response = await authService.login(email, password);

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

      // Set auth state manually (e.g. after registration or invitation acceptance)
      setAuth: (response: AuthResponse) => {
        set({
          user: response.user,
          account: response.account,
          token: response.token,
          refreshToken: response.refresh_token,
          isAuthenticated: true,
          isLoading: false,
          error: null,
        });
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
