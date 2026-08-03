import { useCallback, useEffect, useMemo, useState } from 'react';
import { Link, useNavigate, useParams } from 'react-router';
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Switch } from '@/components/ui/switch';
import { Textarea } from '@/components/ui/textarea';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';
import {
  ArrowLeft,
  Copy,
  GitCompareArrows,
  Play,
  Plus,
  Rocket,
  Save,
  Trash2,
  X,
} from 'lucide-react';
import { CodeEditorLazy } from '@/components/code-editor';
import {
  functionsService,
  type FunctionBody,
  type FunctionExecution,
  type FunctionItem,
  type FunctionStats,
  type FunctionVersion,
} from '@/services/functions.service';
import { useAuthStore } from '@/stores/auth.store';
import { useToast } from '@/hooks/use-toast';
import { Checkbox } from '@/components/ui/checkbox';
import {
  generateRequirementsTxt,
  isPinnedDependency,
  isRequirementsFile,
  normalizeDependencies,
  validateSourcePath,
} from './functionSourceUtils';
import {
  createEditorSnapshot,
  isEditorDirty,
  type FunctionEditorSnapshot,
} from './functionEditorSnapshot';
import { useUnsavedChangesGuard } from './useUnsavedChangesGuard';
import VersionCompareSheet from './VersionCompareSheet';

const DEFAULT_HANDLER = `from snackbase_fn import Request, Response


def handler(req: Request) -> Response:
    return Response.json({"ok": True})
`;

const DEFAULT_ENTRYPOINT = 'handler.py';

function buildEditorFiles(
  files: Record<string, string>,
  deps: string[],
): Record<string, string> {
  const next = { ...files };
  next['requirements.txt'] = generateRequirementsTxt(deps);
  return next;
}

export default function FunctionEditorPage() {
  const { slug = '' } = useParams();
  const navigate = useNavigate();
  const { toast } = useToast();
  const account = useAuthStore((s) => s.account);

  const [fn, setFn] = useState<FunctionItem | null>(null);
  const [files, setFiles] = useState<Record<string, string>>({
    [DEFAULT_ENTRYPOINT]: DEFAULT_HANDLER,
  });
  const [activeFile, setActiveFile] = useState(DEFAULT_ENTRYPOINT);
  const [entrypoint, setEntrypoint] = useState(DEFAULT_ENTRYPOINT);
  const [deps, setDeps] = useState<string[]>([]);
  const [newDep, setNewDep] = useState('');
  const [newFileName, setNewFileName] = useState('');
  const [fileNameError, setFileNameError] = useState<string | null>(null);
  const [baselineFiles, setBaselineFiles] = useState<Record<string, string>>({
    [DEFAULT_ENTRYPOINT]: DEFAULT_HANDLER,
  });
  const [baseline, setBaseline] = useState<FunctionEditorSnapshot | null>(null);
  const [loading, setLoading] = useState(true);
  const [deploying, setDeploying] = useState(false);
  const [deployError, setDeployError] = useState<string | null>(null);

  // Test sheet
  const [testMethod, setTestMethod] = useState('POST');
  const [testPath, setTestPath] = useState('/');
  const [testBody, setTestBody] = useState('{\n  "hello": "world"\n}');
  const [testResult, setTestResult] = useState<string | null>(null);
  const [testing, setTesting] = useState(false);

  // Executions / versions / grants / stats
  const [executions, setExecutions] = useState<FunctionExecution[]>([]);
  const [versions, setVersions] = useState<FunctionVersion[]>([]);
  const [compareSelection, setCompareSelection] = useState<string[]>([]);
  const [compareOpen, setCompareOpen] = useState(false);
  const [compareLoading, setCompareLoading] = useState(false);
  const [compareLeft, setCompareLeft] = useState<FunctionBody | null>(null);
  const [compareRight, setCompareRight] = useState<FunctionBody | null>(null);
  const [grantsText, setGrantsText] = useState('');
  const [stats, setStats] = useState<FunctionStats | null>(null);

  const invokeUrl = useMemo(() => {
    const accountSlug = account?.slug ?? '{account_slug}';
    return `/api/v1/f/${accountSlug}/${slug}`;
  }, [account?.slug, slug]);

  const editorFiles = useMemo(() => buildEditorFiles(files, deps), [files, deps]);
  const openPaths = useMemo(() => Object.keys(editorFiles), [editorFiles]);

  const currentSnapshot = useMemo(
    () => createEditorSnapshot(files, deps, entrypoint),
    [files, deps, entrypoint],
  );
  const dirty = !loading && isEditorDirty(currentSnapshot, baseline);
  useUnsavedChangesGuard(dirty);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const item = await functionsService.get(slug);
      setFn(item);
      const caps =
        item.grants && typeof item.grants === 'object' && 'capabilities' in item.grants
          ? ((item.grants as { capabilities?: string[] }).capabilities ?? [])
          : [];
      setGrantsText(caps.join('\n'));
      try {
        const body = await functionsService.getBody(slug);
        const loadedDeps = normalizeDependencies(body.dependencies ?? []);
        const loadedFiles = { ...body.files };
        // Dependencies panel is source of truth; regenerate requirements.txt.
        loadedFiles['requirements.txt'] = generateRequirementsTxt(loadedDeps);
        setFiles(loadedFiles);
        setBaselineFiles(loadedFiles);
        setDeps(loadedDeps);
        const ep = body.entrypoint || item.entrypoint || Object.keys(loadedFiles)[0] || DEFAULT_ENTRYPOINT;
        setEntrypoint(ep);
        setBaseline(createEditorSnapshot(loadedFiles, loadedDeps, ep));
        setActiveFile(ep in loadedFiles ? ep : Object.keys(loadedFiles)[0] || DEFAULT_ENTRYPOINT);
      } catch {
        // No version yet
        const initial = {
          [DEFAULT_ENTRYPOINT]: DEFAULT_HANDLER,
          'requirements.txt': '',
        };
        const ep = item.entrypoint || DEFAULT_ENTRYPOINT;
        setFiles(initial);
        setBaselineFiles(initial);
        setDeps([]);
        setEntrypoint(ep);
        setBaseline(createEditorSnapshot(initial, [], ep));
        setActiveFile(DEFAULT_ENTRYPOINT);
      }
      const [execs, vers, st] = await Promise.all([
        functionsService.listExecutions(slug),
        functionsService.listVersions(slug),
        functionsService.stats(slug, '24h').catch(() => null),
      ]);
      setExecutions(execs.items);
      setVersions(vers.items);
      setStats(st);
    } catch {
      toast({ title: 'Error', description: 'Function not found', variant: 'destructive' });
      navigate('/admin/functions');
    } finally {
      setLoading(false);
    }
  }, [slug, navigate, toast]);

  useEffect(() => {
    load();
  }, [load]);

  const handleDeploy = async () => {
    if (!fn) return;
    const normalized = normalizeDependencies(deps);
    const invalid = normalized.filter((d) => !isPinnedDependency(d));
    if (invalid.length) {
      toast({
        title: 'Invalid dependencies',
        description: `Use exact pins (name==version). Invalid: ${invalid.join(', ')}`,
        variant: 'destructive',
      });
      return;
    }
    if (!(entrypoint in editorFiles)) {
      toast({
        title: 'Invalid entrypoint',
        description: `Entrypoint '${entrypoint}' is not among the source files`,
        variant: 'destructive',
      });
      return;
    }
    setDeploying(true);
    setDeployError(null);
    try {
      const filesOut = buildEditorFiles(files, normalized);
      await functionsService.deploy(fn.slug, {
        entrypoint,
        dependencies: normalized,
        files: filesOut,
      });
      toast({ title: 'Deployed successfully' });
      await load();
    } catch (err: unknown) {
      const msg =
        (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail ??
        'Deploy failed';
      setDeployError(String(msg));
      toast({ title: 'Deploy failed', description: String(msg), variant: 'destructive' });
    } finally {
      setDeploying(false);
    }
  };

  const handleTest = async () => {
    if (!fn) return;
    setTesting(true);
    setTestResult(null);
    try {
      let body: unknown = testBody;
      try {
        body = JSON.parse(testBody);
      } catch {
        // keep raw string
      }
      const result = await functionsService.test(fn.slug, {
        method: testMethod,
        path: testPath,
        body,
      });
      setTestResult(JSON.stringify(result, null, 2));
      const execs = await functionsService.listExecutions(fn.slug);
      setExecutions(execs.items);
    } catch (err: unknown) {
      const msg =
        (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail ??
        'Test failed';
      setTestResult(String(msg));
    } finally {
      setTesting(false);
    }
  };

  const addDep = () => {
    const pin = newDep.trim();
    if (!pin) return;
    if (!isPinnedDependency(pin)) {
      toast({
        title: 'Unpinned dependency',
        description: 'Use exact form package==version',
        variant: 'destructive',
      });
      return;
    }
    setDeps(normalizeDependencies([...deps, pin]));
    setNewDep('');
  };

  const addFile = () => {
    const error = validateSourcePath(newFileName, files);
    if (error) {
      setFileNameError(error);
      return;
    }
    const name = newFileName.trim();
    setFiles({ ...files, [name]: '' });
    setActiveFile(name);
    setNewFileName('');
    setFileNameError(null);
  };

  const removeFile = (name: string) => {
    if (isRequirementsFile(name)) return;
    if (name === entrypoint) {
      toast({
        title: 'Cannot remove entrypoint',
        description: 'Set another file as the entrypoint before removing this file.',
        variant: 'destructive',
      });
      return;
    }
    const removable = Object.keys(files).filter((n) => !isRequirementsFile(n));
    if (removable.length <= 1) return;
    const next = { ...files };
    delete next[name];
    setFiles(next);
    if (activeFile === name) {
      const nextActive =
        Object.keys(next).find((n) => !isRequirementsFile(n)) ?? Object.keys(next)[0];
      setActiveFile(nextActive);
    }
  };

  const saveMeta = async (patch: Partial<FunctionItem>) => {
    if (!fn) return;
    const updated = await functionsService.update(fn.slug, {
      auth_required: patch.auth_required,
      enabled: patch.enabled,
      name: patch.name,
    });
    setFn(updated);
  };

  const saveGrants = async () => {
    if (!fn) return;
    const grants = grantsText
      .split('\n')
      .map((l) => l.trim())
      .filter(Boolean);
    const updated = await functionsService.updateGrants(fn.slug, grants);
    setFn(updated);
    toast({ title: 'Grants saved' });
  };

  const activateVersion = async (versionId: string) => {
    if (!fn) return;
    await functionsService.activateVersion(fn.slug, versionId);
    toast({ title: 'Version activated' });
    await load();
  };

  const toggleCompareSelection = (versionId: string, checked: boolean) => {
    setCompareSelection((prev) => {
      if (!checked) return prev.filter((id) => id !== versionId);
      if (prev.includes(versionId)) return prev;
      if (prev.length < 2) return [...prev, versionId];
      // Selecting a 3rd replaces the older selection by version number.
      const selected = versions.filter((v) => prev.includes(v.id));
      const oldest = selected.reduce((a, b) => (a.version <= b.version ? a : b));
      return [...prev.filter((id) => id !== oldest.id), versionId];
    });
  };

  const handleCompare = async () => {
    if (!fn || compareSelection.length !== 2) return;
    setCompareLoading(true);
    try {
      const [a, b] = await Promise.all([
        functionsService.getBody(fn.slug, compareSelection[0]),
        functionsService.getBody(fn.slug, compareSelection[1]),
      ]);
      setCompareLeft(a);
      setCompareRight(b);
      setCompareOpen(true);
    } catch (err: unknown) {
      const msg =
        (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail ??
        'Failed to load versions for compare';
      toast({ title: 'Compare failed', description: String(msg), variant: 'destructive' });
    } finally {
      setCompareLoading(false);
    }
  };

  const selectedCompareVersions = useMemo(
    () =>
      compareSelection
        .map((id) => versions.find((v) => v.id === id))
        .filter((v): v is FunctionVersion => Boolean(v))
        .sort((a, b) => a.version - b.version),
    [compareSelection, versions],
  );

  const fileIsDirty = (name: string) => {
    return (editorFiles[name] ?? '') !== (baselineFiles[name] ?? '');
  };

  const activeIsReadOnly = isRequirementsFile(activeFile);

  if (loading || !fn) {
    return <div className="p-8 text-muted-foreground">Loading function…</div>;
  }

  return (
    <div className="p-6 space-y-4 max-w-[1400px]">
      <div className="flex items-start justify-between gap-4">
        <div className="space-y-1">
          <Button variant="ghost" size="sm" asChild className="-ml-2">
            <Link to="/admin/functions">
              <ArrowLeft className="h-4 w-4 mr-1" />
              Functions
            </Link>
          </Button>
          <h1 className="text-2xl font-bold tracking-tight">{fn.name}</h1>
          <div className="flex items-center gap-2 text-sm text-muted-foreground">
            <code className="font-mono">{fn.slug}</code>
            {fn.auth_required ? (
              <Badge variant="secondary">Auth required</Badge>
            ) : (
              <Badge variant="outline">Public</Badge>
            )}
            <Badge variant="outline">{fn.status}</Badge>
          </div>
        </div>
        <div className="flex gap-2">
          <Button variant="outline" size="sm" onClick={() => navigator.clipboard.writeText(invokeUrl)}>
            <Copy className="h-4 w-4 mr-2" />
            Copy invoke URL
          </Button>
          <Button size="sm" onClick={handleDeploy} disabled={deploying} aria-label="Deploy function">
            <Rocket className="h-4 w-4 mr-2" />
            {deploying ? 'Deploying…' : 'Deploy'}
          </Button>
          {dirty && (
            <Badge variant="secondary" data-testid="unsaved-changes">
              Unsaved changes
            </Badge>
          )}
        </div>
      </div>

      {!fn.auth_required && (
        <Alert>
          <AlertTitle>Public function</AlertTitle>
          <AlertDescription>
            Anyone who knows the invoke URL can call this function. Use secrets and signature
            verification for webhooks.
          </AlertDescription>
        </Alert>
      )}

      {deployError && (
        <Alert variant="destructive">
          <AlertTitle>Deploy error</AlertTitle>
          <AlertDescription className="whitespace-pre-wrap font-mono text-xs">
            {deployError}
          </AlertDescription>
        </Alert>
      )}

      <div className="flex flex-wrap items-center gap-6 text-sm">
        <div className="flex items-center gap-2">
          <Switch
            checked={fn.enabled}
            onCheckedChange={(enabled) => saveMeta({ enabled })}
          />
          <span>Enabled</span>
        </div>
        <div className="flex items-center gap-2">
          <Switch
            checked={fn.auth_required}
            onCheckedChange={(auth_required) => saveMeta({ auth_required })}
          />
          <span>Auth required</span>
        </div>
        <code className="text-xs bg-muted px-2 py-1 rounded">{invokeUrl}</code>
        {stats && (
          <span className="text-muted-foreground">
            24h: {stats.total} invokes · p50 {stats.p50_ms ?? '—'}ms · p95 {stats.p95_ms ?? '—'}ms
          </span>
        )}
      </div>

      <Tabs defaultValue="code">
        <TabsList>
          <TabsTrigger value="code">Code</TabsTrigger>
          <TabsTrigger value="test">Test</TabsTrigger>
          <TabsTrigger value="executions">Executions</TabsTrigger>
          <TabsTrigger value="versions">Versions</TabsTrigger>
          <TabsTrigger value="grants">Grants</TabsTrigger>
        </TabsList>

        <TabsContent value="code" className="space-y-4">
          <div className="grid grid-cols-1 lg:grid-cols-[1fr_280px] gap-4">
            <div className="border rounded-lg overflow-hidden min-w-0">
              <div
                className="flex flex-wrap gap-1 border-b bg-muted/40 p-2"
                role="group"
                aria-label="Source files"
              >
                {Object.keys(editorFiles).map((name) => {
                  const selected = activeFile === name;
                  const dirty = fileIsDirty(name);
                  const isEp = name === entrypoint;
                  const readOnlyFile = isRequirementsFile(name);
                  return (
                    <div key={name} className="flex items-center">
                      <Button
                        size="sm"
                        aria-current={selected ? 'page' : undefined}
                        aria-label={`${name}${isEp ? ' (entrypoint)' : ''}${readOnlyFile ? ' (read-only)' : ''}${dirty ? ', unsaved changes' : ''}`}
                        variant={selected ? 'default' : 'ghost'}
                        className="h-7 rounded-r-none"
                        onClick={() => setActiveFile(name)}
                      >
                        {name}
                        {isEp ? ' ★' : ''}
                        {dirty ? ' •' : ''}
                      </Button>
                      {!readOnlyFile && Object.keys(editorFiles).filter((n) => !isRequirementsFile(n)).length > 1 && (
                        <Button
                          size="sm"
                          variant="ghost"
                          className="h-7 w-7 p-0 rounded-l-none"
                          aria-label={`Remove ${name}`}
                          onClick={() => removeFile(name)}
                        >
                          <X className="h-3 w-3" />
                        </Button>
                      )}
                    </div>
                  );
                })}
                <div className="flex items-center gap-1 ml-2">
                  <Input
                    className="h-7 w-36"
                    placeholder="utils.py"
                    aria-label="New file name"
                    value={newFileName}
                    onChange={(e) => {
                      setNewFileName(e.target.value);
                      setFileNameError(null);
                    }}
                    onKeyDown={(e) => e.key === 'Enter' && (e.preventDefault(), addFile())}
                  />
                  <Button
                    size="sm"
                    variant="outline"
                    className="h-7"
                    aria-label="Add file"
                    onClick={addFile}
                  >
                    <Plus className="h-3 w-3" />
                  </Button>
                </div>
              </div>
              {fileNameError && (
                <p className="px-3 py-1 text-xs text-destructive" role="alert">
                  {fileNameError}
                </p>
              )}
              {!activeIsReadOnly && activeFile !== entrypoint && (
                <div className="flex items-center gap-2 border-b px-3 py-1.5 bg-muted/20">
                  <Button
                    size="sm"
                    variant="outline"
                    className="h-7"
                    aria-label={`Set ${activeFile} as entrypoint`}
                    onClick={() => setEntrypoint(activeFile)}
                  >
                    Set as entrypoint
                  </Button>
                  <span className="text-xs text-muted-foreground">
                    Current entrypoint: <code>{entrypoint}</code>
                  </span>
                </div>
              )}
              {activeIsReadOnly && (
                <div className="px-3 py-1.5 border-b text-xs text-muted-foreground bg-muted/20">
                  Generated from the Dependencies panel — edit pins there, not this file.
                </div>
              )}
              <CodeEditorLazy
                path={activeFile}
                value={editorFiles[activeFile] ?? ''}
                readOnly={activeIsReadOnly}
                height={420}
                openPaths={openPaths}
                language={{ path: activeFile }}
                className="min-w-0 w-full border-0"
                aria-label={
                  activeIsReadOnly
                    ? `${activeFile} (read-only generated file)`
                    : `Editing ${activeFile}`
                }
                onChange={(next) => {
                  if (isRequirementsFile(activeFile)) return;
                  setFiles({ ...files, [activeFile]: next });
                }}
              />
            </div>

            <div className="border rounded-lg p-4 space-y-3">
              <h3 className="font-medium">Dependencies</h3>
              <p className="text-xs text-muted-foreground">
                Exact pins only (<code>package==version</code>). Installed with uv on deploy.
                Generates read-only <code>requirements.txt</code>.
              </p>
              <div className="space-y-1">
                {deps.map((d) => (
                  <div key={d} className="flex items-center justify-between text-sm font-mono">
                    <span>{d}</span>
                    <Button
                      size="icon"
                      variant="ghost"
                      className="h-7 w-7"
                      aria-label={`Remove dependency ${d}`}
                      onClick={() => setDeps(deps.filter((x) => x !== d))}
                    >
                      <Trash2 className="h-3 w-3" />
                    </Button>
                  </div>
                ))}
                {deps.length === 0 && (
                  <p className="text-xs text-muted-foreground">No extra packages</p>
                )}
              </div>
              <div className="flex gap-1">
                <Input
                  className="h-8 font-mono text-xs"
                  placeholder="cowsay==6.1"
                  aria-label="New dependency pin"
                  value={newDep}
                  onChange={(e) => setNewDep(e.target.value)}
                  onKeyDown={(e) => e.key === 'Enter' && (e.preventDefault(), addDep())}
                />
                <Button size="sm" className="h-8" aria-label="Add dependency" onClick={addDep}>
                  Add
                </Button>
              </div>
            </div>
          </div>
        </TabsContent>

        <TabsContent value="test" className="space-y-4">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div className="space-y-3 border rounded-lg p-4">
              <div className="grid grid-cols-2 gap-2">
                <div>
                  <Label>Method</Label>
                  <Select value={testMethod} onValueChange={setTestMethod}>
                    <SelectTrigger>
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      {['GET', 'POST', 'PUT', 'PATCH', 'DELETE'].map((m) => (
                        <SelectItem key={m} value={m}>
                          {m}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>
                <div>
                  <Label>Path suffix</Label>
                  <Input value={testPath} onChange={(e) => setTestPath(e.target.value)} />
                </div>
              </div>
              <div>
                <Label>JSON body</Label>
                <CodeEditorLazy
                  path="test-body.json"
                  value={testBody}
                  onChange={setTestBody}
                  language={{ path: 'test-body.json', languageId: 'json' }}
                  height={220}
                  className="mt-1 min-w-0 w-full overflow-hidden rounded-md border"
                  aria-label="JSON body"
                />
              </div>
              <Button onClick={handleTest} disabled={testing || !fn.active_version_id}>
                <Play className="h-4 w-4 mr-2" />
                {testing ? 'Running…' : 'Run test'}
              </Button>
              {!fn.active_version_id && (
                <p className="text-xs text-muted-foreground">Deploy a version before testing.</p>
              )}
            </div>
            <div className="border rounded-lg p-4">
              <Label>Result</Label>
              <CodeEditorLazy
                path="test-result.json"
                value={testResult ?? 'Run a test to see output'}
                readOnly
                language={
                  testResult && testResult.trimStart().startsWith('{')
                    ? { path: 'test-result.json', languageId: 'json' }
                    : { path: 'test-result.txt', languageId: 'plaintext' }
                }
                height={280}
                className="mt-2 min-w-0 w-full overflow-hidden rounded-md border"
                aria-label="Test result"
              />
            </div>
          </div>
        </TabsContent>

        <TabsContent value="executions">
          <div className="border rounded-lg">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Time</TableHead>
                  <TableHead>Status</TableHead>
                  <TableHead>HTTP</TableHead>
                  <TableHead>Duration</TableHead>
                  <TableHead>Error</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {executions.length === 0 ? (
                  <TableRow>
                    <TableCell colSpan={5} className="text-center text-muted-foreground">
                      No executions yet
                    </TableCell>
                  </TableRow>
                ) : (
                  executions.map((ex) => (
                    <TableRow key={ex.id}>
                      <TableCell className="text-sm">
                        {new Date(ex.executed_at).toLocaleString()}
                      </TableCell>
                      <TableCell>
                        <Badge variant={ex.status === 'success' ? 'default' : 'destructive'}>
                          {ex.status}
                        </Badge>
                      </TableCell>
                      <TableCell>{ex.http_status}</TableCell>
                      <TableCell>{ex.duration_ms ?? '—'} ms</TableCell>
                      <TableCell className="max-w-[280px] truncate text-xs text-muted-foreground">
                        {ex.error_message || '—'}
                      </TableCell>
                    </TableRow>
                  ))
                )}
              </TableBody>
            </Table>
          </div>
        </TabsContent>

        <TabsContent value="versions" className="space-y-3">
          <div className="flex flex-wrap items-center gap-2">
            <Button
              size="sm"
              variant="outline"
              disabled={compareSelection.length !== 2 || compareLoading}
              onClick={handleCompare}
              aria-label="Compare selected versions"
            >
              <GitCompareArrows className="h-4 w-4 mr-2" />
              {compareLoading ? 'Loading…' : 'Compare'}
            </Button>
            {selectedCompareVersions.length === 2 ? (
              <span className="text-sm text-muted-foreground">
                v{selectedCompareVersions[0].version} vs v{selectedCompareVersions[1].version}
              </span>
            ) : (
              <span className="text-sm text-muted-foreground">
                Select two versions to compare
              </span>
            )}
            {compareSelection.length > 0 && (
              <Button
                size="sm"
                variant="ghost"
                className="h-8"
                onClick={() => setCompareSelection([])}
              >
                Clear
              </Button>
            )}
          </div>
          <div className="border rounded-lg">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead className="w-10">
                    <span className="sr-only">Select</span>
                  </TableHead>
                  <TableHead>Version</TableHead>
                  <TableHead>SHA</TableHead>
                  <TableHead>Deps</TableHead>
                  <TableHead>Created</TableHead>
                  <TableHead />
                </TableRow>
              </TableHeader>
              <TableBody>
                {versions.map((v) => (
                  <TableRow key={v.id}>
                    <TableCell>
                      <Checkbox
                        checked={compareSelection.includes(v.id)}
                        onCheckedChange={(checked) =>
                          toggleCompareSelection(v.id, checked === true)
                        }
                        aria-label={`Select version ${v.version} for compare`}
                      />
                    </TableCell>
                    <TableCell>
                      v{v.version}
                      {fn.active_version_id === v.id && (
                        <Badge className="ml-2" variant="secondary">
                          active
                        </Badge>
                      )}
                    </TableCell>
                    <TableCell className="font-mono text-xs">{v.sha256.slice(0, 12)}</TableCell>
                    <TableCell className="text-xs">{v.dependencies?.join(', ') || '—'}</TableCell>
                    <TableCell className="text-sm">
                      {new Date(v.created_at).toLocaleString()}
                    </TableCell>
                    <TableCell>
                      {fn.active_version_id !== v.id && (
                        <Button size="sm" variant="outline" onClick={() => activateVersion(v.id)}>
                          Rollback
                        </Button>
                      )}
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </div>
          <VersionCompareSheet
            open={compareOpen}
            onOpenChange={setCompareOpen}
            left={compareLeft}
            right={compareRight}
            activeVersionId={fn.active_version_id}
          />
        </TabsContent>

        <TabsContent value="grants" className="space-y-3 max-w-xl">
          <p className="text-sm text-muted-foreground">
            Deny-by-default capabilities for <code>get_admin_client()</code>. One per line, e.g.{' '}
            <code>records.read:todos</code>, <code>records.write:orders</code>,{' '}
            <code>records.secrets.read:todos</code>.
          </p>
          <Textarea
            className="font-mono text-sm min-h-[160px]"
            value={grantsText}
            onChange={(e) => setGrantsText(e.target.value)}
            placeholder="records.read:todos"
          />
          <Button onClick={saveGrants}>
            <Save className="h-4 w-4 mr-2" />
            Save grants
          </Button>
        </TabsContent>
      </Tabs>
    </div>
  );
}
