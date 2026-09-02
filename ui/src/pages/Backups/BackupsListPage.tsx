/**
 * Backups list and actions (F6.2).
 *
 * Every archive is shown with its type badge — `Restorable` for physical,
 * `Portable` for logical — and the Restore action is disabled with an
 * explanatory tooltip for anything that is not restorable. Polling runs
 * every 5 seconds only while an operation is in flight.
 */
import { useCallback, useEffect, useRef, useState } from 'react';
import { Link } from 'react-router';
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert';
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from '@/components/ui/alert-dialog';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from '@/components/ui/card';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
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
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from '@/components/ui/tooltip';
import {
  backupsApi,
  type BackupEntry,
  type BackupListResponse,
} from '@/services/backups';
import { RestoreDialog } from './RestoreDialog';

const POLL_INTERVAL_MS = 5000;

function formatSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  const units = ['KB', 'MB', 'GB', 'TB'];
  let value = bytes / 1024;
  let unit = 0;
  while (value >= 1024 && unit < units.length - 1) {
    value /= 1024;
    unit += 1;
  }
  return `${value.toFixed(1)}${units[unit]}`;
}

export default function BackupsListPage() {
  const [data, setData] = useState<BackupListResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [createOpen, setCreateOpen] = useState(false);
  const [createName, setCreateName] = useState('');
  const [deleteTarget, setDeleteTarget] = useState<BackupEntry | null>(null);
  const [restoreTarget, setRestoreTarget] = useState<BackupEntry | null>(null);
  const [restoreOpen, setRestoreOpen] = useState(false);
  const [uploadError, setUploadError] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const refresh = useCallback(async () => {
    try {
      const response = await backupsApi.list();
      setData(response);
      setError(null);
    } catch {
      setError('Failed to load backups.');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void refresh();
  }, [refresh]);

  const active = data?.active ?? null;

  // Poll every 5 seconds only while an operation is in flight; never at rest.
  useEffect(() => {
    if (!active) return undefined;
    const timer = window.setInterval(() => {
      void refresh();
    }, POLL_INTERVAL_MS);
    return () => window.clearInterval(timer);
  }, [active, refresh]);

  async function handleCreate(): Promise<void> {
    try {
      await backupsApi.create(createName || null);
      setCreateOpen(false);
      setCreateName('');
      await refresh();
    } catch (createError) {
      setError('Failed to create backup.');
      void createError;
    }
  }

  async function handleDelete(): Promise<void> {
    if (!deleteTarget) return;
    try {
      await backupsApi.remove(deleteTarget.name);
      setDeleteTarget(null);
      await refresh();
    } catch (deleteError) {
      setError(`Failed to delete ${deleteTarget.name}.`);
      void deleteError;
    }
  }

  async function handleUpload(
    event: React.ChangeEvent<HTMLInputElement>,
  ): Promise<void> {
    const file = event.target.files?.[0];
    event.target.value = '';
    if (!file) return;
    setUploadError(null);
    try {
      await backupsApi.upload(file);
      await refresh();
    } catch (uploadError_) {
      const detail =
        // eslint-disable-next-line @typescript-eslint/no-explicit-any
        (uploadError_ as any)?.response?.data?.detail ?? 'Upload failed';
      setUploadError(String(detail));
    }
  }

  function openRestore(entry: BackupEntry): void {
    setRestoreTarget(entry);
    setRestoreOpen(true);
  }

  return (
    <div className="space-y-4 p-4">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-semibold">Backups</h1>
        <div className="flex items-center gap-2">
          <Button asChild variant="outline">
            <Link to="/admin/backups/settings">Settings</Link>
          </Button>
          <input
            ref={fileInputRef}
            type="file"
            accept=".zip"
            className="hidden"
            data-testid="backup-upload-input"
            onChange={handleUpload}
          />
          <Button variant="outline" onClick={() => fileInputRef.current?.click()}>
            Upload
          </Button>
          <Button
            onClick={() => setCreateOpen(true)}
            disabled={active !== null}
            data-testid="backup-create-button"
          >
            Create backup
          </Button>
        </div>
      </div>

      {(data?.consecutive_failures ?? 0) > 0 && (
        <Alert variant="destructive" data-testid="backup-failure-banner">
          <AlertTitle>
            Automatic backups are failing ({data?.consecutive_failures} consecutive
            failures)
          </AlertTitle>
          <AlertDescription>{data?.last_error}</AlertDescription>
        </Alert>
      )}

      {uploadError && (
        <Alert variant="destructive" data-testid="upload-error">
          <AlertTitle>Upload rejected</AlertTitle>
          <AlertDescription>{uploadError}</AlertDescription>
        </Alert>
      )}

      {error && (
        <Alert variant="destructive">
          <AlertDescription>{error}</AlertDescription>
        </Alert>
      )}

      <Card>
        <CardHeader>
          <CardTitle>Archives</CardTitle>
          <CardDescription>
            {active
              ? `${active.operation} of ${active.name} is in progress…`
              : 'Archives at the configured destination, newest first.'}
          </CardDescription>
        </CardHeader>
        <CardContent>
          <Table data-testid="backups-table">
            <TableHeader>
              <TableRow>
                <TableHead>Name</TableHead>
                <TableHead>Type</TableHead>
                <TableHead>Size</TableHead>
                <TableHead>Created</TableHead>
                <TableHead>Origin</TableHead>
                <TableHead className="text-right">Actions</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {loading && (
                <TableRow>
                  <TableCell colSpan={6}>Loading…</TableCell>
                </TableRow>
              )}
              {!loading && (data?.backups.length ?? 0) === 0 && (
                <TableRow>
                  <TableCell colSpan={6}>No backups yet.</TableCell>
                </TableRow>
              )}
              {data?.backups.map((entry) => (
                <TableRow key={entry.name} data-testid={`backup-row-${entry.name}`}>
                  <TableCell className="font-mono">{entry.name}</TableCell>
                  <TableCell>
                    {entry.restorable ? (
                      <Badge data-testid={`badge-${entry.name}`}>Restorable</Badge>
                    ) : (
                      <Badge variant="secondary" data-testid={`badge-${entry.name}`}>
                        Portable
                      </Badge>
                    )}
                  </TableCell>
                  <TableCell>{formatSize(entry.size)}</TableCell>
                  <TableCell>{new Date(entry.modified).toLocaleString()}</TableCell>
                  <TableCell>
                    {entry.is_automatic ? 'Automatic' : 'Manual'}
                  </TableCell>
                  <TableCell className="text-right">
                    <div className="flex justify-end gap-1">
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={() => void backupsApi.download(entry.name)}
                      >
                        Download
                      </Button>
                      <TooltipProvider>
                        <Tooltip>
                          <TooltipTrigger asChild>
                            <span tabIndex={entry.restorable ? -1 : 0}>
                              <Button
                                variant="outline"
                                size="sm"
                                disabled={!entry.restorable || active !== null}
                                data-testid={`restore-${entry.name}`}
                                onClick={() => openRestore(entry)}
                              >
                                Restore
                              </Button>
                            </span>
                          </TooltipTrigger>
                          {!entry.restorable && (
                            <TooltipContent>
                              Logical archives are portable exports, not
                              restorable backups. PostgreSQL disaster recovery
                              is configured on the database.
                            </TooltipContent>
                          )}
                        </Tooltip>
                      </TooltipProvider>
                      <Button
                        variant="destructive"
                        size="sm"
                        disabled={active !== null}
                        data-testid={`delete-${entry.name}`}
                        onClick={() => setDeleteTarget(entry)}
                      >
                        Delete
                      </Button>
                    </div>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </CardContent>
      </Card>

      <Dialog open={createOpen} onOpenChange={setCreateOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Create backup</DialogTitle>
            <DialogDescription>
              Leave the name empty to use the generated timestamped name.
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-2">
            <Label htmlFor="create-backup-name">Archive name (optional)</Label>
            <Input
              id="create-backup-name"
              value={createName}
              onChange={(event) => setCreateName(event.target.value)}
              placeholder="snackbase_backup_20260902020000.zip"
            />
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setCreateOpen(false)}>
              Cancel
            </Button>
            <Button onClick={handleCreate}>Create</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      <AlertDialog
        open={deleteTarget !== null}
        onOpenChange={(open) => !open && setDeleteTarget(null)}
      >
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Delete {deleteTarget?.name}?</AlertDialogTitle>
            <AlertDialogDescription>
              This permanently removes the archive from the destination. This
              action cannot be undone.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Cancel</AlertDialogCancel>
            <AlertDialogAction onClick={handleDelete}>Delete</AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>

      <RestoreDialog
        entry={restoreTarget}
        open={restoreOpen}
        onOpenChange={setRestoreOpen}
        onRequested={refresh}
      />
    </div>
  );
}
