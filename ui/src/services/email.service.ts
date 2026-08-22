import type { SnackBaseClient } from '@snackbase/sdk';
import { createServiceHook } from '@/lib/snackbase/createServiceHook';
import { bindService } from '@/lib/snackbase/bindService';

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

export function createEmailService(client: SnackBaseClient) {
  return {
    listEmailTemplates: (params?: {
      template_type?: string;
      locale?: string;
      account_id?: string;
      enabled?: boolean;
    }) => client.emailTemplates.list(params),
    getEmailTemplate: (id: string) => client.emailTemplates.get(id),
    updateEmailTemplate: (id: string, data: EmailTemplateUpdate) =>
      client.emailTemplates.update(id, data),
    renderEmailTemplate: (data: EmailTemplateRenderRequest) => client.emailTemplates.render(data),
    sendTestEmail: (id: string, data: EmailTemplateTestRequest) =>
      client.emailTemplates.sendTest(
        id,
        data.recipient_email,
        data.variables ?? {},
        data.provider,
      ),
    listEmailLogs: (params?: {
      status_filter?: string;
      template_type?: string;
      start_date?: string;
      end_date?: string;
      page?: number;
      page_size?: number;
    }) => client.emailTemplates.listLogs(params),
    getEmailLog: (id: string) => client.emailTemplates.getLog(id),
  };
}

export const useEmailService = createServiceHook(createEmailService);
export const emailService = bindService(createEmailService);
