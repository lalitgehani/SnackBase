/**
 * Audit logs viewer page - placeholder
 */

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { FileText } from 'lucide-react';

export default function AuditLogsPage() {
    return (
        <div className="space-y-6">
            <div>
                <h1 className="text-3xl font-bold">Audit Logs</h1>
                <p className="text-muted-foreground mt-2">View and export audit trail</p>
            </div>

            <Card>
                <CardHeader>
                    <CardTitle className="flex items-center gap-2">
                        <FileText className="h-5 w-5 text-primary" />
                        Audit Log Viewer
                    </CardTitle>
                    <CardDescription>
                        Coming in Phase 3.8
                    </CardDescription>
                </CardHeader>
                <CardContent>
                    <p className="text-muted-foreground">
                        This page will display GxP-compliant audit logs with filtering, search, and export capabilities.
                        You'll be able to view all data changes, user actions, and system events with full traceability.
                    </p>
                </CardContent>
            </Card>
        </div>
    );
}
