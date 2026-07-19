/**
 * Client-side hook templates for the create flow.
 */

import type { HookFormState } from '../hookFormState';
import { DEFAULT_FORM, newAction } from '../hookFormState';

export interface HookTemplateMeta {
  id: string;
  name: string;
  description: string;
  actionCount: number;
}

export interface HookTemplate extends HookTemplateMeta {
  build: () => HookFormState;
}

const emptyTemplate: HookTemplate = {
  id: 'empty',
  name: 'Empty hook',
  description: 'Manual trigger with no actions. Add at least one action before saving.',
  actionCount: 0,
  build: () => ({
    ...DEFAULT_FORM,
    name: '',
    description: '',
    triggerType: 'manual',
    event: 'records.create',
    collection: '',
    condition: '',
    actions: [],
    enabled: true,
  }),
};

const notifyOnCreate: HookTemplate = {
  id: 'notify-on-create',
  name: 'Notify on record create',
  description: 'When a record is created, call a webhook with the record payload.',
  actionCount: 1,
  build: () => ({
    ...DEFAULT_FORM,
    name: 'Notify on record create',
    description: 'Send a webhook when a new record is created',
    triggerType: 'event',
    event: 'records.create',
    collection: '',
    condition: '',
    actions: [
      {
        ...newAction('send_webhook'),
        url: 'https://example.com/webhook',
        method: 'POST',
        body_template: '{"id": "{{record.id}}", "user": "{{auth.user_id}}"}',
      },
    ],
    enabled: true,
  }),
};

const auditLogWrite: HookTemplate = {
  id: 'audit-log-write',
  name: 'Write activity log',
  description: 'On record create, write a row to an activity_logs collection.',
  actionCount: 1,
  build: () => ({
    ...DEFAULT_FORM,
    name: 'Write activity log',
    description: 'Create an activity log entry when a record is created',
    triggerType: 'event',
    event: 'records.create',
    collection: '',
    condition: '',
    actions: [
      {
        ...newAction('create_record'),
        collection: 'activity_logs',
        data: JSON.stringify(
          {
            message: 'Record {{record.id}} created by {{auth.email}}',
            source: 'hook',
          },
          null,
          2,
        ),
      },
    ],
    enabled: true,
  }),
};

const welcomeEmail: HookTemplate = {
  id: 'welcome-email',
  name: 'Welcome on register',
  description: 'Send a welcome email when a user registers.',
  actionCount: 1,
  build: () => ({
    ...DEFAULT_FORM,
    name: 'Welcome on register',
    description: 'Email new users after registration',
    triggerType: 'event',
    event: 'auth.register',
    collection: '',
    condition: '',
    actions: [
      {
        ...newAction('send_email'),
        to: '{{auth.email}}',
        subject: 'Welcome!',
        body: 'Hello {{auth.email}}, welcome to the platform.',
      },
    ],
    enabled: true,
  }),
};

export const HOOK_TEMPLATES: HookTemplate[] = [
  emptyTemplate,
  notifyOnCreate,
  auditLogWrite,
  welcomeEmail,
];
