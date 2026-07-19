/**
 * Full-page structured hook editor (create + edit).
 * Three regions: trigger/condition | action pipeline | action properties.
 */

import { useCallback, useEffect, useState } from 'react';
import { Link, useNavigate, useParams } from 'react-router';
import { ArrowLeft, Save } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Switch } from '@/components/ui/switch';
import { Skeleton } from '@/components/ui/skeleton';
import { useToast } from '@/hooks/use-toast';
import { hooksService } from '@/services/hooks.service';
import { getCollections } from '@/services/collections.service';
import { emailService } from '@/services/email.service';
import {
  DEFAULT_FORM,
  formToPayload,
  hookToForm,
  moveAction,
  newAction,
  removeActionAt,
  validateHookForm,
  type HookFormState,
} from './hookFormState';
import { TriggerConfigCard, type PickerOption } from './TriggerConfigCard';
import { ConditionCard } from './ConditionCard';
import { ActionPipeline } from './ActionPipeline';
import { ActionPropertiesPanel } from './ActionPropertiesPanel';
import { TemplatePickerDialog } from './templates/TemplatePickerDialog';
import type { HookTemplate } from './templates/hookTemplates';

export default function HookEditorPage() {
  const { id } = useParams<{ id: string }>();
  const isEdit = Boolean(id);
  const navigate = useNavigate();
  const { toast } = useToast();

  const [form, setForm] = useState<HookFormState>(DEFAULT_FORM);
  const [selectedIndex, setSelectedIndex] = useState<number | null>(null);
  const [loading, setLoading] = useState(isEdit);
  const [saving, setSaving] = useState(false);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [templateChosen, setTemplateChosen] = useState(isEdit);

  const [collections, setCollections] = useState<PickerOption[]>([]);
  const [collectionsLoading, setCollectionsLoading] = useState(true);
  const [collectionsFallback, setCollectionsFallback] = useState(false);
  const [emailTemplates, setEmailTemplates] = useState<PickerOption[]>([]);
  const [emailFallback, setEmailFallback] = useState(false);

  const patchForm = useCallback((patch: Partial<HookFormState>) => {
    setForm((prev) => ({ ...prev, ...patch }));
  }, []);

  // Load pickers (non-blocking)
  useEffect(() => {
    let cancelled = false;
    (async () => {
      setCollectionsLoading(true);
      try {
        const res = await getCollections({ page_size: 200 });
        if (cancelled) return;
        const items = (res.items ?? []).map((c) => ({
          value: c.name,
          label: c.name,
        }));
        setCollections(items);
        setCollectionsFallback(items.length === 0);
      } catch {
        if (!cancelled) {
          setCollections([]);
          setCollectionsFallback(true);
        }
      } finally {
        if (!cancelled) setCollectionsLoading(false);
      }
    })();

    (async () => {
      try {
        const templates = await emailService.listEmailTemplates();
        if (cancelled) return;
        const items = (templates ?? []).map((t) => ({
          value: t.id,
          label: t.template_type
            ? `${t.template_type}${t.locale ? ` (${t.locale})` : ''}`
            : t.id,
        }));
        setEmailTemplates(items);
        setEmailFallback(items.length === 0);
      } catch {
        if (!cancelled) {
          setEmailTemplates([]);
          setEmailFallback(true);
        }
      }
    })();

    return () => {
      cancelled = true;
    };
  }, []);

  // Load existing hook
  useEffect(() => {
    if (!id) {
      setLoading(false);
      setLoadError(null);
      setForm(DEFAULT_FORM);
      setSelectedIndex(null);
      setTemplateChosen(false);
      return;
    }

    let cancelled = false;
    setLoading(true);
    setLoadError(null);
    setTemplateChosen(true);

    (async () => {
      try {
        const h = await hooksService.get(id);
        if (cancelled) return;
        const next = hookToForm(h);
        setForm(next);
        setSelectedIndex(next.actions.length > 0 ? 0 : null);
      } catch {
        if (cancelled) return;
        setLoadError('Failed to load hook.');
        setForm(DEFAULT_FORM);
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();

    return () => {
      cancelled = true;
    };
  }, [id]);

  const handleTemplateSelect = (tpl: HookTemplate) => {
    const next = tpl.build();
    setForm(next);
    setSelectedIndex(next.actions.length > 0 ? 0 : null);
    setTemplateChosen(true);
  };

  const handleTemplateCancel = () => {
    navigate('/admin/hooks');
  };

  const handleAddAction = () => {
    const lastType =
      form.actions.length > 0
        ? form.actions[form.actions.length - 1].type
        : 'send_webhook';
    const action = newAction(lastType || 'send_webhook');
    const actions = [...form.actions, action];
    setForm((prev) => ({ ...prev, actions }));
    setSelectedIndex(actions.length - 1);
  };

  const handleMove = (index: number, direction: -1 | 1) => {
    setForm((prev) => {
      const actions = moveAction(prev.actions, index, direction);
      return { ...prev, actions };
    });
    setSelectedIndex((prev) => {
      if (prev === null) return null;
      if (prev === index) return index + direction;
      if (prev === index + direction) return index;
      return prev;
    });
  };

  const handleRemove = (index: number) => {
    setForm((prev) => {
      const { actions } = removeActionAt(prev.actions, index);
      return { ...prev, actions };
    });
    setSelectedIndex((prev) => {
      if (prev === null) return null;
      const { selectedIndex: next } = removeActionAt(form.actions, index);
      return next;
    });
  };

  const handleActionChange = (updated: typeof form.actions[0]) => {
    if (selectedIndex === null) return;
    setForm((prev) => {
      const actions = [...prev.actions];
      actions[selectedIndex] = updated;
      return { ...prev, actions };
    });
  };

  const handleSave = async () => {
    const validation = validateHookForm(form);
    if (!validation.ok) {
      toast({
        title: 'Validation failed',
        description: validation.errors[0],
        variant: 'destructive',
      });
      return;
    }

    setSaving(true);
    try {
      const payload = formToPayload(form);
      if (isEdit && id) {
        const updated = await hooksService.update(id, payload);
        setForm(hookToForm(updated));
        toast({ title: 'Hook updated' });
      } else {
        const created = await hooksService.create(payload);
        toast({ title: 'Hook created' });
        navigate(`/admin/hooks/${created.id}/edit`, { replace: true });
      }
    } catch (err: unknown) {
      const msg =
        (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail ??
        'Failed to save hook';
      toast({ title: 'Error', description: String(msg), variant: 'destructive' });
    } finally {
      setSaving(false);
    }
  };

  // Cmd/Ctrl+S save
  useEffect(() => {
    if (!templateChosen || loading || loadError) return;
    const onKey = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key === 's') {
        const tag = (e.target as HTMLElement)?.tagName;
        if (tag === 'INPUT' || tag === 'TEXTAREA' || tag === 'SELECT') {
          // still allow save from inputs
        }
        e.preventDefault();
        void handleSave();
      }
    };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
    // eslint-disable-next-line react-hooks/exhaustive-deps -- save uses latest form via closure on each render registration
  }, [templateChosen, loading, loadError, form, isEdit, id]);

  if (loading) {
    return (
      <div className="flex flex-col h-full p-6 gap-4" data-testid="hook-editor-loading">
        <Skeleton className="h-8 w-64" />
        <Skeleton className="h-full w-full min-h-[240px]" />
      </div>
    );
  }

  if (isEdit && loadError) {
    return (
      <div
        className="flex flex-col items-center justify-center h-full gap-4 p-6"
        data-testid="hook-editor-error"
      >
        <p className="text-sm text-destructive">{loadError}</p>
        <Button variant="outline" asChild>
          <Link to="/admin/hooks">Back to Hooks</Link>
        </Button>
      </div>
    );
  }

  if (!isEdit && !templateChosen) {
    return (
      <div className="flex flex-col h-full min-h-0" data-testid="hook-editor-template-gate">
        <TemplatePickerDialog
          open
          onSelect={handleTemplateSelect}
          onCancel={handleTemplateCancel}
        />
      </div>
    );
  }

  const selectedAction =
    selectedIndex !== null && form.actions[selectedIndex]
      ? form.actions[selectedIndex]
      : null;

  return (
    <div className="flex flex-col h-full min-h-0" data-testid="hook-editor-page">
      {/* Sticky header */}
      <div className="shrink-0 border-b bg-background px-4 py-3 space-y-2">
        <div className="flex flex-wrap items-center gap-3">
          <Button variant="ghost" size="sm" asChild className="h-8 px-2">
            <Link to="/admin/hooks" data-testid="hook-editor-back">
              <ArrowLeft className="h-4 w-4 mr-1" />
              Hooks
            </Link>
          </Button>
          <div className="flex-1 min-w-0 flex items-center gap-2">
            <Input
              className="max-w-md h-9 font-medium"
              placeholder="Hook name"
              value={form.name}
              onChange={(e) => patchForm({ name: e.target.value })}
              data-testid="hook-name-input"
            />
            <div className="flex items-center gap-2 shrink-0">
              <Switch
                id="hook-enabled"
                checked={form.enabled}
                onCheckedChange={(v) => patchForm({ enabled: v })}
                data-testid="hook-enabled-switch"
              />
              <Label htmlFor="hook-enabled" className="text-sm whitespace-nowrap">
                Enabled
              </Label>
            </div>
          </div>
          <div className="flex items-center gap-2">
            <Button
              variant="outline"
              size="sm"
              onClick={() => navigate('/admin/hooks')}
              data-testid="hook-editor-cancel"
            >
              Cancel
            </Button>
            <Button
              size="sm"
              onClick={() => void handleSave()}
              disabled={saving}
              data-testid="hook-editor-save"
            >
              <Save className="h-4 w-4 mr-1" />
              {saving ? 'Saving…' : 'Save'}
            </Button>
          </div>
        </div>
        <Input
          className="h-8 text-sm"
          placeholder="Description (optional)"
          value={form.description}
          onChange={(e) => patchForm({ description: e.target.value })}
          data-testid="hook-description-input"
        />
      </div>

      {/* Three regions */}
      <div
        className="flex-1 min-h-0 grid grid-cols-1 md:grid-cols-[280px_1fr_320px] border-t"
        data-testid="hook-editor-regions"
      >
        <div className="min-h-0 overflow-y-auto border-r p-3 space-y-3 bg-muted/20">
          <TriggerConfigCard
            form={form}
            onChange={patchForm}
            collections={collections}
            collectionsLoading={collectionsLoading}
            collectionsFallback={collectionsFallback}
          />
          <ConditionCard form={form} onChange={patchForm} />
        </div>
        <div className="min-h-0 overflow-hidden border-r">
          <ActionPipeline
            actions={form.actions}
            selectedIndex={selectedIndex}
            onSelect={setSelectedIndex}
            onAdd={handleAddAction}
            onMove={handleMove}
            onRemove={handleRemove}
          />
        </div>
        <div className="min-h-0 overflow-hidden bg-muted/10">
          <ActionPropertiesPanel
            action={selectedAction}
            selectedIndex={selectedIndex}
            onChange={handleActionChange}
            collections={collections}
            collectionsFallback={collectionsFallback}
            emailTemplates={emailTemplates}
            emailFallback={emailFallback}
          />
        </div>
      </div>
    </div>
  );
}
