/**
 * Restore confirmation dialog (F6.3).
 *
 * Shows exactly what a restore will do and what it will discard before the
 * operator can confirm: the operator must type the archive name to enable
 * the confirm button, blocking compatibility issues disable it permanently,
 * and warning issues require an explicit "restore anyway" checkbox that
 * sends force=true.
 */
import { useEffect, useState } from 'react';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert';
import { Checkbox } from '@/components/ui/checkbox';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Button } from '@/components/ui/button';
import { backupsApi } from '@/services/backups';
import type {
  BackupEntry,
  RestoreIssue,
  RestorePreview,
} from '@/services/backups';

export interface RestoreDialogProps {
  entry: BackupEntry | null;
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onRequested?: () => void;
}

export function RestoreDialog({ entry, open, onOpenChange, onRequested }: RestoreDialogProps) {
  const [typedName, setTypedName] = useState('');
  const [force, setForce] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [phase, setPhase] = useState<'input' | 'restarting' | 'done'>('input');
  const [outcome, setOutcome] = useState<RestoreStatus | null>(null);
  const [serverError, setServerError] = useState<string | null>(null);
  const [preview, setPreview] = useState<RestorePreview | null>(null);
  const [previewError, setPreviewError] = useState<string | null>(null);

  useEffect(() => {
    if (!open) {
      setTypedName('');
      setForce(false);
      setSubmitting(false);
      setPhase('input');
      setOutcome(null);
      setServerError(null);
      setPreview(null);
      setPreviewError(null);
      return;
    }
    if (!entry) return;
    let cancelled = false;
    backupsApi
      .restorePreview(entry.name)
      .then((data) => {
        if (!cancelled) setPreview(data);
      })
      .catch(() => {
        if (!cancelled) setPreviewError('Archive could not be validated.');
      });
    return () => {
      cancelled = true;
    };
  }, [open, entry]);

  const blocking: RestoreIssue[] = preview?.blocking ?? [];
  const warnings: RestoreIssue[] = preview?.warnings ?? [];

  const nameMatches = entry !== null && typedName === entry.name;
  const confirmDisabled =
    blocking.length > 0 || !nameMatches || submitting || phase !== 'input';

  async function pollUntilInstanceReturns(): Promise<void> {
    // During the restart the instance refuses connections; treat every
    // failure as the expected path and keep probing.
    const probe = async (): Promise<boolean> => {
      try {
        await backupsApi.restoreStatus();
        return true;
      } catch {
        return false;
      }
    };
    for (let attempt = 0; attempt < 120; attempt += 1) {
      await new Promise((resolve) => setTimeout(resolve, 2000));
      if (await probe()) return;
    }
  }

  async function handleConfirm(): Promise<void> {
    if (!entry) return;
    setSubmitting(true);
    setServerError(null);
    try {
      await backupsApi.restore(entry.name, force && warnings.length > 0);
      setPhase('restarting');
      onRequested?.();
      await pollUntilInstanceReturns();
      try {
        const status = await backupsApi.restoreStatus();
        setOutcome(status);
      } catch {
        setOutcome({
          archive_name: entry.name,
          status: 'unknown',
          completed_at: '',
        });
      }
      setPhase('done');
    } catch (error) {
      const message =
        // eslint-disable-next-line @typescript-eslint/no-explicit-any
        (error as any)?.response?.data?.detail?.message ??
        // eslint-disable-next-line @typescript-eslint/no-explicit-any
        (error as any)?.response?.data?.detail ??
        'Restore request failed';
      setServerError(String(message));
    } finally {
      setSubmitting(false);
    }
  }

  if (!entry) return null;

  return (
    <Dialog open={open} onOpenChange={phase === 'restarting' ? undefined : onOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Restore {entry.name}</DialogTitle>
          <DialogDescription>
            All data created after {new Date(entry.modified).toLocaleString()} will
            be discarded, and the instance will restart to complete the restore.
          </DialogDescription>
        </DialogHeader>

        {phase === 'restarting' && (
          <Alert>
            <AlertTitle>Restarting…</AlertTitle>
            <AlertDescription>
              The restore was requested. The instance is shutting down and will
              come back with the restored data. Connection failures during the
              restart are expected.
            </AlertDescription>
          </Alert>
        )}

        {phase === 'done' && outcome && (
          <Alert>
            <AlertTitle>
              {outcome.status === 'completed' ? 'Restore completed' : `Restore ${outcome.status}`}
            </AlertTitle>
            <AlertDescription>
              {outcome.status === 'completed'
                ? `${outcome.archive_name} was restored.`
                : outcome.error ?? 'The restore outcome could not be read yet.'}
            </AlertDescription>
          </Alert>
        )}

        {phase === 'input' && (
          <>
            {previewError && (
              <Alert variant="destructive">
                <AlertDescription>{previewError}</AlertDescription>
              </Alert>
            )}
            {preview && (
              <div className="text-sm space-y-1">
                <div>
                  Created: {new Date(preview.created_at).toLocaleString()}
                </div>
                <div>
                  Source SnackBase version: {preview.source_version}
                </div>
                <div>
                  Includes files: {preview.includes_files ? 'yes' : 'no'}
                </div>
              </div>
            )}

            {blocking.map((issue) => (
              <Alert key={issue.type} variant="destructive">
                <AlertTitle>Blocking issue</AlertTitle>
                <AlertDescription>{issue.message}</AlertDescription>
              </Alert>
            ))}
            {warnings.map((issue) => (
              <Alert key={issue.type}>
                <AlertTitle>Warning</AlertTitle>
                <AlertDescription>{issue.message}</AlertDescription>
              </Alert>
            ))}
            {warnings.length > 0 && blocking.length === 0 && (
              <div className="flex items-center gap-2">
                <Checkbox
                  id="restore-anyway"
                  checked={force}
                  onCheckedChange={(checked) => setForce(checked === true)}
                />
                <Label htmlFor="restore-anyway">Restore anyway (force)</Label>
              </div>
            )}

            <div className="space-y-2">
              <Label htmlFor="restore-confirm-name">
                Type the archive name ({entry.name}) to enable Restore
              </Label>
              <Input
                id="restore-confirm-name"
                value={typedName}
                onChange={(event) => setTypedName(event.target.value)}
                autoComplete="off"
              />
            </div>
            {serverError && (
              <Alert variant="destructive">
                <AlertDescription>{serverError}</AlertDescription>
              </Alert>
            )}
          </>
        )}

        <DialogFooter>
          <Button
            variant="outline"
            onClick={() => onOpenChange(false)}
            disabled={phase === 'restarting'}
          >
            Close
          </Button>
          {phase === 'input' && (
            <Button
              variant="destructive"
              onClick={handleConfirm}
              disabled={confirmDisabled}
            >
              {submitting ? 'Requesting…' : 'Restore'}
            </Button>
          )}
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

export default RestoreDialog;
