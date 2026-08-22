/**
 * Users API service
 * Handles API calls for user management (superadmin only)
 */

import type { SnackBaseClient } from '@snackbase/sdk';
import { createServiceHook } from '@/lib/snackbase/createServiceHook';
import { bindService } from '@/lib/snackbase/bindService';

export interface User {
  id: string;
  email: string;
  account_id: string;
  account_code: string;
  account_name: string;
  role_id: number;
  role_name: string;
  is_active: boolean;
  created_at: string;
  last_login: string | null;
  email_verified: boolean;
  email_verified_at: string | null;
}

export type UserListItem = User;

export interface UserListResponse {
  total: number;
  items: UserListItem[];
}

export interface UserListParams {
  account_id?: string;
  role_id?: number;
  is_active?: boolean;
  search?: string;
  skip?: number;
  limit?: number;
  sort?: string;
}

export interface CreateUserRequest {
  email: string;
  password: string;
  account_id: string;
  role_id: number;
  is_active?: boolean;
}

export interface UpdateUserRequest {
  email?: string;
  role_id?: number;
  is_active?: boolean;
}

export interface PasswordResetRequest {
  new_password?: string;
  send_reset_link?: boolean;
}

export function createUsersService(client: SnackBaseClient) {
  return {
    getUsers: (params?: UserListParams) => client.users.list(params),
    getUser: (userId: string) => client.users.get(userId),
    createUser: (data: CreateUserRequest) => client.users.create(data),
    updateUser: (userId: string, data: UpdateUserRequest) => client.users.update(userId, data),
    resetUserPassword: (userId: string, data: PasswordResetRequest) =>
      client.users.resetPassword(userId, data),
    verifyUser: (userId: string) => client.users.verifyEmail(userId),
    resendUserVerification: (userId: string) => client.users.resendVerification(userId),
    deactivateUser: async (userId: string) => {
      await client.users.delete(userId);
    },
  };
}

export const useUsersService = createServiceHook(createUsersService);

const usersService = bindService(createUsersService);
export const getUsers = usersService.getUsers;
export const getUser = usersService.getUser;
export const createUser = usersService.createUser;
export const updateUser = usersService.updateUser;
export const resetUserPassword = usersService.resetUserPassword;
export const verifyUser = usersService.verifyUser;
export const resendUserVerification = usersService.resendUserVerification;
export const deactivateUser = usersService.deactivateUser;
