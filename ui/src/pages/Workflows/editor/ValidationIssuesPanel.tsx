/**
 * Lists graph validation issues; click focuses the related node.
 */

import { AlertCircle, AlertTriangle, X } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { cn } from '@/lib/utils';
import type { ValidationIssue } from './graphValidation';

interface Props {
    issues: ValidationIssue[];
    onSelectIssue: (issue: ValidationIssue) => void;
    onDismiss?: () => void;
    className?: string;
}

export function ValidationIssuesPanel({
    issues,
    onSelectIssue,
    onDismiss,
    className,
}: Props) {
    if (issues.length === 0) return null;

    const errors = issues.filter((i) => i.severity === 'error');
    const warnings = issues.filter((i) => i.severity === 'warning');

    return (
        <div
            className={cn(
                'border-b bg-muted/30 px-4 py-2 shrink-0 max-h-36 overflow-y-auto',
                className,
            )}
            data-testid="workflow-validation-panel"
            role="region"
            aria-label="Validation issues"
        >
            <div className="flex items-center justify-between gap-2 mb-1.5">
                <p className="text-xs font-medium text-muted-foreground">
                    {errors.length > 0 && (
                        <span className="text-destructive mr-2">
                            {errors.length} error{errors.length === 1 ? '' : 's'}
                        </span>
                    )}
                    {warnings.length > 0 && (
                        <span className="text-amber-600 dark:text-amber-400">
                            {warnings.length} warning{warnings.length === 1 ? '' : 's'}
                        </span>
                    )}
                    {errors.length === 0 && warnings.length > 0 && (
                        <span className="ml-1 font-normal">— save is allowed</span>
                    )}
                    {errors.length > 0 && (
                        <span className="ml-1 font-normal">— fix errors to save</span>
                    )}
                </p>
                {onDismiss && (
                    <Button
                        variant="ghost"
                        size="icon"
                        className="h-6 w-6"
                        onClick={onDismiss}
                        aria-label="Dismiss validation panel"
                    >
                        <X className="h-3.5 w-3.5" />
                    </Button>
                )}
            </div>
            <ul className="space-y-1">
                {issues.map((issue) => (
                    <li key={issue.id}>
                        <button
                            type="button"
                            className={cn(
                                'w-full text-left text-xs flex items-start gap-1.5 rounded px-1.5 py-1',
                                'hover:bg-muted transition-colors',
                                issue.nodeId && 'cursor-pointer',
                            )}
                            onClick={() => onSelectIssue(issue)}
                            data-testid={`validation-issue-${issue.id}`}
                        >
                            {issue.severity === 'error' ? (
                                <AlertCircle className="h-3.5 w-3.5 text-destructive shrink-0 mt-0.5" />
                            ) : (
                                <AlertTriangle className="h-3.5 w-3.5 text-amber-600 dark:text-amber-400 shrink-0 mt-0.5" />
                            )}
                            <span
                                className={
                                    issue.severity === 'error'
                                        ? 'text-destructive'
                                        : 'text-amber-800 dark:text-amber-200'
                                }
                            >
                                {issue.message}
                            </span>
                        </button>
                    </li>
                ))}
            </ul>
        </div>
    );
}

export default ValidationIssuesPanel;
