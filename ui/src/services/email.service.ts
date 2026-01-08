import { apiClient as api } from '@/lib/api';

export interface EmailTemplate {
  id: string;
  account_id: string;
  template_type: string;
  locale: string;
  subject: string;
  html_body: string;
  text_body: string;
  enabled: boolean;
  is_builtin: boolean;
  created_at: string;
  updated_at: string;
}

export interface EmailTemplateUpdate {
  subject?: string;
  html_body?: string;
  text_body?: string;
  enabled?: boolean;
}

export interface EmailTemplateTestRequest {
  recipient_email: string;
  variables?: Record<string, string>;
}

export interface EmailTemplateRenderRequest {
  template_type: string;
  variables: Record<string, string>;
  locale?: string;
  account_id?: string;
}

export interface EmailTemplateRenderResponse {
  subject: string;
  html_body: string;
  text_body: string;
}

export const emailService = {
  listEmailTemplates: async (params?: {
    template_type?: string;
    locale?: string;
    account_id?: string;
    enabled?: boolean;
  }): Promise<EmailTemplate[]> => {
    const queryParams = new URLSearchParams();
    if (params?.template_type) queryParams.append('template_type', params.template_type);
    if (params?.locale) queryParams.append('locale', params.locale);
    if (params?.account_id) queryParams.append('account_id', params.account_id);
    if (params?.enabled !== undefined) queryParams.append('enabled', params.enabled.toString());

    const response = await api.get<EmailTemplate[]>(
      `/admin/email/templates?${queryParams.toString()}`
    );
    return response.data;
  },

  getEmailTemplate: async (id: string): Promise<EmailTemplate> => {
    const response = await api.get<EmailTemplate>(`/admin/email/templates/${id}`);
    return response.data;
  },

  updateEmailTemplate: async (
    id: string,
    data: EmailTemplateUpdate
  ): Promise<EmailTemplate> => {
    const response = await api.put<EmailTemplate>(`/admin/email/templates/${id}`, data);
    return response.data;
  },

  renderEmailTemplate: async (
    data: EmailTemplateRenderRequest
  ): Promise<EmailTemplateRenderResponse> => {
    const response = await api.post<EmailTemplateRenderResponse>(
      '/admin/email/templates/render',
      data
    );
    return response.data;
  },

  sendTestEmail: async (
    id: string,
    data: EmailTemplateTestRequest
  ): Promise<{ status: string; message: string }> => {
    const response = await api.post<{ status: string; message: string }>(
      `/admin/email/templates/${id}/test`,
      data
    );
    return response.data;
  },
};
