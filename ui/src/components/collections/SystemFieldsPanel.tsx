/**
 * Read-only panel listing platform system fields always applied to collections.
 */

import { Lock } from 'lucide-react';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';
import { cn } from '@/lib/utils';

export const SYSTEM_FIELDS = [
  { name: 'id', type: 'TEXT', note: 'Primary key' },
  { name: 'account_id', type: 'TEXT', note: 'Tenant isolation (NOT NULL)' },
  { name: 'created_at', type: 'DATETIME', note: 'Audit' },
  { name: 'created_by', type: 'TEXT', note: 'Audit' },
  { name: 'updated_at', type: 'DATETIME', note: 'Audit' },
  { name: 'updated_by', type: 'TEXT', note: 'Audit' },
] as const;

interface SystemFieldsPanelProps {
  className?: string;
  compact?: boolean;
}

export default function SystemFieldsPanel({
  className,
  compact = false,
}: SystemFieldsPanelProps) {
  return (
    <div
      className={cn(
        'rounded-lg border border-dashed bg-muted/30',
        compact ? 'p-3' : 'p-4',
        className,
      )}
      data-testid="system-fields-panel"
    >
      <div className="mb-3 flex items-start gap-2">
        <Lock className="mt-0.5 h-4 w-4 shrink-0 text-muted-foreground" />
        <div>
          <h3 className="text-sm font-semibold">System fields</h3>
          <p className="text-xs text-muted-foreground">
            Always applied by the platform. Not editable and not part of your schema payload.
          </p>
        </div>
      </div>

      <Table>
        <TableHeader>
          <TableRow className="hover:bg-transparent">
            <TableHead className="h-8 text-xs">Name</TableHead>
            <TableHead className="h-8 text-xs">Type</TableHead>
            <TableHead className="h-8 text-xs">Notes</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {SYSTEM_FIELDS.map((field) => (
            <TableRow
              key={field.name}
              className="hover:bg-transparent text-muted-foreground"
            >
              <TableCell className="py-1.5 font-mono text-xs">
                <span className="inline-flex items-center gap-1.5">
                  <Lock className="h-3 w-3" aria-hidden />
                  {field.name}
                </span>
              </TableCell>
              <TableCell className="py-1.5 font-mono text-xs">{field.type}</TableCell>
              <TableCell className="py-1.5 text-xs">{field.note}</TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </div>
  );
}
