/**
 * Demo banner component that displays demo information and login credentials
 * Only shown when VITE_IS_DEMO environment variable is set to 'true'
 */

import { Info } from 'lucide-react';
import { Alert, AlertDescription } from '@/components/ui/alert';

export function DemoBanner() {
    const isDemo = import.meta.env.VITE_IS_DEMO === 'true';

    if (!isDemo) {
        return null;
    }

    return (
        <Alert className="rounded-none border-x-0 border-t-0 bg-amber-50 dark:bg-amber-950/20 border-amber-200 dark:border-amber-800">
            <Info className="h-4 w-4 text-amber-600 dark:text-amber-500" />
            <AlertDescription className="text-sm text-amber-900 dark:text-amber-100">
                <strong className="font-semibold">Demo Mode:</strong> This is a demo of SnackBase admin dashboard.
                The database resets every hour. Realtime data and file upload are disabled.
                <span className="ml-2">
                    To login, use Email: <code className="px-1.5 py-0.5 rounded bg-amber-100 dark:bg-amber-900/40 font-mono text-xs">admin@admin.com</code>
                    {' '}and Password: <code className="px-1.5 py-0.5 rounded bg-amber-100 dark:bg-amber-900/40 font-mono text-xs">Admin@123456</code>
                </span>
            </AlertDescription>
        </Alert>
    );
}
