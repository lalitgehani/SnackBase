/**
 * Accounts API service
 */
import type { SnackBaseClient } from '@snackbase/sdk';
import { createServiceHook } from '@/lib/snackbase/createServiceHook';
import { bindService } from '@/lib/snackbase/bindService';

export interface Account {
  id: string; account_code: string; slug: string; name: string;
  created_at: string; updated_at: string;
}
export interface AccountListItem extends Account { user_count: number; status: string; }
export interface AccountListResponse {
  items: AccountListItem[]; total: number; page: number; page_size: number; total_pages: number;
}
export interface AccountDetail extends Account { user_count: number; collections_used: string[]; }
export interface CreateAccountData { name: string; slug?: string; }
export interface UpdateAccountData { name: string; }
export interface AccountUser {
  id: string; email: string; role: string; is_active: boolean; created_at: string;
}
export interface AccountUsersResponse {
  items: AccountUser[]; total: number; page: number; page_size: number; total_pages: number;
}
export interface GetAccountsParams {
  page?: number; page_size?: number; sort_by?: string; sort_order?: 'asc' | 'desc'; search?: string;
}

export function createAccountsService(client: SnackBaseClient) {
  return {
    getAccounts: (params: GetAccountsParams = {}) => client.accounts.list(params),
    getAccountById: (accountId: string) => client.accounts.get(accountId),
    createAccount: (data: CreateAccountData) => client.accounts.create(data),
    updateAccount: (accountId: string, data: UpdateAccountData) => client.accounts.update(accountId, data),
    deleteAccount: async (accountId: string) => { await client.accounts.delete(accountId); },
    getAccountUsers: (accountId: string, page = 1, page_size = 25) =>
      client.accounts.getUsers(accountId, { page, page_size }),
  };
}

export const useAccountsService = createServiceHook(createAccountsService);
const accountsService = bindService(createAccountsService);
export const getAccounts = accountsService.getAccounts;
export const getAccountById = accountsService.getAccountById;
export const createAccount = accountsService.createAccount;
export const updateAccount = accountsService.updateAccount;
export const deleteAccount = accountsService.deleteAccount;
export const getAccountUsers = accountsService.getAccountUsers;
