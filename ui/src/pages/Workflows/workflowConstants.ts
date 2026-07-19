/**
 * Shared constants for workflow step types, actions, events, and palette.
 * Used by the visual editor (palette, properties) — not form-based step lists.
 */

export const WORKFLOW_EVENTS = [
    { value: 'records.create', label: 'records.create — Record created' },
    { value: 'records.update', label: 'records.update — Record updated' },
    { value: 'records.delete', label: 'records.delete — Record deleted' },
    { value: 'auth.login', label: 'auth.login — User logged in' },
    { value: 'auth.register', label: 'auth.register — User registered' },
] as const;

export const STEP_TYPES = [
    { value: 'action', label: 'Action' },
    { value: 'condition', label: 'Condition (branch)' },
    { value: 'wait_delay', label: 'Wait — Delay' },
    { value: 'wait_condition', label: 'Wait — Until Condition' },
    { value: 'wait_event', label: 'Wait — For Event' },
    { value: 'loop', label: 'Loop' },
    { value: 'parallel', label: 'Parallel' },
] as const;

export const ACTION_TYPES = [
    { value: 'send_webhook', label: 'Send Webhook' },
    { value: 'send_email', label: 'Send Email' },
    { value: 'create_record', label: 'Create Record' },
    { value: 'update_record', label: 'Update Record' },
    { value: 'delete_record', label: 'Delete Record' },
    { value: 'enqueue_job', label: 'Enqueue Job' },
] as const;

export type StepTypeValue = (typeof STEP_TYPES)[number]['value'];
export type ActionTypeValue = (typeof ACTION_TYPES)[number]['value'];

/** Palette groups for the left rail (trigger is not paletted). */
export interface PaletteItem {
    stepType: StepTypeValue;
    label: string;
    description: string;
}

export interface PaletteGroup {
    id: string;
    label: string;
    items: PaletteItem[];
}

export const PALETTE_GROUPS: PaletteGroup[] = [
    {
        id: 'actions',
        label: 'Actions',
        items: [
            {
                stepType: 'action',
                label: 'Action',
                description: 'Webhook, email, record CRUD, or job',
            },
        ],
    },
    {
        id: 'logic',
        label: 'Logic',
        items: [
            {
                stepType: 'condition',
                label: 'Condition',
                description: 'Branch on true / false',
            },
            {
                stepType: 'loop',
                label: 'Loop',
                description: 'Iterate over items',
            },
            {
                stepType: 'parallel',
                label: 'Parallel',
                description: 'Run branch chains concurrently',
            },
        ],
    },
    {
        id: 'wait',
        label: 'Wait',
        items: [
            {
                stepType: 'wait_delay',
                label: 'Delay',
                description: 'Wait a fixed duration',
            },
            {
                stepType: 'wait_condition',
                label: 'Until condition',
                description: 'Poll until expression is true',
            },
            {
                stepType: 'wait_event',
                label: 'For event',
                description: 'Wait for a platform event',
            },
        ],
    },
];

/** Drag-and-drop MIME / dataTransfer type for palette → canvas. */
export const PALETTE_DND_TYPE = 'application/reactflow-step-type';

/** Stable React Flow node id for the single trigger node (not a step name). */
export const TRIGGER_NODE_ID = '__trigger__';

export const DEFAULT_TRIGGER_POSITION = { x: 80, y: 120 } as const;
