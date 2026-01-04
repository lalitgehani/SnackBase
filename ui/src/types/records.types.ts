/**
 * Records types
 * Type definitions for record CRUD operations
 */

export type RecordData = Record<string, unknown>;

export interface RecordDetail {
	id: string;
	account_id: string;
	created_at: string;
	updated_at: string;
	created_by: string;
	updated_by: string;
	[key: string]: unknown; // Dynamic fields from schema
}

export interface RecordListItem {
	id: string;
	created_at: string;
	updated_at: string;
	account_name?: string;
	[key: string]: unknown; // Dynamic fields from schema
}

export interface RecordListResponse {
	items: RecordListItem[];
	total: number;
	skip: number;
	limit: number;
}

export interface FormFieldState {
	value: unknown;
	error: string | null;
	touched: boolean;
}

export interface RecordFormState {
	fields: Record<string, FormFieldState>;
	isValid: boolean;
}

export interface GetRecordsParams {
	collection: string;
	skip?: number;
	limit?: number;
	sort?: string;
	fields?: string;
	[key: string]: unknown; // For filter params
}

// Backend validation error format
export interface ValidationErrorDetail {
	field?: string;
	message: string;
	code?: string;
}

export interface ValidationErrorResponse {
	error: string;
	details: ValidationErrorDetail[];
}

// PII masking display helpers
export interface PiiMaskConfig {
	type: string;
	maskFn: (value: string) => string;
}

export const PII_MASK_FUNCTIONS: Record<string, (value: string) => string> = {
	email: (value: string) => {
		const [local, domain] = value.split('@');
		if (!domain) return '***@***.***';
		if (local.length <= 2) return `${local[0]}***@${domain}`;
		return `${local[0]}${local[1]}***@${domain}`;
	},
	phone: (value: string) => {
		// Mask all but last 4 digits
		return value.replace(/\d(?=\d{4})/g, '*');
	},
	name: (value: string) => {
		const parts = value.trim().split(/\s+/);
		return parts.map(p => p.length > 1 ? p[0] + '*'.repeat(p.length - 1) : p).join(' ');
	},
	ssn: (value: string) => {
		// Show last 4 digits only
		if (value.length <= 4) return value;
		return '***-**-' + value.slice(-4);
	},
	full: (value: string) => '*'.repeat(value.length),
	custom: (value: string) => '*'.repeat(Math.min(value.length, 8)),
};
