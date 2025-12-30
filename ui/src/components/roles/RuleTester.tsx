/**
 * Rule Tester component
 * Test permission rules with sample context data
 */

import { useState } from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import { Badge } from '@/components/ui/badge';
import { Separator } from '@/components/ui/separator';
import { Play, CheckCircle, XCircle, AlertCircle, Loader2 } from 'lucide-react';
import { testRule } from '@/services/roles.service';

interface RuleContext {
  user: {
    id: string;
    email: string;
    role: string;
  };
  account: {
    id: string;
  };
  record: Record<string, unknown>;
}

interface RuleTesterProps {
  initialRule?: string;
  onRuleChange?: (rule: string) => void;
}

const EXAMPLE_CONTEXTS: Record<string, RuleContext> = {
  admin: {
    user: { id: 'user_admin001', email: 'admin@example.com', role: 'admin' },
    account: { id: 'AB1234' },
    record: { id: 'rec_001', title: 'Test Post', status: 'published', created_by: 'user_admin001' },
  },
  editor: {
    user: { id: 'user_editor001', email: 'editor@example.com', role: 'editor' },
    account: { id: 'AB1234' },
    record: { id: 'rec_002', title: 'Draft Post', status: 'draft', created_by: 'user_editor001' },
  },
  viewer: {
    user: { id: 'user_viewer001', email: 'viewer@example.com', role: 'viewer' },
    account: { id: 'AB1234' },
    record: { id: 'rec_003', title: 'Public Post', status: 'published', created_by: 'user_admin001' },
  },
};

const EXAMPLE_RULES = [
  '@has_role("admin")',
  '@has_role("editor") or @owns_record()',
  'user.id == record.created_by',
  'status in ["draft", "pending"] and @owns_record()',
  '@has_role("admin") or (user.role == "editor" and record.status == "draft")',
];

export default function RuleTester({ initialRule = '', onRuleChange }: RuleTesterProps) {
  const [rule, setRule] = useState(initialRule);
  const [context, setContext] = useState<RuleContext>(EXAMPLE_CONTEXTS.editor);
  const [rawRecord, setRawRecord] = useState(JSON.stringify(EXAMPLE_CONTEXTS.editor.record, null, 2));
  const [testing, setTesting] = useState(false);
  const [result, setResult] = useState<{ allowed: boolean; error: string | null; evaluation_details: string | null } | null>(null);

  const handleRuleChange = (newRule: string) => {
    setRule(newRule);
    onRuleChange?.(newRule);
  };

  const handleContextFieldChange = (field: string, value: string) => {
    if (field.startsWith('user.')) {
      const userField = field.split('.')[1];
      setContext((prev) => ({
        ...prev,
        user: { ...prev.user, [userField]: value },
      }));
    } else if (field.startsWith('account.')) {
      const accountField = field.split('.')[1];
      setContext((prev) => ({
        ...prev,
        account: { ...prev.account, [accountField]: value },
      }));
    }
  };

  const handleRecordChange = (json: string) => {
    setRawRecord(json);
    try {
      const parsed = JSON.parse(json);
      setContext((prev) => ({ ...prev, record: parsed }));
    } catch {
      // Invalid JSON, don't update context
    }
  };

  const handleLoadExample = (exampleKey: string) => {
    const exampleContext = EXAMPLE_CONTEXTS[exampleKey];
    if (exampleContext) {
      setContext(exampleContext);
      setRawRecord(JSON.stringify(exampleContext.record, null, 2));
    }
  };

  const handleTestRule = async () => {
    setTesting(true);
    setResult(null);

    try {
      const response = await testRule(rule, context as any);
      setResult(response);
    } catch (error: unknown) {
      const err = error as { response?: { data?: { detail?: string } }; message?: string };
      setResult({
        allowed: false,
        error: err.response?.data?.detail || err.message || 'Failed to test rule',
        evaluation_details: null,
      });
    } finally {
      setTesting(false);
    }
  };

  return (
    <div className="grid gap-6 md:grid-cols-2">
      {/* Left Panel: Rule and Context */}
      <div className="space-y-4">
        {/* Rule Input */}
        <Card>
          <CardHeader>
            <CardTitle className="text-lg">Rule Expression</CardTitle>
            <CardDescription>Enter the rule you want to test</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <Textarea
              value={rule}
              onChange={(e) => handleRuleChange(e.target.value)}
              placeholder='e.g., @has_role("admin") or user.id == record.created_by'
              className="font-mono text-sm"
              rows={3}
            />

            {/* Example Rules */}
            <div className="space-y-2">
              <Label className="text-xs text-muted-foreground">Example Rules</Label>
              <div className="flex flex-wrap gap-2">
                {EXAMPLE_RULES.map((exampleRule) => (
                  <Badge
                    key={exampleRule}
                    variant="outline"
                    className="cursor-pointer hover:bg-secondary"
                    onClick={() => handleRuleChange(exampleRule)}
                  >
                    {exampleRule}
                  </Badge>
                ))}
              </div>
            </div>
          </CardContent>
        </Card>

        {/* Context Builder */}
        <Card>
          <CardHeader>
            <CardTitle className="text-lg">Test Context</CardTitle>
            <CardDescription>Define the context for testing</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            {/* Example Contexts */}
            <div className="flex gap-2">
              <Button
                type="button"
                variant="outline"
                size="sm"
                onClick={() => handleLoadExample('admin')}
              >
                Admin Context
              </Button>
              <Button
                type="button"
                variant="outline"
                size="sm"
                onClick={() => handleLoadExample('editor')}
              >
                Editor Context
              </Button>
              <Button
                type="button"
                variant="outline"
                size="sm"
                onClick={() => handleLoadExample('viewer')}
              >
                Viewer Context
              </Button>
            </div>

            <Separator />

            {/* User Context */}
            <div className="space-y-3">
              <Label className="text-sm font-medium">User Context</Label>
              <div className="grid gap-2">
                <div>
                  <Label htmlFor="user-id" className="text-xs text-muted-foreground">
                    user.id
                  </Label>
                  <Input
                    id="user-id"
                    value={context.user.id}
                    onChange={(e) => handleContextFieldChange('user.id', e.target.value)}
                    placeholder="user_123"
                  />
                </div>
                <div>
                  <Label htmlFor="user-email" className="text-xs text-muted-foreground">
                    user.email
                  </Label>
                  <Input
                    id="user-email"
                    type="email"
                    value={context.user.email}
                    onChange={(e) => handleContextFieldChange('user.email', e.target.value)}
                    placeholder="user@example.com"
                  />
                </div>
                <div>
                  <Label htmlFor="user-role" className="text-xs text-muted-foreground">
                    user.role
                  </Label>
                  <Input
                    id="user-role"
                    value={context.user.role}
                    onChange={(e) => handleContextFieldChange('user.role', e.target.value)}
                    placeholder="admin"
                  />
                </div>
              </div>
            </div>

            <Separator />

            {/* Account Context */}
            <div>
              <Label htmlFor="account-id" className="text-sm font-medium">
                Account Context
              </Label>
              <Input
                id="account-id"
                value={context.account.id}
                onChange={(e) => handleContextFieldChange('account.id', e.target.value)}
                placeholder="AB1234"
                className="mt-2"
              />
            </div>

            <Separator />

            {/* Record Context */}
            <div>
              <Label htmlFor="record-json" className="text-sm font-medium">
                Record Context (JSON)
              </Label>
              <Textarea
                id="record-json"
                value={rawRecord}
                onChange={(e) => handleRecordChange(e.target.value)}
                className="font-mono text-xs mt-2"
                rows={6}
                placeholder='{"id": "rec_001", "status": "published"}'
              />
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Right Panel: Results */}
      <div>
        <Card className="sticky top-4">
          <CardHeader>
            <CardTitle className="text-lg">Test Result</CardTitle>
            <CardDescription>Click "Test Rule" to see the result</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <Button
              onClick={handleTestRule}
              disabled={!rule.trim() || testing}
              className="w-full"
              size="lg"
            >
              {testing ? (
                <>
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                  Testing...
                </>
              ) : (
                <>
                  <Play className="mr-2 h-4 w-4" />
                  Test Rule
                </>
              )}
            </Button>

            {result && (
              <div className="space-y-4">
                <Separator />

                {/* Result Status */}
                <div
                  className={`flex items-center gap-3 p-4 rounded-lg border ${result.error
                      ? 'bg-destructive/10 border-destructive/20'
                      : result.allowed
                        ? 'bg-green-500/10 border-green-500/20'
                        : 'bg-orange-500/10 border-orange-500/20'
                    }`}
                >
                  {result.error ? (
                    <AlertCircle className="h-8 w-8 text-destructive shrink-0" />
                  ) : result.allowed ? (
                    <CheckCircle className="h-8 w-8 text-green-600 shrink-0" />
                  ) : (
                    <XCircle className="h-8 w-8 text-orange-600 shrink-0" />
                  )}
                  <div>
                    <p className="font-medium">
                      {result.error ? 'Error' : result.allowed ? 'Allowed' : 'Denied'}
                    </p>
                    <p className="text-sm text-muted-foreground">
                      {result.error || `The rule evaluates to ${result.allowed}`}
                    </p>
                  </div>
                </div>

                {/* Evaluation Details */}
                {result.evaluation_details && (
                  <div>
                    <Label className="text-sm font-medium">Evaluation Details</Label>
                    <pre className="mt-2 p-3 bg-muted rounded-md text-xs overflow-x-auto">
                      {result.evaluation_details}
                    </pre>
                  </div>
                )}

                {/* Context Used */}
                <div>
                  <Label className="text-sm font-medium">Context Used</Label>
                  <pre className="mt-2 p-3 bg-muted rounded-md text-xs overflow-x-auto">
                    {JSON.stringify(context, null, 2)}
                  </pre>
                </div>
              </div>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
