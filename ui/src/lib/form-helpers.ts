/**
 * Form helper utilities for dynamic record forms
 */

import type { FieldDefinition } from '@/services/collections.service';
import type { RecordData, FormFieldState, RecordFormState } from '@/types/records.types';

/**
 * Initialize form state from schema
 */
export function initializeFormState(
	schema: FieldDefinition[],
	initialValues?: RecordData,
): RecordFormState {
	const fields: Record<string, FormFieldState> = {};

	for (const field of schema) {
		const initialValue =
			initialValues?.[field.name] ?? field.default ?? getDefaultValueForType(field.type);
		fields[field.name] = {
			value: initialValue,
			error: null,
			touched: false,
		};
	}

	return { fields, isValid: true };
}

/**
 * Get default value for a field type
 */
export function getDefaultValueForType(type: string): unknown {
	switch (type) {
		case 'boolean':
			return false;
		case 'number':
			return 0;
		case 'json':
			return '{}';
		case 'reference':
			return null;
		case 'datetime':
			return '';
		default:
			return '';
	}
}

/**
 * Validate a single field value
 */
export function validateFieldValue(field: FieldDefinition, value: unknown): string | null {
	// Skip validation if field is not required and value is empty
	if (!field.required && isEmpty(value)) {
		return null;
	}

	// Required field validation
	if (field.required && isEmpty(value)) {
		return `${field.name} is required`;
	}

	// Type-specific validation
	if (value !== null && value !== undefined && value !== '') {
		switch (field.type) {
			case 'email':
				if (typeof value === 'string' && !isValidEmail(value)) {
					return 'Invalid email format';
				}
				break;

			case 'url':
				if (typeof value === 'string' && !isValidUrl(value)) {
					return 'Invalid URL format';
				}
				break;

			case 'json':
				if (typeof value === 'string' && !isValidJson(value)) {
					return 'Invalid JSON format';
				}
				break;

			case 'number':
				if (isNaN(Number(value))) {
					return 'Must be a valid number';
				}
				break;

			case 'datetime':
				if (typeof value === 'string' && !isValidDatetime(value)) {
					return 'Invalid datetime format';
				}
				break;

			case 'reference':
				if (typeof value === 'string' && value.trim() === '') {
					return 'Reference cannot be empty';
				}
				break;
		}
	}

	return null;
}

/**
 * Validate all fields in a form
 */
export function validateFormState(
	formState: RecordFormState,
	schema: FieldDefinition[],
): RecordFormState {
	let isValid = true;

	for (const field of schema) {
		const fieldState = formState.fields[field.name];
		if (!fieldState) continue;

		const error = validateFieldValue(field, fieldState.value);
		fieldState.error = error;
		fieldState.touched = true;

		if (error) {
			isValid = false;
		}
	}

	return { ...formState, isValid };
}

/**
 * Check if value is empty
 */
function isEmpty(value: unknown): boolean {
	return value === null || value === undefined || value === '';
}

/**
 * Validate email format
 */
function isValidEmail(email: string): boolean {
	return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email);
}

/**
 * Validate URL format
 */
function isValidUrl(url: string): boolean {
	try {
		new URL(url);
		return true;
	} catch {
		return false;
	}
}

/**
 * Validate JSON format
 */
function isValidJson(str: string): boolean {
	try {
		JSON.parse(str);
		return true;
	} catch {
		return false;
	}
}

/**
 * Validate datetime format (ISO 8601 or datetime-local format)
 */
function isValidDatetime(value: string): boolean {
	if (!value) return false;
	// Try parsing as date
	const date = new Date(value);
	return !isNaN(date.getTime());
}

/**
 * Format field value for display
 */
export function formatFieldValue(value: unknown, fieldType: string): string {
	if (value === null || value === undefined || value === '') {
		return '';
	}

	switch (fieldType) {
		case 'boolean':
			return value ? 'Yes' : 'No';
		case 'datetime':
			return typeof value === 'string' || typeof value === 'number' || value instanceof Date 
				? new Date(value as string | number | Date).toLocaleString() 
				: '';
		case 'json':
			if (typeof value === 'string') {
				return value;
			}
			try {
				return JSON.stringify(value, null, 2);
			} catch {
				return String(value);
			}
		default:
			return String(value);
	}
}

/**
 * Convert datetime-local input value to ISO string
 */
export function datetimeLocalToIso(value: string): string {
	if (!value) return '';
	const date = new Date(value);
	return date.toISOString();
}

/**
 * Convert ISO string to datetime-local input value
 */
export function isoToDatetimeLocal(value: string): string {
	if (!value) return '';
	const date = new Date(value);
	// Return format: YYYY-MM-DDTHH:mm
	const year = date.getFullYear();
	const month = String(date.getMonth() + 1).padStart(2, '0');
	const day = String(date.getDate()).padStart(2, '0');
	const hours = String(date.getHours()).padStart(2, '0');
	const minutes = String(date.getMinutes()).padStart(2, '0');
	return `${year}-${month}-${day}T${hours}:${minutes}`;
}

/**
 * Get display value for a record field
 */
export function getFieldDisplayValue(
	record: RecordData,
	fieldName: string,
	fieldType: string,
): string {
	const value = record[fieldName];
	return formatFieldValue(value, fieldType);
}

/**
 * Check if field should show as masked (PII)
 */
export function shouldMaskField(field: FieldDefinition, hasPiiAccess: boolean): boolean {
	return field.pii === true && !hasPiiAccess;
}

/**
 * Mask a PII value
 */
export function maskPiiValue(value: string, maskType: string): string {
	const maskFn = PII_MASK_FUNCTIONS[maskType] || PII_MASK_FUNCTIONS.full;
	return maskFn(value);
}

// Import PII mask functions from types
const PII_MASK_FUNCTIONS: Record<string, (value: string) => string> = {
	email: (value: string) => {
		const [local, domain] = value.split('@');
		if (!domain) return '***@***.***';
		if (local.length <= 2) return `${local[0]}***@${domain}`;
		return `${local[0]}${local[1]}***@${domain}`;
	},
	phone: (value: string) => {
		return value.replace(/\d(?=\d{4})/g, '*');
	},
	name: (value: string) => {
		const parts = value.trim().split(/\s+/);
		return parts.map((p) => (p.length > 1 ? p[0] + '*'.repeat(p.length - 1) : p)).join(' ');
	},
	ssn: (value: string) => {
		if (value.length <= 4) return value;
		return '***-**-' + value.slice(-4);
	},
	full: (value: string) => '*'.repeat(value.length),
	custom: (value: string) => '*'.repeat(Math.min(value.length, 8)),
};
