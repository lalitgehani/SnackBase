/**
 * Authentication types for the admin UI
 */

export interface LoginRequest {
  email: string;
  password: string;
}

export interface UserInfo {
  id: string;
  email: string;
  role: string;
  is_active: boolean;
  created_at: string;
}

export interface AccountInfo {
  id: string;
  slug: string;
  name: string;
  created_at: string;
}

export interface AuthResponse {
  token: string;
  refresh_token: string;
  expires_in: number;
  account: AccountInfo;
  user: UserInfo;
}

export interface TokenRefreshResponse {
  token: string;
  refresh_token: string;
  expires_in: number;
}

export interface CurrentUserResponse {
  user_id: string;
  account_id: string;
  email: string;
  role: string;
}
