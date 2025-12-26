/**
 * Roles & permissions management page - placeholder
 */

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Shield } from 'lucide-react';

export default function RolesPage() {
    return (
        <div className="space-y-6">
            <div>
                <h1 className="text-3xl font-bold">Roles & Permissions</h1>
                <p className="text-muted-foreground mt-2">Manage access control and permissions</p>
            </div>

            <Card>
                <CardHeader>
                    <CardTitle className="flex items-center gap-2">
                        <Shield className="h-5 w-5 text-primary" />
                        Permission Management
                    </CardTitle>
                    <CardDescription>
                        Coming in Phase 3.5
                    </CardDescription>
                </CardHeader>
                <CardContent>
                    <p className="text-muted-foreground">
                        This page will provide a visual permission editor with a permission matrix,
                        rule builder, and testing tools. You'll be able to create roles, define permissions,
                        and test permission rules with sample data.
                    </p>
                </CardContent>
            </Card>
        </div>
    );
}
