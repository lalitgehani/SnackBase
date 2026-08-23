/**
 * Auth store — Zustand session state delegating to the instance SDK client.
 */

import { create } from 'zustand';
import { persist } from 'zustand/middleware';
import { getInstanceClient } from '@/lib/snackbase/instanceClientRef';
import { instanceIdentityFromMe } from '@/lib/snackbase/instanceIdentity';
import type { AuthResponse, AccountInfo, UserInfo } from '@/types/auth.types';

interface AuthState {
  user: UserInfo | null;
  account: AccountInfo | null;
  token: string | null;
  refreshToken: string | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  error: string | null;
  login: (email: string, password: string) => Promise<void>;
  logout: () => void;
  restoreSession: () => Promise<void>;
  clearError: () => void;
  setAuth: (response: AuthResponse) => void;
}

function extractErrorMessage(error: unknown): string {
  if (error instanceof Error) return error.message;
  if (typeof error === 'object' && error !== null && 'message' in error) {
    return String((error as { message: unknown }).message);
  }
  return 'Login failed';
}

function toAuthResponse(raw: {
  token?: string;
  refresh_token?: string;
  refreshToken?: string;
  expires_in?: number;
  account?: AccountInfo;
  user?: UserInfo;
}): AuthResponse {
  return {
    token: raw.token ?? '',
    refresh_token: raw.refresh_token ?? raw.refreshToken ?? '',
    expires_in: raw.expires_in ?? 3600,
    account: raw.account as AccountInfo,
    user: raw.user as UserInfo,
  };
}

function authSliceFromResponse(response: AuthResponse) {
  return {
    user: response.user,
    account: response.account,
    token: response.token,
    refreshToken: response.refresh_token,
    isAuthenticated: true,
    isLoading: false,
    error: null,
  };
}

export const useAuthStore = create<AuthState>()(
  persist(
    (set, get) => ({
      user: null,
      account: null,
      token: null,
      refreshToken: null,
      isAuthenticated: false,
      isLoading: false,
      error: null,

      login: async (email, password) => {
        set({ isLoading: true, error: null });
        try {
          const client = getInstanceClient();
          const raw = await client.auth.login({
            email,
            password,
            account: 'SY0000',
          });
          set(authSliceFromResponse(toAuthResponse(raw)));
        } catch (error) {
          set({
            isLoading: false,
            error: extractErrorMessage(error),
            isAuthenticated: false,
            user: null,
            account: null,
            token: null,
            refreshToken: null,
          });
          throw error;
        }
      },

      logout: () => {
        try {
          const client = getInstanceClient();
          void client.auth.logout();
        } catch {
          // Provider may not be mounted during teardown.
        }
        set({
          user: null,
          account: null,
          token: null,
          refreshToken: null,
          isAuthenticated: false,
          error: null,
        });
      },

      restoreSession: async () => {
        set({ isLoading: true });
        try {
          const client = getInstanceClient();
          const sdkAuth = client.internalAuthManager.getState();
          const { token, refreshToken, user, account } = get();

          if (sdkAuth.token && sdkAuth.isAuthenticated) {
            set({
              user: sdkAuth.user as UserInfo | null,
              account: sdkAuth.account as AccountInfo | null,
              token: sdkAuth.token,
              refreshToken: sdkAuth.refreshToken,
              isAuthenticated: true,
            });
          } else if (token && user && account) {
            await client.internalAuthManager.updateState({
              token,
              refresh_token: refreshToken ?? '',
              expires_in: 3600,
              user,
              account,
            });
          } else {
            set({ isLoading: false, isAuthenticated: false });
            return;
          }

          // /auth/me is flat ({ user_id, account_id, email, role }); login is nested.
          // Mapping through toAuthResponse drops account and replaces the token with ''.
          const raw = await client.auth.getCurrentUser();
          const identity = instanceIdentityFromMe(raw);
          if (!identity) {
            set({ isLoading: false, isAuthenticated: false });
            return;
          }

          const latestSdk = client.internalAuthManager.getState();
          set({
            user: identity.user,
            account: identity.account,
            token: latestSdk.token ?? get().token,
            refreshToken: latestSdk.refreshToken ?? get().refreshToken,
            isAuthenticated: true,
            isLoading: false,
            error: null,
          });
        } catch {
          get().logout();
          set({ isLoading: false });
        }
      },

      clearError: () => set({ error: null }),

      setAuth: (response) => {
        void getInstanceClient()
          .internalAuthManager.updateState(response)
          .then(() => {
            set(authSliceFromResponse(response));
          });
      },
    }),
    {
      name: 'auth-storage',
      partialize: (state) => ({
        user: state.user,
        account: state.account,
        isAuthenticated: state.isAuthenticated,
      }),
    },
  ),
);
