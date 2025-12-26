/**
 * Accounts management page - placeholder
 */

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Users } from 'lucide-react';

export default function AccountsPage() {
    return (
        <div className="space-y-6">
            <div>
                <h1 className="text-3xl font-bold">Accounts</h1>
                <p className="text-muted-foreground mt-2">Manage tenant accounts</p>
            </div>

            <Card>
                <CardHeader>
                    <CardTitle className="flex items-center gap-2">
                        <Users className="h-5 w-5 text-primary" />
                        Account Management
                    </CardTitle>
                    <CardDescription>
                        Coming in Phase 3.3
                    </CardDescription>
                </CardHeader>
                <CardContent>
                    <p className="text-muted-foreground">
                        This page will allow you to view, create, edit, and delete tenant accounts.
                        Features will include account listing, search, filtering, and detailed account views.
                    </p>
                </CardContent>
            </Card>
        </div>
    );
}
