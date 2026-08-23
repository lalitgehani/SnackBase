/**
 * Secondary left rail listing collections with search, create, and collapse.
 */

import { useMemo, useState } from 'react';
import { Link, useNavigate, useParams } from 'react-router';
import {
  ChevronLeft,
  ChevronRight,
  Database,
  Keyboard,
  Plus,
  RefreshCw,
  Search,
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Badge } from '@/components/ui/badge';
import { ScrollArea } from '@/components/ui/scroll-area';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from '@/components/ui/popover';
import { useIsMobile } from '@/hooks/use-mobile';
import {
  COLLECTION_BROWSER_SEARCH_ID,
  SHORTCUTS_HELP_TRIGGER_ID,
} from '@/hooks/useCollectionsWorkspaceShortcuts';
import { cn } from '@/lib/utils';
import { useCollectionsWorkspace } from './CollectionsWorkspaceContext';

export default function CollectionBrowserRail() {
  const {
    collections,
    loading,
    error,
    refreshCollections,
    railCollapsed,
    setRailCollapsed,
    isSuperadmin,
  } = useCollectionsWorkspace();
  const { collectionName } = useParams<{ collectionName?: string }>();
  const navigate = useNavigate();
  const isMobile = useIsMobile();
  const [search, setSearch] = useState('');

  const filtered = useMemo(() => {
    const q = search.trim().toLowerCase();
    if (!q) return collections;
    return collections.filter((c) => c.name.toLowerCase().includes(q));
  }, [collections, search]);

  const collapsed = isMobile || railCollapsed;

  if (collapsed) {
    return (
      <aside
        className="flex w-14 shrink-0 flex-col border-r bg-muted/30"
        data-testid="collection-browser-rail-collapsed"
      >
        <div className="flex flex-col items-center gap-2 p-2 border-b">
          {!isMobile && (
            <Button
              variant="ghost"
              size="icon"
              className="h-8 w-8"
              onClick={() => setRailCollapsed(false)}
              title="Expand collection browser"
              aria-label="Expand collection browser"
            >
              <ChevronRight className="h-4 w-4" />
            </Button>
          )}
          {isSuperadmin && (
            <Button
              variant="default"
              size="icon"
              className="h-8 w-8"
              onClick={() => navigate('/admin/collections/new')}
              title="New collection"
              aria-label="New collection"
              data-testid="collections-new-collection"
            >
              <Plus className="h-4 w-4" />
            </Button>
          )}
          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <Button
                variant="outline"
                size="icon"
                className="h-8 w-8"
                title="Switch collection"
                aria-label="Switch collection"
              >
                <Database className="h-4 w-4" />
              </Button>
            </DropdownMenuTrigger>
            <DropdownMenuContent align="start" className="w-56 max-h-80 overflow-y-auto">
              {collections.length === 0 && (
                <DropdownMenuItem disabled>No collections</DropdownMenuItem>
              )}
              {collections.map((c) => (
                <DropdownMenuItem
                  key={c.id}
                  onClick={() => navigate(`/admin/collections/${c.name}`)}
                  className={cn(c.name === collectionName && 'bg-accent')}
                >
                  <span className="truncate">{c.name}</span>
                </DropdownMenuItem>
              ))}
            </DropdownMenuContent>
          </DropdownMenu>
        </div>
      </aside>
    );
  }

  return (
    <aside
      className="flex w-64 shrink-0 flex-col border-r bg-muted/30"
      data-testid="collection-browser-rail"
    >
      <div className="flex items-center justify-between gap-1 border-b p-3">
        <span className="text-sm font-semibold">Collections</span>
        <div className="flex items-center gap-0.5">
          <Button
            variant="ghost"
            size="icon"
            className="h-7 w-7"
            onClick={() => void refreshCollections()}
            disabled={loading}
            title="Refresh"
            aria-label="Refresh collections"
          >
            <RefreshCw className={cn('h-3.5 w-3.5', loading && 'animate-spin')} />
          </Button>
          <Popover>
            <PopoverTrigger asChild>
              <Button
                id={SHORTCUTS_HELP_TRIGGER_ID}
                variant="ghost"
                size="icon"
                className="h-7 w-7"
                title="Keyboard shortcuts"
                aria-label="Keyboard shortcuts"
                data-testid="collections-shortcuts-help"
              >
                <Keyboard className="h-3.5 w-3.5" />
              </Button>
            </PopoverTrigger>
            <PopoverContent align="start" className="w-64 text-sm" side="bottom">
              <p className="font-semibold mb-2">Keyboard shortcuts</p>
              <ul className="space-y-1.5 text-muted-foreground">
                <li className="flex justify-between gap-2">
                  <span>Focus collection search</span>
                  <kbd className="rounded border bg-muted px-1.5 font-mono text-xs text-foreground">
                    /
                  </kbd>
                </li>
                <li className="flex justify-between gap-2">
                  <span>Add schema field</span>
                  <kbd className="rounded border bg-muted px-1.5 font-mono text-xs text-foreground">
                    a
                  </kbd>
                </li>
                <li className="flex justify-between gap-2">
                  <span>Show this help</span>
                  <kbd className="rounded border bg-muted px-1.5 font-mono text-xs text-foreground">
                    ?
                  </kbd>
                </li>
              </ul>
              <p className="mt-2 text-xs text-muted-foreground">
                Shortcuts are disabled while typing in inputs.
              </p>
            </PopoverContent>
          </Popover>
          <Button
            variant="ghost"
            size="icon"
            className="h-7 w-7"
            onClick={() => setRailCollapsed(true)}
            title="Collapse collection browser"
            aria-label="Collapse collection browser"
          >
            <ChevronLeft className="h-4 w-4" />
          </Button>
        </div>
      </div>

      <div className="space-y-2 border-b p-3">
        <div className="relative">
          <Search className="absolute left-2.5 top-1/2 h-3.5 w-3.5 -translate-y-1/2 text-muted-foreground" />
          <Input
            id={COLLECTION_BROWSER_SEARCH_ID}
            data-testid={COLLECTION_BROWSER_SEARCH_ID}
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Search collections…"
            className="h-8 pl-8 text-sm"
            aria-label="Search collections"
          />
        </div>
        {isSuperadmin && (
          <Button
            size="sm"
            className="w-full gap-1.5"
            onClick={() => navigate('/admin/collections/new')}
            data-testid="collections-new-collection"
          >
            <Plus className="h-3.5 w-3.5" />
            New collection
          </Button>
        )}
      </div>

      {error && (
        <div className="m-3 rounded-md border border-destructive/30 bg-destructive/10 p-3 text-sm">
          <p className="font-medium text-destructive">Failed to load</p>
          <p className="mt-1 text-xs text-muted-foreground">{error}</p>
          <Button
            size="sm"
            variant="outline"
            className="mt-2"
            onClick={() => void refreshCollections()}
          >
            Retry
          </Button>
        </div>
      )}

      {loading && collections.length === 0 && !error && (
        <div className="flex flex-1 items-center justify-center p-6">
          <RefreshCw className="h-6 w-6 animate-spin text-muted-foreground" />
        </div>
      )}

      {!loading && !error && collections.length === 0 && (
        <div className="p-4 text-center text-sm text-muted-foreground">
          <Database className="mx-auto mb-2 h-8 w-8 opacity-40" />
          <p>No collections yet</p>
        </div>
      )}

      {!error && collections.length > 0 && filtered.length === 0 && (
        <div className="p-4 text-center text-sm text-muted-foreground">
          No collections match “{search}”
        </div>
      )}

      {filtered.length > 0 && (
        <ScrollArea className="flex-1">
          <nav className="p-2 space-y-0.5" aria-label="Collection list">
            {filtered.map((c) => {
              const active = c.name === collectionName;
              return (
                <Link
                  key={c.id}
                  to={`/admin/collections/${c.name}`}
                  className={cn(
                    'flex flex-col gap-0.5 rounded-md px-2.5 py-2 text-sm transition-colors',
                    'hover:bg-accent hover:text-accent-foreground',
                    active && 'bg-accent text-accent-foreground font-medium',
                  )}
                  aria-current={active ? 'page' : undefined}
                >
                  <span className="flex items-center gap-1.5 truncate">
                    <span className="truncate">{c.name}</span>
                    {c.has_public_access && (
                      <Badge
                        variant="outline"
                        className="shrink-0 text-[10px] px-1 py-0 border-green-500 text-green-600 dark:text-green-400 dark:border-green-700"
                      >
                        Public
                      </Badge>
                    )}
                  </span>
                  <span className="text-xs text-muted-foreground">
                    {c.fields_count} fields · {c.records_count} records
                  </span>
                </Link>
              );
            })}
          </nav>
        </ScrollArea>
      )}
    </aside>
  );
}
