import type { SnackBaseClient } from '@snackbase/sdk';
import { createServiceHook } from '@/lib/snackbase/createServiceHook';
import { bindService } from '@/lib/snackbase/bindService';
import type { AuthResponse } from '@/types/auth.types';

export interface Invitation {
  id: string;
  account_id: string;
  account_code: string;
  email: string;
  invited_by: string;
  expires_at: string;
  accepted_at: string | null;
  created_at: string;
  email_sent: boolean;
  email_sent_at: string | null;
  status: 'pending' | 'accepted' | 'expired' | 'cancelled';
  /**
   * Present only on create and resend responses. The server stores a hash of
   * the token, so a listing cannot hand one out; resending issues a new one.
   */
  token: string | null;
}

export interface InvitationListResponse {
  invitations: Invitation[];
  total: number;
}

export interface InvitationCreateRequest {
  email: string;
  role_id?: string;
  groups?: string[];
  account_id?: string;
}

export interface InvitationPublicResponse {
  email: string;
  account_name: string;
  invited_by_name: string;
  expires_at: string;
  is_valid: boolean;
}

export interface InvitationAcceptRequest {
  password?: string;
}

export function createInvitationsService(client: SnackBaseClient) {
  return {
    getInvitations: (status?: string, account_id?: string): Promise<InvitationListResponse> => {
      const params: Record<string, string> = {};
      if (status) params.status_filter = status;
      if (account_id) params.account_id = account_id;
      return client.invitations.list(params);
    },
    createInvitation: (data: InvitationCreateRequest) => client.invitations.create(data),
    cancelInvitation: async (invitationId: string) => {
      await client.invitations.cancel(invitationId);
    },
    resendInvitation: (invitationId: string) => client.invitations.resend(invitationId),
    getInvitation: (token: string): Promise<InvitationPublicResponse> =>
      client.invitations.getPublic(token),
    acceptInvitation: (token: string, data: InvitationAcceptRequest): Promise<AuthResponse> =>
      client.invitations.accept(token, data.password) as Promise<AuthResponse>,
  };
}

export const useInvitationsService = createServiceHook(createInvitationsService);

const invitationsService = bindService(createInvitationsService);
export const getInvitations = invitationsService.getInvitations;
export const createInvitation = invitationsService.createInvitation;
export const cancelInvitation = invitationsService.cancelInvitation;
export const resendInvitation = invitationsService.resendInvitation;
export const getInvitation = invitationsService.getInvitation;
export const acceptInvitation = invitationsService.acceptInvitation;
