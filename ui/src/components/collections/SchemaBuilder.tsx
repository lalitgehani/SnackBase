/**
 * Schema builder — thin wrapper around SchemaColumnTable for backward compatibility.
 * Prefer importing SchemaColumnTable for new code.
 */

export { default } from './SchemaColumnTable';
export type { SchemaColumnTableProps as SchemaBuilderProps } from './SchemaColumnTable';
