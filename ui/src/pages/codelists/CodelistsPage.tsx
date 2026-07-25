/**
 * Codelists workspace: left rail of codelists + detail tabs
 * (values | overrides | settings).
 */

import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { Link, useNavigate, useParams, useSearchParams } from 'react-router';
import {
  BookMarked,
  Download,
  Lock,
  Plus,
  RefreshCw,
  Search,
  Upload,
} from 'lucide-react';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Skeleton } from '@/components/ui/skeleton';
import { Switch } from '@/components/ui/switch';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Textarea } from '@/components/ui/textarea';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { useToast } from '@/hooks/use-toast';
import { handleApiError } from '@/lib/api';
import { isSuperadminAccount, SYSTEM_ACCOUNT_ID } from '@/lib/auth';
import { useAuthStore } from '@/stores/auth.store';
import * as codelistsService from '@/services/codelists.service';
import { getAccounts, type AccountListItem } from '@/services/accounts.service';
import type {
  Codelist,
  CodelistValue,
  EffectiveCodelistValue,
  CodelistOverride,
} from '@/types/codelist';
import { cn } from '@/lib/utils';

type ScopeFilter = 'all' | 'system' | 'account';

export default function CodelistsPage() {
  const { code: routeCode } = useParams<{ code?: string }>();
  const [searchParams, setSearchParams] = useSearchParams();
  const navigate = useNavigate();
  const { toast } = useToast();
  const account = useAuthStore((s) => s.account);
  const user = useAuthStore((s) => s.user);
  const isSuperadmin = isSuperadminAccount(account);
  const isAdmin = user?.role === 'admin' || isSuperadmin;

  const [lists, setLists] = useState<Codelist[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [search, setSearch] = useState('');
  const [scopeFilter, setScopeFilter] = useState<ScopeFilter>('all');
  const [selectedCode, setSelectedCode] = useState<string | null>(routeCode ?? null);
  const [tab, setTab] = useState(searchParams.get('tab') || 'values');

  const [values, setValues] = useState<CodelistValue[]>([]);
  const [effective, setEffective] = useState<EffectiveCodelistValue[]>([]);
  const [overrides, setOverrides] = useState<CodelistOverride[]>([]);
  const [langPreview, setLangPreview] = useState('en');
  const [showInactive, setShowInactive] = useState(false);
  const [detailLoading, setDetailLoading] = useState(false);
  /** Superadmin: which tenant's overrides/effective preview to manage. */
  const [overrideAccountId, setOverrideAccountId] = useState<string>('');
  const [tenantAccounts, setTenantAccounts] = useState<AccountListItem[]>([]);

  const [createOpen, setCreateOpen] = useState(false);
  const [valueDialogOpen, setValueDialogOpen] = useState(false);
  const [editingValue, setEditingValue] = useState<CodelistValue | null>(null);
  const importFileRef = useRef<HTMLInputElement>(null);

  // Create form
  const [formCode, setFormCode] = useState('');
  const [formName, setFormName] = useState('');
  const [formDesc, setFormDesc] = useState('');
  const [formScope, setFormScope] = useState<'system' | 'account'>('account');
  const [formExtensible, setFormExtensible] = useState(false);
  const [formCodeError, setFormCodeError] = useState<string | null>(null);

  // Value form
  const [vCode, setVCode] = useState('');
  const [vDef, setVDef] = useState('');
  const [vSort, setVSort] = useState(0);
  const [vActive, setVActive] = useState(true);
  const [vLabels, setVLabels] = useState<Array<{ language: string; label: string }>>([
    { language: 'en', label: '' },
  ]);
  const [vMeta, setVMeta] = useState('{}');

  // Settings form
  const [settingsName, setSettingsName] = useState('');
  const [settingsDesc, setSettingsDesc] = useState('');
  const [settingsActive, setSettingsActive] = useState(true);
  const [settingsExtensible, setSettingsExtensible] = useState(false);

  const selected = useMemo(
    () => lists.find((c) => c.code === selectedCode) ?? null,
    [lists, selectedCode],
  );

  const fetchLists = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await codelistsService.listCodelists();
      setLists(data);
    } catch (err) {
      setError(handleApiError(err));
    } finally {
      setLoading(false);
    }
  }, []);

  /** Account id for override APIs: own account for tenants; selected tenant for superadmin. */
  const overrideTargetAccountId = isSuperadmin
    ? overrideAccountId || undefined
    : account?.id;

  const fetchDetail = useCallback(
    async (code: string) => {
      setDetailLoading(true);
      try {
        const canLoadOverrides =
          isAdmin && (!isSuperadmin || Boolean(overrideAccountId));
        const effParams: {
          lang?: string;
          active?: boolean;
          account_id?: string;
        } = { lang: langPreview, active: true };
        if (isSuperadmin && overrideAccountId) {
          effParams.account_id = overrideAccountId;
        }

        const [raw, eff, ovs] = await Promise.all([
          codelistsService.listManageValues(code, true),
          codelistsService.getEffectiveValues(code, effParams),
          canLoadOverrides
            ? codelistsService
              .listOverrides(
                code,
                isSuperadmin ? overrideAccountId : undefined,
              )
              .catch(() => [] as CodelistOverride[])
            : Promise.resolve([] as CodelistOverride[]),
        ]);
        setValues(raw);
        setEffective(eff);
        setOverrides(ovs);
      } catch (err) {
        toast({ title: 'Failed to load codelist detail', description: handleApiError(err), variant: 'destructive' });
      } finally {
        setDetailLoading(false);
      }
    },
    [isAdmin, isSuperadmin, langPreview, overrideAccountId, toast],
  );

  useEffect(() => {
    fetchLists();
  }, [fetchLists]);

  useEffect(() => {
    if (!isSuperadmin) return;
    let cancelled = false;
    (async () => {
      try {
        const res = await getAccounts({ page: 1, page_size: 100 });
        if (cancelled) return;
        // Exclude system account — overrides are for tenant pickers
        const tenants = (res.items || []).filter(
          (a) => a.id !== SYSTEM_ACCOUNT_ID && a.slug !== 'system',
        );
        setTenantAccounts(tenants);
        if (!overrideAccountId && tenants.length > 0) {
          setOverrideAccountId(tenants[0].id);
        }
      } catch {
        // Superadmin without accounts list still sees the selector empty state
      }
    })();
    return () => {
      cancelled = true;
    };
    // only load once when becoming superadmin
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [isSuperadmin]);

  useEffect(() => {
    if (routeCode) {
      setSelectedCode(routeCode);
    }
  }, [routeCode]);

  useEffect(() => {
    if (selectedCode) {
      fetchDetail(selectedCode);
    }
  }, [selectedCode, fetchDetail]);

  useEffect(() => {
    if (selected) {
      setSettingsName(selected.name);
      setSettingsDesc(selected.description || '');
      setSettingsActive(selected.is_active);
      setSettingsExtensible(selected.is_extensible);
    }
  }, [selected]);

  const filtered = useMemo(() => {
    return lists.filter((c) => {
      if (scopeFilter === 'system' && !c.is_system) return false;
      if (scopeFilter === 'account' && c.is_system) return false;
      const q = search.toLowerCase();
      if (!q) return true;
      return (
        c.code.toLowerCase().includes(q) ||
        c.name.toLowerCase().includes(q) ||
        (c.description || '').toLowerCase().includes(q)
      );
    });
  }, [lists, search, scopeFilter]);

  const selectCodelist = (code: string) => {
    setSelectedCode(code);
    navigate(`/admin/codelists/${code}`);
  };

  const onTabChange = (t: string) => {
    setTab(t);
    setSearchParams(t === 'values' ? {} : { tab: t });
  };

  const handleCreate = async () => {
    if (!codelistsService.isValidCodelistCode(formCode)) {
      setFormCodeError('Code must match ^[a-z][a-z0-9_]*$');
      return;
    }
    setFormCodeError(null);
    try {
      const created = await codelistsService.createCodelist({
        code: formCode,
        name: formName,
        description: formDesc || null,
        scope: isSuperadmin ? formScope : 'account',
        is_extensible: formExtensible,
      });
      toast({ title: 'Codelist created', description: created.code });
      setCreateOpen(false);
      setFormCode('');
      setFormName('');
      setFormDesc('');
      await fetchLists();
      selectCodelist(created.code);
    } catch (err) {
      toast({ title: 'Create failed', description: handleApiError(err), variant: 'destructive' });
    }
  };

  const openAddValue = () => {
    setEditingValue(null);
    setVCode('');
    setVDef('');
    setVSort(0);
    setVActive(true);
    setVLabels([{ language: 'en', label: '' }]);
    setVMeta('{}');
    setValueDialogOpen(true);
  };

  const openEditValue = (v: CodelistValue) => {
    setEditingValue(v);
    setVCode(v.code);
    setVDef(v.definition || '');
    setVSort(v.sort_order);
    setVActive(v.is_active);
    setVLabels(
      v.labels && v.labels.length > 0
        ? v.labels.map((l) => ({ language: l.language, label: l.label }))
        : [{ language: 'en', label: '' }],
    );
    setVMeta(JSON.stringify(v.metadata || {}, null, 2));
    setValueDialogOpen(true);
  };

  const saveValue = async () => {
    if (!selectedCode) return;
    let metadata: Record<string, unknown> | null = null;
    try {
      metadata = vMeta.trim() ? JSON.parse(vMeta) : null;
    } catch {
      toast({ title: 'Invalid metadata JSON', variant: 'destructive' });
      return;
    }
    const labels = vLabels.filter((l) => l.label.trim());
    try {
      if (editingValue) {
        await codelistsService.updateValue(selectedCode, editingValue.code, {
          definition: vDef || null,
          sort_order: vSort,
          is_active: vActive,
          metadata,
        });
        if (labels.length) {
          await codelistsService.upsertLabels(selectedCode, editingValue.code, labels);
        }
      } else {
        if (!vCode.trim()) {
          toast({ title: 'Value code is required', variant: 'destructive' });
          return;
        }
        await codelistsService.createValue(selectedCode, {
          code: vCode.trim(),
          definition: vDef || null,
          sort_order: vSort,
          is_active: vActive,
          metadata,
          labels: labels.length ? labels : undefined,
        });
      }
      toast({ title: editingValue ? 'Value updated' : 'Value created' });
      setValueDialogOpen(false);
      await fetchDetail(selectedCode);
    } catch (err) {
      toast({ title: 'Save failed', description: handleApiError(err), variant: 'destructive' });
    }
  };

  const deactivateValue = async (v: CodelistValue) => {
    if (!selectedCode) return;
    try {
      await codelistsService.updateValue(selectedCode, v.code, { is_active: false });
      toast({ title: 'Value deactivated', description: v.code });
      await fetchDetail(selectedCode);
    } catch (err) {
      toast({ title: 'Deactivate failed', description: handleApiError(err), variant: 'destructive' });
    }
  };

  const toggleHide = async (valueCode: string, hidden: boolean) => {
    if (!selectedCode) return;
    if (isSuperadmin && !overrideAccountId) {
      toast({
        title: 'Select an account',
        description: 'Choose which tenant account to apply overrides for.',
        variant: 'destructive',
      });
      return;
    }
    const accountIdParam = isSuperadmin ? overrideAccountId : undefined;
    try {
      if (hidden) {
        await codelistsService.setOverride(
          selectedCode,
          valueCode,
          { visibility: 'hidden' },
          accountIdParam,
        );
      } else {
        await codelistsService.clearOverride(
          selectedCode,
          valueCode,
          accountIdParam,
        );
      }
      await fetchDetail(selectedCode);
    } catch (err) {
      toast({ title: 'Override failed', description: handleApiError(err), variant: 'destructive' });
    }
  };

  const toggleDefault = async (valueCode: string, makeDefault: boolean) => {
    if (!selectedCode) return;
    if (isSuperadmin && !overrideAccountId) {
      toast({
        title: 'Select an account',
        description: 'Choose which tenant account to apply overrides for.',
        variant: 'destructive',
      });
      return;
    }
    const accountIdParam = isSuperadmin ? overrideAccountId : undefined;
    try {
      // Default toggle is disabled when hidden; always keep value visible
      await codelistsService.setOverride(
        selectedCode,
        valueCode,
        {
          visibility: 'visible',
          is_default: makeDefault,
        },
        accountIdParam,
      );
      await fetchDetail(selectedCode);
    } catch (err) {
      toast({
        title: 'Default update failed',
        description: handleApiError(err),
        variant: 'destructive',
      });
    }
  };

  const saveSettings = async () => {
    if (!selectedCode || !selected) return;
    try {
      await codelistsService.updateCodelist(selectedCode, {
        name: settingsName,
        description: settingsDesc || null,
        is_active: settingsActive,
        is_extensible: selected.is_system ? settingsExtensible : undefined,
      });
      toast({ title: 'Settings saved' });
      await fetchLists();
    } catch (err) {
      toast({ title: 'Save failed', description: handleApiError(err), variant: 'destructive' });
    }
  };

  const deactivateCodelist = async () => {
    if (!selectedCode || !selected) return;
    try {
      await codelistsService.deleteCodelist(selectedCode, false);
      toast({ title: 'Codelist deactivated' });
      await fetchLists();
    } catch (err) {
      toast({ title: 'Deactivate failed', description: handleApiError(err), variant: 'destructive' });
    }
  };

  /** Superadmin: download versioned JSON package for selected codelist. */
  const handleExport = async () => {
    if (!selectedCode) return;
    try {
      const pkg = await codelistsService.exportCodelist(selectedCode);
      const blob = new Blob([JSON.stringify(pkg, null, 2)], {
        type: 'application/json',
      });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `codelist-${selectedCode}.json`;
      a.setAttribute('data-testid', 'codelist-export-download');
      document.body.appendChild(a);
      a.click();
      a.remove();
      URL.revokeObjectURL(url);
      toast({ title: 'Exported', description: `${selectedCode} package downloaded` });
    } catch (err) {
      toast({
        title: 'Export failed',
        description: handleApiError(err),
        variant: 'destructive',
      });
    }
  };

  /** Superadmin: import package JSON from file picker. */
  const handleImportFile = async (file: File | null) => {
    if (!file) return;
    try {
      const text = await file.text();
      const packageData = JSON.parse(text) as Record<string, unknown>;
      const created = await codelistsService.importCodelist(packageData);
      toast({ title: 'Imported', description: created.code });
      await fetchLists();
      selectCodelist(created.code);
    } catch (err) {
      toast({
        title: 'Import failed',
        description: handleApiError(err),
        variant: 'destructive',
      });
    } finally {
      if (importFileRef.current) importFileRef.current.value = '';
    }
  };

  const labelPreview = (v: CodelistValue) => {
    const labels = v.labels || [];
    const preferred =
      labels.find((l) => l.language === langPreview) ||
      labels.find((l) => l.language === 'en');
    return preferred?.label || v.code;
  };

  const displayedValues = values.filter((v) => showInactive || v.is_active);
  const overrideByValue = useMemo(() => {
    const m = new Map<string, CodelistOverride>();
    for (const o of overrides) m.set(o.value_id, o);
    return m;
  }, [overrides]);

  const canEditSelected =
    isAdmin &&
    selected &&
    (selected.is_system ? isSuperadmin : true);

  return (
    <div className="flex h-[calc(100vh-8rem)] gap-4" data-testid="codelists-workspace">
      {/* Rail */}
      <Card className="w-72 shrink-0 flex flex-col overflow-hidden">
        <CardHeader className="pb-3 space-y-3">
          <div className="flex items-center justify-between gap-1">
            <CardTitle className="text-lg flex items-center gap-2">
              <BookMarked className="h-5 w-5" />
              Codelists
            </CardTitle>
            <div className="flex items-center gap-1">
              {isSuperadmin && (
                <>
                  <input
                    ref={importFileRef}
                    type="file"
                    accept="application/json,.json"
                    className="hidden"
                    data-testid="codelist-import-input"
                    onChange={(e) => {
                      const f = e.target.files?.[0] ?? null
                      void handleImportFile(f)
                    }}
                  />
                  <Button
                    size="sm"
                    variant="outline"
                    onClick={() => importFileRef.current?.click()}
                    data-testid="codelist-import-btn"
                    title="Import package (superadmin)"
                  >
                    <Upload className="h-4 w-4" />
                  </Button>
                </>
              )}
              {isAdmin && (
                <Button size="sm" onClick={() => setCreateOpen(true)} data-testid="codelist-create-btn">
                  <Plus className="h-4 w-4" />
                </Button>
              )}
            </div>
          </div>
          <div className="relative">
            <Search className="absolute left-2 top-2.5 h-4 w-4 text-muted-foreground" />
            <Input
              className="pl-8"
              placeholder="Search code or name"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              data-testid="codelist-search"
            />
          </div>
          <div className="flex gap-1">
            {(['all', 'system', 'account'] as ScopeFilter[]).map((f) => (
              <Button
                key={f}
                size="sm"
                variant={scopeFilter === f ? 'default' : 'outline'}
                className="flex-1 capitalize text-xs"
                onClick={() => setScopeFilter(f)}
              >
                {f}
              </Button>
            ))}
          </div>
        </CardHeader>
        <CardContent className="flex-1 p-0 overflow-hidden">
          {loading ? (
            <div className="p-4 space-y-2">
              <Skeleton className="h-10 w-full" />
              <Skeleton className="h-10 w-full" />
              <Skeleton className="h-10 w-full" />
            </div>
          ) : error ? (
            <p className="p-4 text-sm text-destructive">{error}</p>
          ) : filtered.length === 0 ? (
            <div className="p-4 text-sm text-muted-foreground space-y-2" data-testid="codelist-empty-rail">
              <p>No codelists match.</p>
              <p>
                <strong>System</strong> dictionaries are shared by all accounts.
                <strong> Account</strong> lists are private to your tenant.
              </p>
            </div>
          ) : (
            <ScrollArea className="h-full">
              <ul className="p-2 space-y-1">
                {filtered.map((c) => (
                  <li key={c.id}>
                    <button
                      type="button"
                      onClick={() => selectCodelist(c.code)}
                      className={cn(
                        'w-full text-left rounded-md px-3 py-2 text-sm hover:bg-muted transition-colors',
                        selectedCode === c.code && 'bg-muted font-medium',
                      )}
                      data-testid={`codelist-rail-${c.code}`}
                    >
                      <div className="flex items-center gap-2">
                        <span className="truncate">{c.name}</span>
                        {c.is_builtin && <Lock className="h-3 w-3 shrink-0 text-muted-foreground" />}
                      </div>
                      <div className="flex items-center gap-1 mt-1">
                        <code className="text-xs text-muted-foreground">{c.code}</code>
                        <Badge variant="outline" className="text-[10px] h-4">
                          {c.is_system ? 'System' : 'Account'}
                        </Badge>
                        {!c.is_active && (
                          <Badge variant="secondary" className="text-[10px] h-4">
                            inactive
                          </Badge>
                        )}
                      </div>
                    </button>
                  </li>
                ))}
              </ul>
            </ScrollArea>
          )}
        </CardContent>
      </Card>

      {/* Detail */}
      <div className="flex-1 min-w-0 flex flex-col">
        {!selected ? (
          <Card className="flex-1 flex items-center justify-center" data-testid="codelist-empty-detail">
            <CardContent className="text-center space-y-3 py-16 max-w-md">
              <BookMarked className="h-12 w-12 mx-auto text-muted-foreground" />
              <CardTitle>Codelists</CardTitle>
              <CardDescription>
                Shared reference dictionaries with stable submission codes and
                multi-language labels. System lists (like <code>regions</code>) are
                defined once; account overrides hide or default values without copying
                rows. Pick a list from the rail or create a new one.
              </CardDescription>
              {isAdmin && (
                <Button onClick={() => setCreateOpen(true)}>
                  <Plus className="h-4 w-4 mr-2" />
                  Create codelist
                </Button>
              )}
            </CardContent>
          </Card>
        ) : (
          <Card className="flex-1 flex flex-col overflow-hidden">
            <CardHeader className="pb-2">
              <div className="flex items-start justify-between gap-4">
                <div>
                  <CardTitle className="flex items-center gap-2">
                    {selected.name}
                    {selected.is_builtin && <Lock className="h-4 w-4 text-muted-foreground" />}
                  </CardTitle>
                  <CardDescription className="flex flex-wrap items-center gap-2 mt-1">
                    <code>{selected.code}</code>
                    <Badge variant="outline">{selected.is_system ? 'System' : 'Account'}</Badge>
                    {selected.is_extensible && <Badge variant="secondary">Extensible</Badge>}
                    {!selected.is_active && <Badge variant="destructive">Inactive</Badge>}
                  </CardDescription>
                </div>
                <div className="flex gap-2">
                  {isSuperadmin && selected.is_system && (
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => void handleExport()}
                      data-testid="codelist-export-btn"
                      title="Export package JSON"
                    >
                      <Download className="h-4 w-4 mr-1" />
                      Export
                    </Button>
                  )}
                  <Button variant="outline" size="sm" onClick={() => fetchDetail(selected.code)}>
                    <RefreshCw className="h-4 w-4" />
                  </Button>
                </div>
              </div>
            </CardHeader>
            <CardContent className="flex-1 overflow-auto">
              <Tabs value={tab} onValueChange={onTabChange}>
                <TabsList>
                  <TabsTrigger value="values">Values</TabsTrigger>
                  <TabsTrigger value="overrides">Overrides</TabsTrigger>
                  <TabsTrigger value="settings">Settings</TabsTrigger>
                </TabsList>

                <TabsContent value="values" className="space-y-4 mt-4">
                  <div className="flex flex-wrap items-center gap-3">
                    <div className="flex items-center gap-2">
                      <Label htmlFor="lang-preview">Label language</Label>
                      <Select value={langPreview} onValueChange={setLangPreview}>
                        <SelectTrigger id="lang-preview" className="w-24" data-testid="lang-preview">
                          <SelectValue />
                        </SelectTrigger>
                        <SelectContent>
                          <SelectItem value="en">en</SelectItem>
                          <SelectItem value="ja">ja</SelectItem>
                        </SelectContent>
                      </Select>
                    </div>
                    <div className="flex items-center gap-2">
                      <Switch
                        id="show-inactive"
                        checked={showInactive}
                        onCheckedChange={setShowInactive}
                      />
                      <Label htmlFor="show-inactive">Show inactive</Label>
                    </div>
                    {canEditSelected && (
                      <Button size="sm" onClick={openAddValue} data-testid="add-value-btn">
                        <Plus className="h-4 w-4 mr-1" />
                        Add value
                      </Button>
                    )}
                  </div>
                  {detailLoading ? (
                    <Skeleton className="h-32 w-full" />
                  ) : displayedValues.length === 0 ? (
                    <p className="text-sm text-muted-foreground" data-testid="values-empty">
                      No values yet. Submission codes are stable machine keys; labels are
                      for display only.
                    </p>
                  ) : (
                    <div className="rounded-md border overflow-x-auto">
                      <table className="w-full text-sm" data-testid="values-table">
                        <thead>
                          <tr className="border-b bg-muted/50 text-left">
                            <th className="p-2 font-medium">Code</th>
                            <th className="p-2 font-medium">Label</th>
                            <th className="p-2 font-medium">Sort</th>
                            <th className="p-2 font-medium">Scope</th>
                            <th className="p-2 font-medium">Status</th>
                            <th className="p-2 font-medium">Actions</th>
                          </tr>
                        </thead>
                        <tbody>
                          {displayedValues.map((v) => (
                            <tr key={v.id} className="border-b">
                              <td className="p-2 font-mono">{v.code}</td>
                              <td className="p-2">{labelPreview(v)}</td>
                              <td className="p-2">{v.sort_order}</td>
                              <td className="p-2">
                                <Badge variant="outline" className="text-xs">
                                  {v.scope}
                                </Badge>
                              </td>
                              <td className="p-2">
                                {v.is_active ? (
                                  <Badge className="text-xs">active</Badge>
                                ) : (
                                  <Badge variant="secondary" className="text-xs">
                                    inactive
                                  </Badge>
                                )}
                              </td>
                              <td className="p-2 space-x-1">
                                {canEditSelected && (
                                  <>
                                    <Button size="sm" variant="ghost" onClick={() => openEditValue(v)}>
                                      Edit
                                    </Button>
                                    {v.is_active && (
                                      <Button
                                        size="sm"
                                        variant="ghost"
                                        onClick={() => deactivateValue(v)}
                                      >
                                        Deactivate
                                      </Button>
                                    )}
                                  </>
                                )}
                              </td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  )}
                </TabsContent>

                <TabsContent value="overrides" className="space-y-4 mt-4">
                  <div
                    className="rounded-md border border-dashed p-3 text-sm text-muted-foreground"
                    data-testid="overrides-callout"
                  >
                    Shared values are defined once. Overrides are <strong>deltas</strong> only
                    (hide, default, sort). New system values appear for all accounts unless
                    hidden.
                    {isSuperadmin && (
                      <>
                        {' '}
                        As superadmin, pick a <strong>tenant account</strong> to apply
                        overrides for (system account cannot hold product overrides).
                      </>
                    )}
                  </div>
                  {isSuperadmin && (
                    <div className="flex flex-wrap items-center gap-2 max-w-md">
                      <Label htmlFor="override-account">Account</Label>
                      <Select
                        value={overrideAccountId || undefined}
                        onValueChange={(id) => {
                          setOverrideAccountId(id);
                        }}
                      >
                        <SelectTrigger
                          id="override-account"
                          className="flex-1 min-w-[12rem]"
                          data-testid="override-account-select"
                        >
                          <SelectValue placeholder="Select tenant account" />
                        </SelectTrigger>
                        <SelectContent>
                          {tenantAccounts.map((a) => (
                            <SelectItem key={a.id} value={a.id}>
                              {a.name} ({a.slug})
                            </SelectItem>
                          ))}
                        </SelectContent>
                      </Select>
                    </div>
                  )}
                  {!isAdmin ? (
                    <p className="text-sm text-muted-foreground">Admin role required to manage overrides.</p>
                  ) : isSuperadmin && !overrideAccountId ? (
                    <p className="text-sm text-muted-foreground" data-testid="override-account-required">
                      Select a tenant account above to manage visibility and defaults.
                    </p>
                  ) : detailLoading ? (
                    <Skeleton className="h-32 w-full" />
                  ) : (
                    <>
                      <div className="rounded-md border overflow-x-auto">
                        <table className="w-full text-sm" data-testid="overrides-table">
                          <thead>
                            <tr className="border-b bg-muted/50 text-left">
                              <th className="p-2">Code</th>
                              <th className="p-2">Label</th>
                              <th className="p-2">Visible</th>
                              <th className="p-2">Default</th>
                            </tr>
                          </thead>
                          <tbody>
                            {values
                              .filter((v) => v.is_active)
                              .map((v) => {
                                const ov = overrideByValue.get(v.id);
                                const hidden = ov?.visibility === 'hidden';
                                const overridesDisabled =
                                  isSuperadmin && !overrideTargetAccountId;
                                return (
                                  <tr key={v.id} className="border-b">
                                    <td className="p-2 font-mono">{v.code}</td>
                                    <td className="p-2">{labelPreview(v)}</td>
                                    <td className="p-2">
                                      <Switch
                                        checked={!hidden}
                                        disabled={overridesDisabled}
                                        onCheckedChange={(vis) => toggleHide(v.code, !vis)}
                                        aria-label={`Visibility for ${v.code}`}
                                      />
                                    </td>
                                    <td className="p-2">
                                      <Switch
                                        checked={Boolean(ov?.is_default)}
                                        disabled={hidden || overridesDisabled}
                                        onCheckedChange={(on) =>
                                          void toggleDefault(v.code, on)
                                        }
                                        aria-label={`Default for ${v.code}`}
                                        data-testid={`default-toggle-${v.code}`}
                                      />
                                    </td>
                                  </tr>
                                );
                              })}
                          </tbody>
                        </table>
                      </div>
                      <div data-testid="effective-preview">
                        <h3 className="font-medium mb-2">Effective preview ({langPreview})</h3>
                        <ul className="text-sm space-y-1 list-disc pl-5">
                          {effective.map((e) => (
                            <li key={e.code}>
                              <code>{e.code}</code> — {e.label}
                              {e.is_default && (
                                <Badge className="ml-2 text-[10px]" variant="secondary">
                                  default
                                </Badge>
                              )}
                            </li>
                          ))}
                          {effective.length === 0 && (
                            <li className="list-none text-muted-foreground">No effective values</li>
                          )}
                        </ul>
                      </div>
                    </>
                  )}
                </TabsContent>

                <TabsContent value="settings" className="space-y-4 mt-4 max-w-lg">
                  <div className="space-y-2">
                    <Label>Code (immutable)</Label>
                    <Input value={selected.code} disabled />
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="settings-name">Name</Label>
                    <Input
                      id="settings-name"
                      value={settingsName}
                      onChange={(e) => setSettingsName(e.target.value)}
                      disabled={!canEditSelected}
                    />
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="settings-desc">Description</Label>
                    <Textarea
                      id="settings-desc"
                      value={settingsDesc}
                      onChange={(e) => setSettingsDesc(e.target.value)}
                      disabled={!canEditSelected}
                    />
                  </div>
                  <div className="flex items-center gap-2">
                    <Switch
                      id="settings-active"
                      checked={settingsActive}
                      onCheckedChange={setSettingsActive}
                      disabled={!canEditSelected}
                    />
                    <Label htmlFor="settings-active">Active</Label>
                  </div>
                  {selected.is_system && isSuperadmin && (
                    <div className="flex items-center gap-2">
                      <Switch
                        id="settings-ext"
                        checked={settingsExtensible}
                        onCheckedChange={setSettingsExtensible}
                      />
                      <Label htmlFor="settings-ext">Extensible by accounts</Label>
                    </div>
                  )}
                  {canEditSelected && (
                    <div className="flex gap-2">
                      <Button onClick={saveSettings}>Save settings</Button>
                      {selected.is_builtin ? (
                        <p className="text-sm text-muted-foreground self-center">
                          Builtin lists cannot be hard-deleted; deactivate instead.
                        </p>
                      ) : (
                        <Button variant="destructive" onClick={deactivateCodelist}>
                          Deactivate
                        </Button>
                      )}
                    </div>
                  )}
                </TabsContent>
              </Tabs>
            </CardContent>
          </Card>
        )}
      </div>

      {/* Create dialog */}
      <Dialog open={createOpen} onOpenChange={setCreateOpen}>
        <DialogContent data-testid="create-codelist-dialog">
          <DialogHeader>
            <DialogTitle>Create codelist</DialogTitle>
            <DialogDescription>
              Submission codes use a stable machine key. Display labels are managed per
              value and language.
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-3">
            <div className="space-y-1">
              <Label htmlFor="cl-code">Code</Label>
              <Input
                id="cl-code"
                value={formCode}
                onChange={(e) => setFormCode(e.target.value)}
                placeholder="my_statuses"
                data-testid="create-code-input"
              />
              {formCodeError && (
                <p className="text-sm text-destructive" data-testid="create-code-error">
                  {formCodeError}
                </p>
              )}
            </div>
            <div className="space-y-1">
              <Label htmlFor="cl-name">Name</Label>
              <Input
                id="cl-name"
                value={formName}
                onChange={(e) => setFormName(e.target.value)}
              />
            </div>
            <div className="space-y-1">
              <Label htmlFor="cl-desc">Description</Label>
              <Textarea
                id="cl-desc"
                value={formDesc}
                onChange={(e) => setFormDesc(e.target.value)}
              />
            </div>
            {isSuperadmin && (
              <div className="space-y-1">
                <Label>Scope</Label>
                <Select
                  value={formScope}
                  onValueChange={(v) => setFormScope(v as 'system' | 'account')}
                >
                  <SelectTrigger data-testid="create-scope-select">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="system">System</SelectItem>
                    <SelectItem value="account">Account</SelectItem>
                  </SelectContent>
                </Select>
              </div>
            )}
            {isSuperadmin && formScope === 'system' && (
              <div className="flex items-center gap-2">
                <Switch checked={formExtensible} onCheckedChange={setFormExtensible} />
                <Label>Extensible</Label>
              </div>
            )}
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setCreateOpen(false)}>
              Cancel
            </Button>
            <Button onClick={handleCreate} disabled={!formCode || !formName}>
              Create
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Value dialog */}
      <Dialog open={valueDialogOpen} onOpenChange={setValueDialogOpen}>
        <DialogContent
          className="max-w-lg max-h-[90vh] flex flex-col gap-4 overflow-hidden"
          data-testid="value-dialog"
        >
          <DialogHeader className="shrink-0">
            <DialogTitle>{editingValue ? 'Edit value' : 'Add value'}</DialogTitle>
            <DialogDescription>
              The <strong>submission code</strong> is stored in application data and should
              not change. Labels are for UI display only.
            </DialogDescription>
          </DialogHeader>
          <div className="min-h-0 flex-1 space-y-3 overflow-y-auto pr-1">
            <div className="space-y-1">
              <Label>Code</Label>
              <Input
                value={vCode}
                onChange={(e) => setVCode(e.target.value)}
                disabled={!!editingValue}
                data-testid="value-code-input"
              />
            </div>
            <div className="space-y-1">
              <Label>Definition</Label>
              <Textarea value={vDef} onChange={(e) => setVDef(e.target.value)} />
            </div>
            <div className="space-y-1">
              <Label>Sort order</Label>
              <Input
                type="number"
                value={vSort}
                onChange={(e) => setVSort(Number(e.target.value))}
              />
            </div>
            <div className="flex items-center gap-2">
              <Switch checked={vActive} onCheckedChange={setVActive} />
              <Label>Active</Label>
            </div>
            <div className="space-y-2">
              <Label>Labels</Label>
              <ScrollArea
                className="h-40 max-h-40 rounded-md border"
                data-testid="labels-scroll"
              >
                <div className="space-y-2 p-2 pr-3">
                  {vLabels.map((row, idx) => (
                    <div key={idx} className="flex gap-2">
                      <Input
                        className="w-20 shrink-0"
                        value={row.language}
                        onChange={(e) => {
                          const next = [...vLabels];
                          next[idx] = { ...next[idx], language: e.target.value };
                          setVLabels(next);
                        }}
                        placeholder="en"
                      />
                      <Input
                        className="flex-1"
                        value={row.label}
                        onChange={(e) => {
                          const next = [...vLabels];
                          next[idx] = { ...next[idx], label: e.target.value };
                          setVLabels(next);
                        }}
                        placeholder="Display label"
                      />
                    </div>
                  ))}
                </div>
              </ScrollArea>
              <Button
                type="button"
                size="sm"
                variant="outline"
                onClick={() => setVLabels([...vLabels, { language: 'ja', label: '' }])}
              >
                Add language
              </Button>
            </div>
            <div className="space-y-1">
              <Label>Metadata (JSON)</Label>
              <Textarea value={vMeta} onChange={(e) => setVMeta(e.target.value)} className="font-mono text-xs" />
            </div>
          </div>
          <DialogFooter className="shrink-0">
            <Button variant="outline" onClick={() => setValueDialogOpen(false)}>
              Cancel
            </Button>
            <Button onClick={saveValue}>Save</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* keep Link for typecheck/navigation smoke */}
      <span className="sr-only">
        <Link to="/admin/codelists">Codelists home</Link>
      </span>
    </div>
  );
}
