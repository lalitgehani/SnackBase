import React, { useState, useEffect } from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Separator } from '@/components/ui/separator';
import { RefreshCw, Save, ShieldAlert, ShieldCheck } from 'lucide-react';
import RuleEditor from './RuleEditor';
import FieldPermissionSelector from './FieldPermissionSelector';
import RuleTesterDialog from './RuleTesterDialog';
import {
    getCollectionRules,
    updateCollectionRules,
    type Collection,
    type CollectionRule,
    type UpdateCollectionRulesData
} from '@/services/collections.service';
import { handleApiError } from '@/lib/api';

interface CollectionRulesTabProps {
    collection: Collection;
}

export default function CollectionRulesTab({ collection }: CollectionRulesTabProps) {
    const [rules, setRules] = useState<CollectionRule | null>(null);
    const [loading, setLoading] = useState(true);
    const [saving, setSaving] = useState(false);
    const [error, setError] = useState<string | null>(null);
    const [success, setSuccess] = useState(false);

    // Tester state
    const [testerOpen, setTesterOpen] = useState(false);
    const [testingExpression, setTestingExpression] = useState('');

    const fetchRules = async () => {
        setLoading(true);
        setError(null);
        try {
            const data = await getCollectionRules(collection.name);
            setRules(data);
        } catch (err) {
            setError(handleApiError(err));
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        fetchRules();
    }, [collection.name]);

    const handleUpdateRule = (field: keyof CollectionRule, value: string | null) => {
        if (!rules) return;
        setRules({ ...rules, [field]: value });
        setSuccess(false);
    };

    const handleSave = async () => {
        if (!rules) return;
        setSaving(true);
        setError(null);
        setSuccess(false);

        const updateData: UpdateCollectionRulesData = {
            list_rule: rules.list_rule,
            view_rule: rules.view_rule,
            create_rule: rules.create_rule,
            update_rule: rules.update_rule,
            delete_rule: rules.delete_rule,
            list_fields: rules.list_fields,
            view_fields: rules.view_fields,
            create_fields: rules.create_fields,
            update_fields: rules.update_fields,
        };

        try {
            await updateCollectionRules(collection.name, updateData);
            setSuccess(true);
            setTimeout(() => setSuccess(false), 3000);
        } catch (err) {
            setError(handleApiError(err));
        } finally {
            setSaving(false);
        }
    };

    const openTester = (expression: string | null) => {
        setTestingExpression(expression || '');
        setTesterOpen(true);
    };

    if (loading) {
        return (
            <div className="flex flex-col items-center justify-center py-20 space-y-4">
                <RefreshCw className="h-8 w-8 animate-spin text-muted-foreground" />
                <p className="text-sm text-muted-foreground">Loading collection rules...</p>
            </div>
        );
    }

    if (error && !rules) {
        return (
            <div className="p-8 text-center bg-destructive/5 border border-destructive/20 rounded-lg">
                <ShieldAlert className="h-10 w-10 mx-auto mb-4 text-destructive" />
                <h3 className="text-lg font-semibold text-destructive">Failed to load rules</h3>
                <p className="text-sm text-muted-foreground mt-2">{error}</p>
                <Button onClick={fetchRules} variant="outline" className="mt-4">
                    Try Again
                </Button>
            </div>
        );
    }

    if (!rules) return null;

    const allFieldNames = collection.schema.map(f => f.name).concat(['id', 'created_at', 'updated_at', 'created_by', 'account_id']);

    return (
        <div className="space-y-6 pb-20">
            <header className="flex items-center justify-between">
                <div>
                    <h2 className="text-xl font-bold">Access Rules</h2>
                    <p className="text-sm text-muted-foreground">Define who can list, view, create, update, or delete records.</p>
                </div>
                <div className="flex items-center gap-3">
                    {success && (
                        <div className="flex items-center gap-2 text-green-600 dark:text-green-400 text-sm font-medium">
                            <ShieldCheck className="h-4 w-4" />
                            Rules saved successfully
                        </div>
                    )}
                    <Button onClick={handleSave} disabled={saving} className="gap-2">
                        <Save className="h-4 w-4" />
                        {saving ? 'Saving...' : 'Save Rules'}
                    </Button>
                </div>
            </header>

            {error && (
                <div className="bg-destructive/10 border border-destructive/20 rounded-lg p-4 text-destructive text-sm">
                    {error}
                </div>
            )}

            <div className="grid gap-6">
                <Card>
                    <CardHeader>
                        <CardTitle>Row-Level Security (RLS)</CardTitle>
                        <CardDescription>
                            Control which rows are visible or modifiable using filter expressions.
                        </CardDescription>
                    </CardHeader>
                    <CardContent className="space-y-8">
                        <RuleEditor
                            label="List Rule"
                            description="Filter applied to list operations (e.g. GET /records/todos)"
                            value={rules.list_rule}
                            onChange={(v) => handleUpdateRule('list_rule', v)}
                            onTest={() => openTester(rules.list_rule)}
                        />
                        <Separator />
                        <RuleEditor
                            label="View Rule"
                            description="Filter applied to single record access (e.g. GET /records/todos/ID)"
                            value={rules.view_rule}
                            onChange={(v) => handleUpdateRule('view_rule', v)}
                            onTest={() => openTester(rules.view_rule)}
                        />
                        <Separator />
                        <RuleEditor
                            label="Create Rule"
                            description="Validation applied during record creation"
                            value={rules.create_rule}
                            onChange={(v) => handleUpdateRule('create_rule', v)}
                            onTest={() => openTester(rules.create_rule)}
                            placeholder="e.g. @request.auth.id != ''"
                        />
                        <Separator />
                        <RuleEditor
                            label="Update Rule"
                            description="Filter/Validation applied during record updates"
                            value={rules.update_rule}
                            onChange={(v) => handleUpdateRule('update_rule', v)}
                            onTest={() => openTester(rules.update_rule)}
                        />
                        <Separator />
                        <RuleEditor
                            label="Delete Rule"
                            description="Filter applied to record deletions"
                            value={rules.delete_rule}
                            onChange={(v) => handleUpdateRule('delete_rule', v)}
                            onTest={() => openTester(rules.delete_rule)}
                        />
                    </CardContent>
                </Card>

                <Card>
                    <CardHeader>
                        <CardTitle>Field-Level Permissions</CardTitle>
                        <CardDescription>
                            Control which fields are visible or modifiable for each operation.
                        </CardDescription>
                    </CardHeader>
                    <CardContent className="space-y-8">
                        <FieldPermissionSelector
                            label="List Fields"
                            description="Fields returned in list results"
                            value={rules.list_fields}
                            fields={allFieldNames}
                            onChange={(v) => handleUpdateRule('list_fields', v)}
                        />
                        <Separator />
                        <FieldPermissionSelector
                            label="View Fields"
                            description="Fields returned in single record view"
                            value={rules.view_fields}
                            fields={allFieldNames}
                            onChange={(v) => handleUpdateRule('view_fields', v)}
                        />
                        <Separator />
                        <FieldPermissionSelector
                            label="Create Fields"
                            description="Fields allowed in the creation request body"
                            value={rules.create_fields}
                            fields={allFieldNames}
                            onChange={(v) => handleUpdateRule('create_fields', v)}
                        />
                        <Separator />
                        <FieldPermissionSelector
                            label="Update Fields"
                            description="Fields allowed in the update request body"
                            value={rules.update_fields}
                            fields={allFieldNames}
                            onChange={(v) => handleUpdateRule('update_fields', v)}
                        />
                    </CardContent>
                </Card>
            </div>

            <RuleTesterDialog
                open={testerOpen}
                onOpenChange={setTesterOpen}
                ruleExpression={testingExpression}
                collectionName={collection.name}
            />
        </div>
    );
}
