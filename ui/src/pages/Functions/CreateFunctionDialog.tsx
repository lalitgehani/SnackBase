import { useState } from 'react';
import { Button } from '@/components/ui/button';
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
import { Switch } from '@/components/ui/switch';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { functionsService } from '@/services/functions.service';
import { useToast } from '@/hooks/use-toast';
import { FUNCTION_TEMPLATES, getTemplate } from './templates';

interface Props {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onCreated: (slug: string) => void;
}

function slugify(name: string): string {
  return name
    .toLowerCase()
    .replace(/[^a-z0-9_-]+/g, '-')
    .replace(/^-+|-+$/g, '')
    .slice(0, 64);
}

export function CreateFunctionDialog({ open, onOpenChange, onCreated }: Props) {
  const { toast } = useToast();
  const [loading, setLoading] = useState(false);
  const [name, setName] = useState('');
  const [slug, setSlug] = useState('');
  const [authRequired, setAuthRequired] = useState(true);
  const [templateId, setTemplateId] = useState('hello');
  const [slugTouched, setSlugTouched] = useState(false);

  const reset = () => {
    setName('');
    setSlug('');
    setAuthRequired(true);
    setTemplateId('hello');
    setSlugTouched(false);
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!name.trim() || !slug.trim()) return;
    setLoading(true);
    try {
      const tpl = getTemplate(templateId);
      const fn = await functionsService.create({
        name: name.trim(),
        slug: slug.trim(),
        auth_required: tpl?.auth_required ?? authRequired,
      });
      if (tpl) {
        try {
          await functionsService.deploy(fn.slug, {
            entrypoint: tpl.entrypoint,
            dependencies: tpl.dependencies,
            files: tpl.files,
          });
        } catch (deployErr: unknown) {
          const msg =
            (deployErr as { response?: { data?: { detail?: string } } })?.response?.data
              ?.detail ?? 'Created, but template deploy failed';
          toast({ title: 'Deploy warning', description: String(msg), variant: 'destructive' });
        }
      }
      toast({ title: 'Function created' });
      onCreated(fn.slug);
      onOpenChange(false);
      reset();
    } catch (err: unknown) {
      const msg =
        (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail ??
        'Failed to create function';
      toast({ title: 'Error', description: String(msg), variant: 'destructive' });
    } finally {
      setLoading(false);
    }
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-[520px]">
        <form onSubmit={handleSubmit}>
          <DialogHeader>
            <DialogTitle>Create Function</DialogTitle>
            <DialogDescription>
              Deploy Python handlers with pinned dependencies. Start from a template or a blank shell.
            </DialogDescription>
          </DialogHeader>

          <div className="grid gap-4 py-4">
            <div className="grid gap-2">
              <Label htmlFor="fn-name">Name</Label>
              <Input
                id="fn-name"
                value={name}
                onChange={(e) => {
                  setName(e.target.value);
                  if (!slugTouched) setSlug(slugify(e.target.value));
                }}
                placeholder="Hello World"
                required
              />
            </div>
            <div className="grid gap-2">
              <Label htmlFor="fn-slug">Slug</Label>
              <Input
                id="fn-slug"
                value={slug}
                onChange={(e) => {
                  setSlugTouched(true);
                  setSlug(e.target.value);
                }}
                placeholder="hello-world"
                pattern="^[a-z][a-z0-9_-]{1,63}$"
                required
              />
              <p className="text-xs text-muted-foreground">
                Lowercase letter start; letters, digits, _ and - only.
              </p>
            </div>
            <div className="grid gap-2">
              <Label>Template</Label>
              <Select value={templateId} onValueChange={setTemplateId}>
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {FUNCTION_TEMPLATES.map((t) => (
                    <SelectItem key={t.id} value={t.id}>
                      {t.name}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
              <p className="text-xs text-muted-foreground">
                {getTemplate(templateId)?.description}
              </p>
            </div>
            <div className="flex items-center justify-between">
              <div>
                <Label htmlFor="fn-auth">Require authentication</Label>
                <p className="text-xs text-muted-foreground">Default true (JWT / API key)</p>
              </div>
              <Switch
                id="fn-auth"
                checked={getTemplate(templateId)?.auth_required ?? authRequired}
                onCheckedChange={setAuthRequired}
              />
            </div>
          </div>

          <DialogFooter>
            <Button type="button" variant="outline" onClick={() => onOpenChange(false)} disabled={loading}>
              Cancel
            </Button>
            <Button type="submit" disabled={loading || !name.trim() || !slug.trim()}>
              {loading ? 'Creating…' : 'Create Function'}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}
