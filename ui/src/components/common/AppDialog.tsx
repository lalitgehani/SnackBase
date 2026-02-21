import * as React from 'react';
import { cn } from '@/lib/utils';
import {
    Dialog,
    DialogContent,
    DialogHeader,
    DialogTitle,
    DialogDescription,
    DialogFooter,
} from '@/components/ui/dialog';

interface AppDialogProps {
    open: boolean;
    onOpenChange: (open: boolean) => void;
    title: React.ReactNode;
    description?: React.ReactNode;
    children: React.ReactNode;
    footer?: React.ReactNode;
    /** Override max-width, e.g. "sm:max-w-xl" or "max-w-4xl". Defaults to "sm:max-w-lg". */
    className?: string;
    /** Override default body padding and scroll behavior. Defaults to "px-6 py-4 overflow-y-auto". */
    bodyClassName?: string;
}

/**
 * Shared dialog shell used by all CRUD/form dialogs.
 * Provides a consistent layout: fixed header, scrollable body, fixed footer.
 * Matches the add/update provider dialog pattern.
 */
export function AppDialog({
    open,
    onOpenChange,
    title,
    description,
    children,
    footer,
    className,
    bodyClassName,
}: AppDialogProps) {
    return (
        <Dialog open={open} onOpenChange={onOpenChange}>
            <DialogContent
                className={cn(
                    'p-0 overflow-hidden flex flex-col max-h-[90vh] sm:max-w-lg',
                    className
                )}
            >
                <DialogHeader className="p-6 pb-0">
                    <DialogTitle>{title}</DialogTitle>
                    {description && (
                        <DialogDescription>{description}</DialogDescription>
                    )}
                </DialogHeader>

                <div className={cn("flex-1 overflow-y-auto px-6 py-4 min-h-0", bodyClassName)}>
                    {children}
                </div>

                {footer && (
                    <DialogFooter className="px-6 pb-6 pt-4 border-t">
                        {footer}
                    </DialogFooter>
                )}
            </DialogContent>
        </Dialog>
    );
}
