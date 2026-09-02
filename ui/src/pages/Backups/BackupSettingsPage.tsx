/**
 * Backup settings page (F6.1).
 *
 * Binds the backup_settings configuration category: destination (Local/S3),
 * schedule (cron with presets and a live description), and retention. The S3
 * secret renders write-only — a masked placeholder when a value is stored,
 * sent back only when the operator enters a new one.
 */
import { useCallback, useEffect, useState } from 'react';
import { Link } from 'react-router';
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert';
import { Button } from '@/components/ui/button';
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { Skeleton } from '@/components/ui/skeleton';
import {
  backupsSettingsApi,
  type BackupSettingsValues,
} from '@/services/backups';
import { backupsApi } from '@/services/backups';
import { isPlausibleCron } from './cronCheck';

const CRON_PRESETS: { label: string; expr: string }[] = [
  { label: 'Hourly', expr: '0 * * * *' },
  { label: 'Daily at 02:00', expr: '0 2 * * *' },
  { label: 'Weekly (Sunday 02:00)', expr: '0 2 * * 0' },
  { label: 'Monthly (day 1, 02:00)', expr: '0 2 1 * *' },
];

const MASK = '••••••••';

export default function BackupSettingsPage() {
  const [values, setValues] = useState<BackupSettingsValues>({});
  const [configId, setConfigId] = useState<string | null>(null);
  const [secretStored, setSecretStored] = useState(false);
  const [secretInput, setSecretInput] = useState('');
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [saved, setSaved] = useState(false);
  const [cronDescription, setCronDescription] = useState<string | null>(null);
  const [isPostgres, setIsPostgres] = useState(false);

  useEffect(() => {
    let cancelled = false;
    backupsApi
      .list()
      .then((data) => {
        if (!cancelled) setIsPostgres(data.database_engine === 'postgresql');
      })
      .catch(() => {
        /* engine panel is informational; default to hidden */
      });
    return () => {
      cancelled = true;
    };
  }, []);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const config = await backupsSettingsApi.getConfig();
      if (!config) {
        setConfigId(null);
        setValues({ destination: 'local', cron: '', max_keep: 3 });
        return;
      }
      setConfigId(config.id);
      const stored = await backupsSettingsApi.getValues(config.id);
      const hasSecret = Boolean(
        stored.s3_secret_access_key && stored.s3_secret_access_key.length > 0,
      );
      setSecretStored(hasSecret);
      setValues({ ...stored, s3_secret_access_key: undefined });
    } catch (loadError) {
      setError('Failed to load backup settings.');
      void loadError;
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  // Live human-readable schedule description from the shared cron parser.
  useEffect(() => {
    const expr = values.cron ?? '';
    if (!expr.trim()) {
      setCronDescription(null);
      return;
    }
    if (!isPlausibleCron(expr)) {
      setCronDescription(null);
      return;
    }
    let cancelled = false;
    backupsApi
      .cronDescription(expr)
      .then((data) => {
        if (!cancelled) setCronDescription(data.description ?? data.error);
      })
      .catch(() => {
        if (!cancelled) setCronDescription(null);
      });
    return () => {
      cancelled = true;
    };
  }, [values.cron]);

  function update(patch: Partial<BackupSettingsValues>): void {
    setValues((current) => ({ ...current, ...patch }));
    setSaved(false);
  }

  async function handleSave(): Promise<void> {
    setSaving(true);
    setError(null);
    setSaved(false);
    const payload: BackupSettingsValues = { ...values };
    // Write-only secret: send only when re-entered.
    if (secretInput) {
      payload.s3_secret_access_key = secretInput;
    } else {
      delete payload.s3_secret_access_key;
    }
    try {
      if (configId) {
        await backupsSettingsApi.updateValues(configId, payload);
      } else {
        const created = await backupsSettingsApi.createConfig(payload);
        setConfigId(created.id);
      }
      setSecretStored(Boolean(payload.s3_secret_access_key) || secretStored);
      setSecretInput('');
      setSaved(true);
    } catch (saveError) {
      const detail =
        // eslint-disable-next-line @typescript-eslint/no-explicit-any
        (saveError as any)?.response?.data?.detail ?? 'Failed to save settings';
      setError(String(detail));
    } finally {
      setSaving(false);
    }
  }

  if (loading) {
    return (
      <div className="space-y-4 p-4" data-testid="backup-settings-loading">
        <Skeleton className="h-8 w-64" />
        <Skeleton className="h-64 w-full" />
      </div>
    );
  }

  return (
    <div className="space-y-4 p-4">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-semibold">Backup Settings</h1>
        <Button asChild variant="outline">
          <Link to="/admin/backups">Back to backups</Link>
        </Button>
      </div>

      {values.destination === 'local' && (
        <Alert data-testid="local-destination-warning">
          <AlertTitle>Local destination</AlertTitle>
          <AlertDescription>
            Local archives share the volume with the database. They protect
            against data mistakes, not against losing the volume — use S3 for
            off-instance copies.
          </AlertDescription>
        </Alert>
      )}

      {isPostgres && (
        <Alert data-testid="postgres-info-panel">
          <AlertTitle>PostgreSQL instance</AlertTitle>
          <AlertDescription>
            Archives created on PostgreSQL are portable logical exports, not
            restorable backups. Disaster recovery is configured on the
            database itself (managed snapshots or operator-run pg_dump).
          </AlertDescription>
        </Alert>
      )}

      <Card>
        <CardHeader>
          <CardTitle>Destination</CardTitle>
          <CardDescription>Where backup archives are stored.</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="space-y-2">
            <Label htmlFor="backup-destination">Destination</Label>
            <Select
              value={values.destination ?? 'local'}
              onValueChange={(value) =>
                update({ destination: value as 'local' | 's3' })
              }
            >
              <SelectTrigger id="backup-destination" className="w-56">
                <SelectValue placeholder="Select destination" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="local">Local directory</SelectItem>
                <SelectItem value="s3">S3 / object storage</SelectItem>
              </SelectContent>
            </Select>
          </div>

          {values.destination === 'local' && (
            <div className="space-y-2">
              <Label htmlFor="backup-local-path">Local path</Label>
              <Input
                id="backup-local-path"
                value={values.local_path ?? ''}
                onChange={(event) => update({ local_path: event.target.value })}
                placeholder="./sb_data/backups"
              />
            </div>
          )}

          {values.destination === 's3' && (
            <div
              className="space-y-4"
              data-testid="s3-settings"
            >
              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-2">
                  <Label htmlFor="s3-bucket">Bucket</Label>
                  <Input
                    id="s3-bucket"
                    value={values.s3_bucket ?? ''}
                    onChange={(event) => update({ s3_bucket: event.target.value })}
                  />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="s3-region">Region</Label>
                  <Input
                    id="s3-region"
                    value={values.s3_region ?? ''}
                    onChange={(event) => update({ s3_region: event.target.value })}
                  />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="s3-access-key">Access key ID</Label>
                  <Input
                    id="s3-access-key"
                    value={values.s3_access_key_id ?? ''}
                    onChange={(event) =>
                      update({ s3_access_key_id: event.target.value })
                    }
                  />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="s3-secret-key">Secret access key</Label>
                  <Input
                    id="s3-secret-key"
                    type="password"
                    placeholder={secretStored ? MASK : ''}
                    value={secretInput}
                    onChange={(event) => setSecretInput(event.target.value)}
                  />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="s3-key-prefix">Key prefix</Label>
                  <Input
                    id="s3-key-prefix"
                    value={values.s3_key_prefix ?? ''}
                    onChange={(event) =>
                      update({ s3_key_prefix: event.target.value })
                    }
                  />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="s3-endpoint">Endpoint URL</Label>
                  <Input
                    id="s3-endpoint"
                    value={values.s3_endpoint_url ?? ''}
                    onChange={(event) =>
                      update({ s3_endpoint_url: event.target.value })
                    }
                    placeholder="https://s3.amazonaws.com"
                  />
                </div>
              </div>
            </div>
          )}
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Schedule and retention</CardTitle>
          <CardDescription>
            Automatic backups run on a cron schedule (UTC). Leave the schedule
            empty to disable them.
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="flex flex-wrap gap-2">
            {CRON_PRESETS.map((preset) => (
              <Button
                key={preset.expr}
                type="button"
                variant="outline"
                size="sm"
                data-testid={`cron-preset-${preset.expr}`}
                onClick={() => update({ cron: preset.expr })}
              >
                {preset.label}
              </Button>
            ))}
          </div>
          <div className="space-y-2">
            <Label htmlFor="backup-cron">Cron expression</Label>
            <Input
              id="backup-cron"
              value={values.cron ?? ''}
              onChange={(event) => update({ cron: event.target.value })}
              placeholder="0 2 * * *"
              className="max-w-xs"
            />
            {values.cron && !isPlausibleCron(values.cron) && (
              <p className="text-sm text-destructive" data-testid="cron-inline-error">
                Invalid cron expression: expected 5 fields (minute hour
                day-of-month month day-of-week).
              </p>
            )}
            {cronDescription && (
              <p className="text-sm text-muted-foreground" data-testid="cron-description">
                {cronDescription}
              </p>
            )}
          </div>
          <div className="space-y-2">
            <Label htmlFor="backup-max-keep">Maximum automatic backups to keep</Label>
            <Input
              id="backup-max-keep"
              type="number"
              min={1}
              value={values.max_keep ?? 3}
              onChange={(event) =>
                update({ max_keep: Number(event.target.value) })
              }
              className="max-w-xs"
            />
          </div>
        </CardContent>
      </Card>

      {error && (
        <Alert variant="destructive" data-testid="settings-error">
          <AlertTitle>Save failed</AlertTitle>
          <AlertDescription>{error}</AlertDescription>
        </Alert>
      )}
      {saved && (
        <p className="text-sm text-muted-foreground" data-testid="settings-saved">
          Settings saved.
        </p>
      )}

      <div>
        <Button onClick={handleSave} disabled={saving}>
          {saving ? 'Saving…' : 'Save settings'}
        </Button>
      </div>
    </div>
  );
}
