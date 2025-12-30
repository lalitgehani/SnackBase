/**
 * Accounts API service
 * Handles API calls for account management
 */

import { apiClient } from "@/lib/api";

export interface Account {
  id: string;
  account_code: string;
  slug: string;
  name: string;
  created_at: string;
  updated_at: string;
}

export interface AccountListItem extends Account {
  user_count: number;
  status: string;
}

export interface AccountListResponse {
  items: AccountListItem[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
}

export interface AccountDetail extends Account {
  user_count: number;
  collections_used: string[];
}

export interface CreateAccountData {
  name: string;
  slug?: string;
}

export interface UpdateAccountData {
  name: string;
}

export interface AccountUser {
  id: string;
  email: string;
  role: string;
  is_active: boolean;
  created_at: string;
}

export interface AccountUsersResponse {
  items: AccountUser[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
}

export interface GetAccountsParams {
  page?: number;
  page_size?: number;
  sort_by?: string;
  sort_order?: "asc" | "desc";
  search?: string;
}

/**
 * Get list of accounts with pagination and search
 */
export const getAccounts = async (
  params: GetAccountsParams = {}
): Promise<AccountListResponse> => {
  const response = await apiClient.get<AccountListResponse>("/accounts", {
    params,
  });
  return response.data;
};

/**
 * Get account by ID
 */
export const getAccountById = async (
  accountId: string
): Promise<AccountDetail> => {
  const response = await apiClient.get<AccountDetail>(`/accounts/${accountId}`);
  return response.data;
};

/**
 * Create a new account
 */
export const createAccount = async (
  data: CreateAccountData
): Promise<AccountDetail> => {
  const response = await apiClient.post<AccountDetail>("/accounts", data);
  return response.data;
};

/**
 * Update an account
 */
export const updateAccount = async (
  accountId: string,
  data: UpdateAccountData
): Promise<AccountDetail> => {
  const response = await apiClient.put<AccountDetail>(
    `/accounts/${accountId}`,
    data
  );
  return response.data;
};

/**
 * Delete an account
 */
export const deleteAccount = async (accountId: string): Promise<void> => {
  await apiClient.delete(`/accounts/${accountId}`);
};

/**
 * Get users in an account
 */
export const getAccountUsers = async (
  accountId: string,
  page: number = 1,
  page_size: number = 25
): Promise<AccountUsersResponse> => {
  const response = await apiClient.get<AccountUsersResponse>(
    `/accounts/${accountId}/users`,
    {
      params: { page, page_size },
    }
  );
  return response.data;
};
