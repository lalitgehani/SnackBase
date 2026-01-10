import { apiClient as api } from '@/lib/api';

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
  token: string;
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

export const getInvitations = async (status?: string, account_id?: string): Promise<InvitationListResponse> => {
  const params: Record<string, string> = {};
  if (status) {
    params.status_filter = status;
  }
  if (account_id) {
    params.account_id = account_id;
  }
  
  const response = await api.get<InvitationListResponse>('/invitations', { params });
  return response.data;
};

export const createInvitation = async (data: InvitationCreateRequest): Promise<Invitation> => {
  const response = await api.post<Invitation>('/invitations', data);
  return response.data;
};

export const cancelInvitation = async (invitationId: string): Promise<void> => {
  await api.delete(`/invitations/${invitationId}`);
};

export const resendInvitation = async (invitationId: string): Promise<{ message: string }> => {
  const response = await api.post<{ message: string }>(`/invitations/${invitationId}/resend`);
  return response.data;
};
