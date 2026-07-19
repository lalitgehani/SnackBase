export const HOOK_EVENTS = [
  { value: 'records.create', label: 'records.create — Record created' },
  { value: 'records.update', label: 'records.update — Record updated' },
  { value: 'records.delete', label: 'records.delete — Record deleted' },
  { value: 'auth.login', label: 'auth.login — User logged in' },
  { value: 'auth.register', label: 'auth.register — User registered' },
] as const;

export const ACTION_TYPES = [
  { value: 'send_webhook', label: 'Send Webhook' },
  { value: 'send_email', label: 'Send Email' },
  { value: 'create_record', label: 'Create Record' },
  { value: 'update_record', label: 'Update Record' },
  { value: 'delete_record', label: 'Delete Record' },
  { value: 'enqueue_job', label: 'Enqueue Job' },
] as const;

export type ActionTypeValue = (typeof ACTION_TYPES)[number]['value'];
