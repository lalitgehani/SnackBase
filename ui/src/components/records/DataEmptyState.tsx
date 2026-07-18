/**
 * Data tab empty-state variants with Schema / Rules / filter CTAs.
 */

import { Database, Filter, Search, Table2, Shield } from 'lucide-react';
import { Button } from '@/components/ui/button';

export type DataEmptyVariant = 'no-schema' | 'no-records' | 'filtered' | 'search';

export interface DataEmptyStateProps {
  variant: DataEmptyVariant;
  collectionName: string;
  onCreateRecord?: () => void;
  onClearFilters?: () => void;
  onClearSearch?: () => void;
  onOpenSchema?: () => void;
  onOpenRules?: () => void;
}

export default function DataEmptyState({
  variant,
  collectionName,
  onCreateRecord,
  onClearFilters,
  onClearSearch,
  onOpenSchema,
  onOpenRules,
}: DataEmptyStateProps) {
  if (variant === 'no-schema') {
    return (
      <div
        className="py-12 text-center"
        data-testid="data-empty-no-schema"
      >
        <Database className="mx-auto mb-4 h-12 w-12 text-muted-foreground opacity-50" />
        <h3 className="mb-2 text-lg font-medium">No schema defined</h3>
        <p className="mb-4 text-muted-foreground">
          This collection has no fields defined yet. Add fields to the schema to
          start creating records.
        </p>
        {onOpenSchema && (
          <Button
            variant="default"
            onClick={onOpenSchema}
            className="gap-2"
            data-testid="data-empty-open-schema"
          >
            <Table2 className="h-4 w-4" />
            Open Schema
          </Button>
        )}
      </div>
    );
  }

  if (variant === 'filtered') {
    return (
      <div
        className="py-12 text-center"
        data-testid="data-empty-filtered"
      >
        <Filter className="mx-auto mb-4 h-12 w-12 text-muted-foreground opacity-50" />
        <h3 className="mb-2 text-lg font-medium">No records match your filters</h3>
        <p className="mb-4 text-muted-foreground">
          Try adjusting or removing your filters to see more records.
        </p>
        {onClearFilters && (
          <Button
            variant="outline"
            onClick={onClearFilters}
            data-testid="data-empty-clear-filters"
          >
            Clear Filters
          </Button>
        )}
      </div>
    );
  }

  if (variant === 'search') {
    return (
      <div className="py-12 text-center" data-testid="data-empty-search">
        <Search className="mx-auto mb-4 h-12 w-12 text-muted-foreground opacity-50" />
        <h3 className="mb-2 text-lg font-medium">No records match your search</h3>
        <p className="mb-4 text-muted-foreground">
          Try a different search term or clear the search to see all records.
        </p>
        <div className="flex flex-wrap items-center justify-center gap-2">
          {onClearSearch && (
            <Button
              variant="outline"
              onClick={onClearSearch}
              data-testid="data-empty-clear-search"
            >
              Clear Search
            </Button>
          )}
          {onCreateRecord && (
            <Button
              onClick={onCreateRecord}
              className="gap-2"
              data-testid="data-empty-create-record"
            >
              Create Record
            </Button>
          )}
        </div>
      </div>
    );
  }

  // no-records
  return (
    <div className="py-12 text-center" data-testid="data-empty-no-records">
      <Database className="mx-auto mb-4 h-12 w-12 text-muted-foreground opacity-50" />
      <h3 className="mb-2 text-lg font-medium">No records yet</h3>
      <p className="mb-4 text-muted-foreground">
        Get started by creating your first record in{' '}
        <strong>{collectionName}</strong>.
      </p>
      <div className="flex flex-wrap items-center justify-center gap-2">
        {onCreateRecord && (
          <Button
            onClick={onCreateRecord}
            className="gap-2"
            data-testid="data-empty-create-record"
          >
            Create Record
          </Button>
        )}
        {onOpenSchema && (
          <Button
            variant="outline"
            onClick={onOpenSchema}
            className="gap-2"
            data-testid="data-empty-open-schema"
          >
            <Table2 className="h-4 w-4" />
            Open Schema
          </Button>
        )}
      </div>
      {onOpenRules && (
        <p className="mt-6 text-sm text-muted-foreground">
          Expected data but see none?{' '}
          <button
            type="button"
            onClick={onOpenRules}
            className="inline-flex items-center gap-1 font-medium text-primary underline-offset-2 hover:underline"
            data-testid="data-empty-open-rules"
          >
            <Shield className="h-3.5 w-3.5" />
            Check access rules
          </button>
        </p>
      )}
    </div>
  );
}
