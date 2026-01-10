// Auth Types
export interface UserInfo {
  id: string;
  email: string;
  role: string;
  is_active: boolean;
  email_verified?: boolean;
  created_at: string;
}

export interface AccountInfo {
  id: string;
  slug: string;
  name: string;
  created_at: string;
}

export interface RegisterResponse {
  message: string;
  account: AccountInfo;
  user: UserInfo;
}

export interface AuthResponse {
  token: string;
  refresh_token: string;
  expires_in: number;
  account: AccountInfo;
  user: UserInfo;
}

export interface LoginRequest {
  account: string;
  email: string;
  password: string;
}

export interface RegisterRequest {
  account_name: string;
  account_slug?: string;
  email: string;
  password: string;
}

// OAuth Types
export interface OAuthAuthorizeRequest {
  account?: string;
  redirect_uri: string;
  state?: string;
}

export interface OAuthAuthorizeResponse {
  authorization_url: string;
  state: string;
  provider: string;
}

export interface OAuthCallbackRequest {
  code: string;
  state: string;
  redirect_uri: string;
}

export interface OAuthCallbackResponse extends AuthResponse {
  is_new_user: boolean;
  is_new_account: boolean;
}

// Todo Types
export type Priority = 'low' | 'medium' | 'high';

export interface Todo {
  id: string;
  title: string;
  description: string | null;
  completed: boolean;
  priority: Priority;
  account_id: string;
  created_at: string;
  created_by: string;
  updated_at: string;
  updated_by: string;
}

export interface TodoInput {
  title: string;
  description?: string;
  priority?: Priority;
  completed?: boolean;
}

export interface TodosResponse {
  items: Todo[];
  total: number;
  skip: number;
  limit: number;
}
