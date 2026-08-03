import { useCallback, useEffect, useState } from 'react';
import { Link } from 'react-router';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';
import { ArrowLeft, KeyRound, Plus, Trash2 } from 'lucide-react';
import { functionsService, type FunctionSecret } from '@/services/functions.service';
import { useToast } from '@/hooks/use-toast';

export default function FunctionSecretsPage() {
  const { toast } = useToast();
  const [items, setItems] = useState<FunctionSecret[]>([]);
  const [loading, setLoading] = useState(true);
  const [name, setName] = useState('');
  const [value, setValue] = useState('');
  const [saving, setSaving] = useState(false);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const res = await functionsService.listSecrets();
      setItems(res.items);
    } catch {
      toast({ title: 'Error', description: 'Failed to load secrets', variant: 'destructive' });
    } finally {
      setLoading(false);
    }
  }, [toast]);

  useEffect(() => {
    load();
  }, [load]);

  const handleSave = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!name.trim() || !value) return;
    if (name.startsWith('SNACKBASE_')) {
      toast({
        title: 'Invalid name',
        description: 'Secret names must not start with SNACKBASE_',
        variant: 'destructive',
      });
      return;
    }
    setSaving(true);
    try {
      await functionsService.upsertSecret(name.trim(), value);
      toast({ title: 'Secret saved' });
      setName('');
      setValue('');
      await load();
    } catch (err: unknown) {
      const msg =
        (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail ??
        'Failed to save secret';
      toast({ title: 'Error', description: String(msg), variant: 'destructive' });
    } finally {
      setSaving(false);
    }
  };

  const handleDelete = async (secretName: string) => {
    try {
      await functionsService.deleteSecret(secretName);
      toast({ title: 'Secret deleted' });
      await load();
    } catch {
      toast({ title: 'Error', description: 'Failed to delete secret', variant: 'destructive' });
    }
  };

  return (
    <div className="p-8 space-y-6 max-w-3xl">
      <div>
        <Button variant="ghost" size="sm" asChild className="-ml-2 mb-2">
          <Link to="/admin/functions">
            <ArrowLeft className="h-4 w-4 mr-1" />
            Functions
          </Link>
        </Button>
        <h1 className="text-3xl font-bold tracking-tight flex items-center gap-3">
          <KeyRound className="h-8 w-8" />
          Function Secrets
        </h1>
        <p className="text-muted-foreground mt-1">
          Write-only secrets injected as environment variables into function processes. Values are
          never returned by the API after save.
        </p>
      </div>

      <form onSubmit={handleSave} className="border rounded-lg p-4 space-y-3">
        <div className="grid gap-2">
          <Label htmlFor="sec-name">Name</Label>
          <Input
            id="sec-name"
            className="font-mono"
            placeholder="OPENAI_API_KEY"
            value={name}
            onChange={(e) => setName(e.target.value)}
            required
          />
        </div>
        <div className="grid gap-2">
          <Label htmlFor="sec-value">Value</Label>
          <Input
            id="sec-value"
            type="password"
            autoComplete="new-password"
            value={value}
            onChange={(e) => setValue(e.target.value)}
            required
          />
        </div>
        <Button type="submit" disabled={saving}>
          <Plus className="h-4 w-4 mr-2" />
          {saving ? 'Saving…' : 'Save secret'}
        </Button>
      </form>

      <div className="border rounded-lg">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Name</TableHead>
              <TableHead>Updated</TableHead>
              <TableHead className="w-[60px]" />
            </TableRow>
          </TableHeader>
          <TableBody>
            {loading ? (
              <TableRow>
                <TableCell colSpan={3} className="text-muted-foreground">
                  Loading…
                </TableCell>
              </TableRow>
            ) : items.length === 0 ? (
              <TableRow>
                <TableCell colSpan={3} className="text-muted-foreground text-center">
                  No secrets yet
                </TableCell>
              </TableRow>
            ) : (
              items.map((s) => (
                <TableRow key={s.id}>
                  <TableCell className="font-mono">{s.name}</TableCell>
                  <TableCell className="text-sm text-muted-foreground">
                    {new Date(s.updated_at).toLocaleString()}
                  </TableCell>
                  <TableCell>
                    <Button
                      size="icon"
                      variant="ghost"
                      onClick={() => handleDelete(s.name)}
                      aria-label={`Delete ${s.name}`}
                    >
                      <Trash2 className="h-4 w-4" />
                    </Button>
                  </TableCell>
                </TableRow>
              ))
            )}
          </TableBody>
        </Table>
      </div>
    </div>
  );
}
