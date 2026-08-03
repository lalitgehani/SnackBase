import { useCallback, useEffect, useState } from 'react';
import { useNavigate } from 'react-router';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Switch } from '@/components/ui/switch';
import { Skeleton } from '@/components/ui/skeleton';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';
import { FunctionSquare, Plus, RefreshCw, MoreHorizontal, Pencil, Trash2, KeyRound } from 'lucide-react';
import { functionsService, type FunctionItem } from '@/services/functions.service';
import { CreateFunctionDialog } from './CreateFunctionDialog';
import { DeleteFunctionDialog } from './DeleteFunctionDialog';
import { useToast } from '@/hooks/use-toast';

export default function FunctionsPage() {
  const { toast } = useToast();
  const navigate = useNavigate();
  const [items, setItems] = useState<FunctionItem[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [toggling, setToggling] = useState<string | null>(null);
  const [createOpen, setCreateOpen] = useState(false);
  const [deleteItem, setDeleteItem] = useState<FunctionItem | null>(null);

  const fetchList = useCallback(async () => {
    setError(null);
    try {
      const response = await functionsService.list();
      setItems(response.items);
      setTotal(response.total);
    } catch {
      setError('Failed to load functions. Please try again.');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchList();
  }, [fetchList]);

  const handleRefresh = async () => {
    setRefreshing(true);
    await fetchList();
    setRefreshing(false);
  };

  const handleToggle = async (fn: FunctionItem) => {
    setToggling(fn.id);
    try {
      const updated = await functionsService.update(fn.slug, { enabled: !fn.enabled });
      setItems((prev) => prev.map((i) => (i.id === fn.id ? updated : i)));
    } catch {
      toast({ title: 'Error', description: 'Failed to toggle function', variant: 'destructive' });
    } finally {
      setToggling(null);
    }
  };

  return (
    <div className="p-8 space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold tracking-tight flex items-center gap-3">
            <FunctionSquare className="h-8 w-8" />
            Functions
          </h1>
          <p className="text-muted-foreground mt-1">
            Deploy and run sandboxed Python handlers with pinned dependencies
          </p>
        </div>
        <div className="flex gap-2">
          <Button variant="outline" size="sm" onClick={() => navigate('/admin/functions/secrets')}>
            <KeyRound className="h-4 w-4 mr-2" />
            Secrets
          </Button>
          <Button variant="outline" size="sm" onClick={handleRefresh} disabled={refreshing}>
            <RefreshCw className={`h-4 w-4 mr-2 ${refreshing ? 'animate-spin' : ''}`} />
            Refresh
          </Button>
          <Button size="sm" onClick={() => setCreateOpen(true)}>
            <Plus className="h-4 w-4 mr-2" />
            New Function
          </Button>
        </div>
      </div>

      {!loading && items.length > 0 && (
        <div className="flex gap-4 text-sm text-muted-foreground">
          <span>{total} total</span>
          <span className="text-green-600 dark:text-green-400">
            {items.filter((i) => i.enabled).length} enabled
          </span>
        </div>
      )}

      {error ? (
        <div className="text-center py-8">
          <p className="text-destructive">{error}</p>
          <Button variant="outline" className="mt-4" onClick={fetchList}>
            Try Again
          </Button>
        </div>
      ) : loading ? (
        <div className="space-y-2">
          <Skeleton className="h-10 w-full" />
          <Skeleton className="h-10 w-full" />
          <Skeleton className="h-10 w-full" />
        </div>
      ) : items.length === 0 ? (
        <div className="text-center py-16 border rounded-lg">
          <FunctionSquare className="h-12 w-12 mx-auto text-muted-foreground mb-4" />
          <h3 className="text-lg font-medium">No functions yet</h3>
          <p className="text-muted-foreground mt-1 mb-4">
            Create a function from a template and deploy Python in minutes.
          </p>
          <Button onClick={() => setCreateOpen(true)}>
            <Plus className="h-4 w-4 mr-2" />
            New Function
          </Button>
        </div>
      ) : (
        <div className="border rounded-lg">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Name</TableHead>
                <TableHead>Slug</TableHead>
                <TableHead>Auth</TableHead>
                <TableHead>Status</TableHead>
                <TableHead>Enabled</TableHead>
                <TableHead>Updated</TableHead>
                <TableHead className="w-[60px]" />
              </TableRow>
            </TableHeader>
            <TableBody>
              {items.map((fn) => (
                <TableRow
                  key={fn.id}
                  className="cursor-pointer"
                  onClick={() => navigate(`/admin/functions/${fn.slug}`)}
                >
                  <TableCell className="font-medium">{fn.name}</TableCell>
                  <TableCell className="font-mono text-sm">{fn.slug}</TableCell>
                  <TableCell>
                    {fn.auth_required ? (
                      <Badge variant="secondary">Required</Badge>
                    ) : (
                      <Badge variant="outline">Public</Badge>
                    )}
                  </TableCell>
                  <TableCell>
                    <Badge variant={fn.status === 'ACTIVE' ? 'default' : 'outline'}>{fn.status}</Badge>
                  </TableCell>
                  <TableCell onClick={(e) => e.stopPropagation()}>
                    <Switch
                      checked={fn.enabled}
                      disabled={toggling === fn.id}
                      onCheckedChange={() => handleToggle(fn)}
                    />
                  </TableCell>
                  <TableCell className="text-sm text-muted-foreground">
                    {new Date(fn.updated_at).toLocaleString()}
                  </TableCell>
                  <TableCell onClick={(e) => e.stopPropagation()}>
                    <DropdownMenu>
                      <DropdownMenuTrigger asChild>
                        <Button variant="ghost" size="icon">
                          <MoreHorizontal className="h-4 w-4" />
                        </Button>
                      </DropdownMenuTrigger>
                      <DropdownMenuContent align="end">
                        <DropdownMenuItem onClick={() => navigate(`/admin/functions/${fn.slug}`)}>
                          <Pencil className="h-4 w-4 mr-2" />
                          Edit
                        </DropdownMenuItem>
                        <DropdownMenuSeparator />
                        <DropdownMenuItem
                          className="text-destructive"
                          onClick={() => setDeleteItem(fn)}
                        >
                          <Trash2 className="h-4 w-4 mr-2" />
                          Delete
                        </DropdownMenuItem>
                      </DropdownMenuContent>
                    </DropdownMenu>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </div>
      )}

      <CreateFunctionDialog
        open={createOpen}
        onOpenChange={setCreateOpen}
        onCreated={(slug) => {
          fetchList();
          navigate(`/admin/functions/${slug}`);
        }}
      />
      <DeleteFunctionDialog
        functionItem={deleteItem}
        open={!!deleteItem}
        onOpenChange={(open) => !open && setDeleteItem(null)}
        onDeleted={fetchList}
      />
    </div>
  );
}
