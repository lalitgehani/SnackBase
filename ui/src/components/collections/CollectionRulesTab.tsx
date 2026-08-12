/**
 * Collection access rules editor — first-class Rules tab content (Phase 3).
 * Semantics: null = locked (403), "" = public, expression = custom filter.
 */

import { useCallback, useEffect, useMemo, useState } from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Separator } from '@/components/ui/separator';
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert';
import {
  Globe,
  Info,
  Lock,
  RefreshCw,
  Save,
  Shield,
  ShieldAlert,
  ShieldCheck,
} from 'lucide-react';
import RuleEditor from './RuleEditor';
import FieldPermissionSelector from './FieldPermissionSelector';
import RuleTesterDialog from './RuleTesterDialog';
import {
  getCustomOperations,
  getLockedOperations,
  getPublicOperations,
  isRulesDirty,
  toRulesSnapshot,
  type RulesSnapshot,
} from './rulesHelpers';
import {
  getCollectionRules,
  updateCollectionRules,
  type Collection,
  type CollectionRule,
  type UpdateCollectionRulesData,
} from '@/services/collections.service';
import { handleApiError } from '@/lib/api';
import { useToast } from '@/hooks/use-toast';

interface CollectionRulesTabProps {
  collection: Collection;
  /** When true, do not fetch or edit rules (non-superadmin). */
  readOnly?: boolean;
  /** Called after a successful save so list badges (has_public_access) refresh. */
  onRulesSaved?: () => void;
  /** Optional public badge from list API when readOnly. */
  hasPublicAccess?: boolean;
}

export default function CollectionRulesTab({
  collection,
  readOnly = false,
  onRulesSaved,
  hasPublicAccess = false,
}: CollectionRulesTabProps) {
  const { toast } = useToast();
  const [baseline, setBaseline] = useState<RulesSnapshot | null>(null);
  const [draft, setDraft] = useState<RulesSnapshot | null>(null);
  const [meta, setMeta] = useState<Pick<
    CollectionRule,
    'id' | 'collection_id' | 'created_at' | 'updated_at'
  > | null>(null);
  const [loading, setLoading] = useState(!readOnly);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const [testerOpen, setTesterOpen] = useState(false);
  const [testingExpression, setTestingExpression] = useState('');

  const fetchRules = useCallback(async () => {
    if (readOnly) return;
    setLoading(true);
    setError(null);
    try {
      const data = await getCollectionRules(collection.name);
      const snapshot = toRulesSnapshot(data);
      setBaseline(snapshot);
      setDraft(snapshot);
      setMeta({
        id: data.id,
        collection_id: data.collection_id,
        created_at: data.created_at,
        updated_at: data.updated_at,
      });
    } catch (err) {
      setError(handleApiError(err));
      setBaseline(null);
      setDraft(null);
    } finally {
      setLoading(false);
    }
  }, [collection.name, readOnly]);

  useEffect(() => {
    void fetchRules();
  }, [fetchRules]);

  const isDirty = useMemo(() => {
    if (!draft || !baseline) return false;
    return isRulesDirty(draft, baseline);
  }, [draft, baseline]);

  const handleUpdateRule = (
    field: keyof RulesSnapshot,
    value: string | null,
  ) => {
    if (!draft || readOnly) return;
    setDraft({ ...draft, [field]: value });
    setError(null);
  };

  const handleDiscard = () => {
    if (!baseline) return;
    setDraft({ ...baseline });
    setError(null);
  };

  const handleSave = async () => {
    if (!draft || !isDirty || readOnly) return;
    setSaving(true);
    setError(null);

    const updateData: UpdateCollectionRulesData = {
      list_rule: draft.list_rule,
      view_rule: draft.view_rule,
      create_rule: draft.create_rule,
      update_rule: draft.update_rule,
      delete_rule: draft.delete_rule,
      list_fields: draft.list_fields,
      view_fields: draft.view_fields,
      create_fields: draft.create_fields,
      update_fields: draft.update_fields,
    };

    try {
      const saved = await updateCollectionRules(collection.name, updateData);
      const snapshot = toRulesSnapshot(saved);
      setBaseline(snapshot);
      setDraft(snapshot);
      setMeta({
        id: saved.id,
        collection_id: saved.collection_id,
        created_at: saved.created_at,
        updated_at: saved.updated_at,
      });
      toast({
        title: 'Rules saved',
        description: 'Access rules updated for this collection.',
      });
      onRulesSaved?.();
    } catch (err) {
      // Keep dirty draft so the user can retry after 403/network errors.
      setError(handleApiError(err));
    } finally {
      setSaving(false);
    }
  };

  const openTester = (expression: string | null) => {
    setTestingExpression(expression || '');
    setTesterOpen(true);
  };

  if (readOnly) {
    return (
      <div className="space-y-4" data-testid="rules-readonly">
        <header>
          <h2 className="text-xl font-bold">Access Rules</h2>
          <p className="text-sm text-muted-foreground">
            Collection API visibility is controlled by operation rules.
          </p>
        </header>

        {hasPublicAccess && (
          <Alert className="border-amber-300 bg-amber-50 dark:bg-amber-950/20 dark:border-amber-800">
            <Globe className="h-4 w-4 text-amber-600 dark:text-amber-400" />
            <AlertTitle className="text-amber-800 dark:text-amber-400">
              Public access enabled
            </AlertTitle>
            <AlertDescription className="text-amber-700 dark:text-amber-500">
              At least one operation allows unauthenticated access. Rate limiting
              applies.
            </AlertDescription>
          </Alert>
        )}

        <Alert data-testid="rules-superadmin-only">
          <Shield className="h-4 w-4" />
          <AlertTitle>Managed by superadmins</AlertTitle>
          <AlertDescription className="space-y-2">
            <p>
              Access rules (list / view / create / update / delete) can only be
              edited by superadmins. Contact a superadmin to change who can access
              this collection via the API.
            </p>
            <p className="text-muted-foreground">
              Data is always multi-tenant: rows are isolated by{' '}
              <code className="font-mono text-xs">account_id</code>. Rules control
              API visibility within that isolation; they are not a Postgres RLS
              toggle.
            </p>
          </AlertDescription>
        </Alert>
      </div>
    );
  }

  if (loading) {
    return (
      <div className="flex flex-col items-center justify-center space-y-4 py-20">
        <RefreshCw className="h-8 w-8 animate-spin text-muted-foreground" />
        <p className="text-sm text-muted-foreground">Loading collection rules...</p>
      </div>
    );
  }

  if (error && !draft) {
    return (
      <div className="rounded-lg border border-destructive/20 bg-destructive/5 p-8 text-center">
        <ShieldAlert className="mx-auto mb-4 h-10 w-10 text-destructive" />
        <h3 className="text-lg font-semibold text-destructive">
          Failed to load rules
        </h3>
        <p className="mt-2 text-sm text-muted-foreground">{error}</p>
        <Button onClick={() => void fetchRules()} variant="outline" className="mt-4">
          Try Again
        </Button>
      </div>
    );
  }

  if (!draft) return null;

  const allFieldNames = collection.schema
    .map((f) => f.name)
    .concat(['id', 'created_at', 'updated_at', 'created_by', 'account_id']);

  const publicOps = getPublicOperations(draft);
  const lockedOps = getLockedOperations(draft);
  const customOps = getCustomOperations(draft);

  return (
    <div className="relative space-y-6 pb-20" data-testid="collection-rules-tab">
      <header className="flex items-center justify-between gap-3">
        <div>
          <h2 className="text-xl font-bold">Access Rules</h2>
          <p className="text-sm text-muted-foreground">
            Define who can list, view, create, update, or delete records
            {isDirty ? ' · unsaved changes' : ''}
          </p>
        </div>
        <div className="flex items-center gap-3">
          {!isDirty && meta && (
            <div className="flex items-center gap-2 text-sm font-medium text-muted-foreground">
              <ShieldCheck className="h-4 w-4" />
              Saved
            </div>
          )}
        </div>
      </header>

      <Alert data-testid="rules-access-education">
        <Info className="h-4 w-4" />
        <AlertTitle>How access works</AlertTitle>
        <AlertDescription className="space-y-2 text-sm">
          <p>
            Every collection is a <strong>global table</strong> shared across
            accounts. Row isolation is always on via{' '}
            <code className="font-mono text-xs">account_id</code>. Access rules
            control API visibility on top of that — not a Postgres RLS toggle.
          </p>
          <ul className="list-disc space-y-1 pl-5 text-muted-foreground">
            <li>
              <strong className="text-foreground">Locked</strong> (default):
              operation is denied for non-superadmin clients (HTTP 403). Superadmins
              bypass rules.
            </li>
            <li>
              <strong className="text-foreground">Public</strong>: anyone including
              unauthenticated users may perform the operation (rate limiting
              applies).
            </li>
            <li>
              <strong className="text-foreground">Custom</strong>: requires
              authentication; the expression filters rows (list/view) or validates
              writes (create/update). A filter that matches no rows returns an empty
              list — a locked list returns 403.
            </li>
          </ul>
        </AlertDescription>
      </Alert>

      <div
        className="flex flex-wrap gap-2 text-sm"
        data-testid="rules-status-strip"
      >
        {lockedOps.length > 0 && (
          <span className="inline-flex items-center gap-1.5 rounded-md border px-2.5 py-1 text-muted-foreground">
            <Lock className="h-3.5 w-3.5" />
            Locked: {lockedOps.join(', ')}
          </span>
        )}
        {publicOps.length > 0 && (
          <span className="inline-flex items-center gap-1.5 rounded-md border border-green-500/40 bg-green-50 px-2.5 py-1 text-green-700 dark:bg-green-950/30 dark:text-green-400">
            <Globe className="h-3.5 w-3.5" />
            Public: {publicOps.join(', ')}
          </span>
        )}
        {customOps.length > 0 && (
          <span className="inline-flex items-center gap-1.5 rounded-md border border-blue-500/40 bg-blue-50 px-2.5 py-1 text-blue-700 dark:bg-blue-950/30 dark:text-blue-400">
            <Shield className="h-3.5 w-3.5" />
            Custom: {customOps.join(', ')}
          </span>
        )}
      </div>

      {error && (
        <div className="rounded-lg border border-destructive/20 bg-destructive/10 p-4 text-sm text-destructive">
          {error}
        </div>
      )}

      {publicOps.length > 0 && (
        <Alert className="border-amber-300 bg-amber-50 dark:bg-amber-950/20 dark:border-amber-800">
          <Globe className="h-4 w-4 text-amber-600 dark:text-amber-400" />
          <AlertTitle className="text-amber-800 dark:text-amber-400">
            Public access enabled
          </AlertTitle>
          <AlertDescription className="text-amber-700 dark:text-amber-500">
            This collection allows unauthenticated access for:{' '}
            <strong>{publicOps.join(', ')}</strong>. Rate limiting applies.
          </AlertDescription>
        </Alert>
      )}

      <div className="grid gap-6">
        <Card>
          <CardHeader>
            <CardTitle>Access rules by operation</CardTitle>
            <CardDescription>
              Filter or validation expressions for each API operation. Defaults
              are locked until you open them for clients.
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-8">
            <RuleEditor
              label="List Rule"
              description="Filter applied to list operations (e.g. GET /api/v1/{collection})"
              value={draft.list_rule}
              onChange={(v) => handleUpdateRule('list_rule', v)}
              onTest={() => openTester(draft.list_rule)}
            />
            <Separator />
            <RuleEditor
              label="View Rule"
              description="Filter applied to single record access"
              value={draft.view_rule}
              onChange={(v) => handleUpdateRule('view_rule', v)}
              onTest={() => openTester(draft.view_rule)}
            />
            <Separator />
            <RuleEditor
              label="Create Rule"
              description="Validation applied during record creation"
              value={draft.create_rule}
              onChange={(v) => handleUpdateRule('create_rule', v)}
              onTest={() => openTester(draft.create_rule)}
              placeholder="e.g. @request.auth.id != ''"
            />
            <Separator />
            <RuleEditor
              label="Update Rule"
              description="Filter/validation applied during record updates"
              value={draft.update_rule}
              onChange={(v) => handleUpdateRule('update_rule', v)}
              onTest={() => openTester(draft.update_rule)}
            />
            <Separator />
            <RuleEditor
              label="Delete Rule"
              description="Filter applied to record deletions"
              value={draft.delete_rule}
              onChange={(v) => handleUpdateRule('delete_rule', v)}
              onTest={() => openTester(draft.delete_rule)}
            />
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Field-level permissions</CardTitle>
            <CardDescription>
              Control which fields are visible or modifiable for each operation.
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-8">
            <FieldPermissionSelector
              label="List Fields"
              description="Fields returned in list results"
              value={draft.list_fields}
              fields={allFieldNames}
              onChange={(v) => handleUpdateRule('list_fields', v)}
            />
            <Separator />
            <FieldPermissionSelector
              label="View Fields"
              description="Fields returned in single record view"
              value={draft.view_fields}
              fields={allFieldNames}
              onChange={(v) => handleUpdateRule('view_fields', v)}
            />
            <Separator />
            <FieldPermissionSelector
              label="Create Fields"
              description="Fields allowed in the creation request body"
              value={draft.create_fields}
              fields={allFieldNames}
              onChange={(v) => handleUpdateRule('create_fields', v)}
            />
            <Separator />
            <FieldPermissionSelector
              label="Update Fields"
              description="Fields allowed in the update request body"
              value={draft.update_fields}
              fields={allFieldNames}
              onChange={(v) => handleUpdateRule('update_fields', v)}
            />
          </CardContent>
        </Card>
      </div>

      {isDirty && !saving && (
        <div
          className="sticky bottom-0 z-10 -mx-2 flex flex-wrap items-center justify-between gap-3 rounded-lg border bg-background px-4 py-3 shadow-md"
          data-testid="rules-dirty-bar"
        >
          <p className="text-sm font-medium">Unsaved rule changes</p>
          <div className="flex gap-2">
            <Button type="button" variant="outline" size="sm" onClick={handleDiscard}>
              Discard
            </Button>
            <Button
              type="button"
              size="sm"
              className="gap-2"
              onClick={() => void handleSave()}
            >
              <Save className="h-4 w-4" />
              Save Rules
            </Button>
          </div>
        </div>
      )}

      {saving && (
        <div className="sticky bottom-0 z-10 -mx-2 flex items-center justify-center gap-2 rounded-lg border bg-background px-4 py-3 shadow-md">
          <RefreshCw className="h-4 w-4 animate-spin" />
          <span className="text-sm font-medium">Saving rules…</span>
        </div>
      )}

      <RuleTesterDialog
        open={testerOpen}
        onOpenChange={setTesterOpen}
        ruleExpression={testingExpression}
        collectionName={collection.name}
      />
    </div>
  );
}
