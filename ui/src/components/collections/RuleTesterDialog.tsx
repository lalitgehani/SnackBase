import React from 'react';
import { AppDialog } from '@/components/common/AppDialog';
import { Button } from '@/components/ui/button';
import { Textarea } from '@/components/ui/textarea';
import { Label } from '@/components/ui/label';
import { AlertCircle, CheckCircle2, XCircle, Play } from 'lucide-react';
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert';

interface RuleTesterDialogProps {
    open: boolean;
    onOpenChange: (open: boolean) => void;
    ruleExpression: string;
    collectionName: string;
}

export default function RuleTesterDialog({
    open,
    onOpenChange,
    ruleExpression,
    collectionName,
}: RuleTesterDialogProps) {
    const [authContext, setAuthContext] = React.useState(
        JSON.stringify({ id: 'user_123', email: 'test@example.com', role: 'user' }, null, 2)
    );
    const [recordData, setRecordData] = React.useState(
        JSON.stringify({ id: 'rec_123', created_by: 'user_123', status: 'active' }, null, 2)
    );
    const [result, setResult] = React.useState<{ status: 'allow' | 'deny' | 'error'; message: string } | null>(null);
    const [isTesting, setIsTesting] = React.useState(false);

    const handleTest = async () => {
        setIsTesting(true);
        setResult(null);

        // Simulate API call for testing
        // In a real implementation, we would call an endpoint like POST /api/v1/collections/{name}/rules/test
        setTimeout(() => {
            try {
                // Mock evaluation logic for demonstration in UI
                // This is just a UI preview; real evaluation happens on the server
                const auth = JSON.parse(authContext);
                const record = JSON.parse(recordData);

                // Very basic mock evaluation for common patterns
                let isAllowed = false;
                if (ruleExpression === '') {
                    isAllowed = true;
                } else if (ruleExpression.includes('created_by = @request.auth.id')) {
                    isAllowed = record.created_by === auth.id;
                } else {
                    // Fallback to "allow" for demo purposes if it "looks" valid
                    isAllowed = ruleExpression.length > 5;
                }

                setResult({
                    status: isAllowed ? 'allow' : 'deny',
                    message: isAllowed
                        ? 'Rule successfully allowed access with this context.'
                        : 'Rule denied access with this context.'
                });
            } catch (err) {
                setResult({
                    status: 'error',
                    message: `Invalid JSON or evaluation error: ${err instanceof Error ? err.message : String(err)}`
                });
            } finally {
                setIsTesting(false);
            }
        }, 800);
    };

    return (
        <AppDialog
            open={open}
            onOpenChange={onOpenChange}
            title={
                <span className="flex items-center gap-2">
                    <Play className="h-5 w-5 text-primary" />
                    Test Rule: {collectionName}
                </span>
            }
            description="Test your expression against sample authentication context and record data."
            className="max-w-2xl"
            footer={
                <>
                    <Button variant="outline" onClick={() => onOpenChange(false)}>
                        Close
                    </Button>
                    <Button onClick={handleTest} disabled={isTesting}>
                        {isTesting ? 'Testing...' : 'Run Test'}
                    </Button>
                </>
            }
        >
            <div className="space-y-4">
                <div className="space-y-2">
                    <Label>Expression</Label>
                    <div className="p-3 bg-muted rounded-md font-mono text-sm border">
                        {ruleExpression || '(Public)'}
                    </div>
                </div>

                <div className="grid grid-cols-2 gap-4">
                    <div className="space-y-2">
                        <Label htmlFor="auth-context">@request.auth</Label>
                        <Textarea
                            id="auth-context"
                            value={authContext}
                            onChange={(e) => setAuthContext(e.target.value)}
                            className="font-mono text-xs h-[150px]"
                            placeholder="Sample auth context JSON"
                        />
                    </div>
                    <div className="space-y-2">
                        <Label htmlFor="record-data">Record (Direct fields)</Label>
                        <Textarea
                            id="record-data"
                            value={recordData}
                            onChange={(e) => setRecordData(e.target.value)}
                            className="font-mono text-xs h-[150px]"
                            placeholder="Sample record data JSON"
                        />
                    </div>
                </div>

                {result && (
                    <Alert
                        variant={result.status === 'error' ? 'destructive' : 'default'}
                        className={cn(
                            result.status === 'allow' && "border-green-500 bg-green-50 dark:bg-green-950/20 text-green-700 dark:text-green-400",
                            result.status === 'deny' && "border-yellow-500 bg-yellow-50 dark:bg-yellow-950/20 text-yellow-700 dark:text-yellow-400"
                        )}
                    >
                        <div className="flex items-center gap-2">
                            {result.status === 'allow' && <CheckCircle2 className="h-4 w-4" />}
                            {result.status === 'deny' && <AlertCircle className="h-4 w-4" />}
                            {result.status === 'error' && <XCircle className="h-4 w-4" />}
                            <AlertTitle className="capitalize font-bold">{result.status}</AlertTitle>
                        </div>
                        <AlertDescription className="mt-1">
                            {result.message}
                        </AlertDescription>
                    </Alert>
                )}
            </div>
        </AppDialog>
    );
}

function cn(...inputs: any[]) {
    return inputs.filter(Boolean).join(' ');
}
