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
  provider?: string;
}

export interface EmailTemplateRenderRequest {
  template_type: string;
  variables: Record<string, string>;
  locale?: string;
  account_id?: string;
  subject?: string;
  html_body?: string;
  text_body?: string;
}

export interface EmailTemplateRenderResponse {
  subject: string;
  html_body: string;
  text_body: string;
}

export interface EmailLog {
  id: string;
  account_id: string;
  template_type: string;
  recipient_email: string;
  provider: string;
  status: string;
  error_message: string | null;
  variables: Record<string, string> | null;
  sent_at: string;
}

export interface EmailLogListResponse {
  logs: EmailLog[];
  total: number;
  page: number;
  page_size: number;
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

  listEmailLogs: async (params?: {
    status_filter?: string;
    template_type?: string;
    start_date?: string;
    end_date?: string;
    page?: number;
    page_size?: number;
  }): Promise<EmailLogListResponse> => {
    const queryParams = new URLSearchParams();
    if (params?.status_filter) queryParams.append('status_filter', params.status_filter);
    if (params?.template_type) queryParams.append('template_type', params.template_type);
    if (params?.start_date) queryParams.append('start_date', params.start_date);
    if (params?.end_date) queryParams.append('end_date', params.end_date);
    if (params?.page) queryParams.append('page', params.page.toString());
    if (params?.page_size) queryParams.append('page_size', params.page_size.toString());

    const response = await api.get<EmailLogListResponse>(
      `/admin/email/logs?${queryParams.toString()}`
    );
    return response.data;
  },

  getEmailLog: async (id: string): Promise<EmailLog> => {
    const response = await api.get<EmailLog>(`/admin/email/logs/${id}`);
    return response.data;
  },
};

