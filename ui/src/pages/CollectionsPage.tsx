/**
 * Collections management page - placeholder
 */

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Database } from 'lucide-react';

export default function CollectionsPage() {
    return (
        <div className="space-y-6">
            <div>
                <h1 className="text-3xl font-bold">Collections</h1>
                <p className="text-muted-foreground mt-2">Manage data collections and schemas</p>
            </div>

            <Card>
                <CardHeader>
                    <CardTitle className="flex items-center gap-2">
                        <Database className="h-5 w-5 text-primary" />
                        Collection Management
                    </CardTitle>
                    <CardDescription>
                        Coming in Phase 3.4
                    </CardDescription>
                </CardHeader>
                <CardContent>
                    <p className="text-muted-foreground">
                        This page will provide a visual schema builder for creating and managing collections.
                        Features will include field definitions, type selection, validation rules, and schema migrations.
                    </p>
                </CardContent>
            </Card>
        </div>
    );
}
