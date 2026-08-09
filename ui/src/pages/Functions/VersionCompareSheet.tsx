import { useMemo, useState } from 'react';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import {
  Sheet,
  SheetContent,
  SheetDescription,
  SheetHeader,
  SheetTitle,
} from '@/components/ui/sheet';
import { cn } from '@/lib/utils';
import type { FunctionBody } from '@/services/functions.service';
import {
  compareFunctionVersions,
  firstInterestingFilePath,
  parseUnifiedDiffLines,
  unifiedFileDiff,
  type ComparedFile,
  type FileDiffStatus,
  type VersionCompareResult,
} from './versionCompare';

export interface VersionCompareSheetProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  left: FunctionBody | null;
  right: FunctionBody | null;
  activeVersionId: string | null;
}

function statusBadgeVariant(
  status: FileDiffStatus,
): 'default' | 'secondary' | 'destructive' | 'outline' {
  switch (status) {
    case 'added':
      return 'default';
    case 'removed':
      return 'destructive';
    case 'changed':
      return 'secondary';
    default:
      return 'outline';
  }
}

function DiffPane({ file }: { file: ComparedFile | undefined }) {
  const lines = useMemo(() => {
    if (!file) return [];
    if (file.status === 'unchanged') {
      const content = file.rightContent ?? file.leftContent ?? '';
      return content.split('\n').map((text) => ({
        type: 'context' as const,
        text: text.length ? ` ${text}` : ' ',
      }));
    }
    return parseUnifiedDiffLines(unifiedFileDiff(file)).filter(
      (l) => l.type !== 'meta',
    );
  }, [file]);

  if (!file) {
    return (
      <p className="text-sm text-muted-foreground p-4">Select a file to view the diff.</p>
    );
  }

  return (
    <pre
      className="text-xs font-mono overflow-auto h-full min-h-0 p-3 leading-5"
      data-testid="version-compare-diff"
      aria-label={`Diff for ${file.path}`}
    >
      {lines.map((line, i) => (
        <div
          key={`${i}-${line.type}-${line.text.slice(0, 24)}`}
          className={cn(
            'whitespace-pre-wrap break-all px-1 -mx-1 rounded-sm',
            line.type === 'added' &&
              'bg-emerald-500/15 text-emerald-800 dark:text-emerald-300',
            line.type === 'removed' &&
              'bg-destructive/15 text-destructive',
            line.type === 'hunk' && 'text-muted-foreground bg-muted/50',
            line.type === 'header' && 'text-muted-foreground',
          )}
        >
          {line.text || ' '}
        </div>
      ))}
    </pre>
  );
}

export default function VersionCompareSheet({
  open,
  onOpenChange,
  left,
  right,
  activeVersionId,
}: VersionCompareSheetProps) {
  const comparison: VersionCompareResult | null = useMemo(() => {
    if (!left || !right) return null;
    return compareFunctionVersions(left, right);
  }, [left, right]);

  const [selectedPath, setSelectedPath] = useState<string | null>(null);
  const [showUnchanged, setShowUnchanged] = useState(false);
  const [lastComparison, setLastComparison] =
    useState<VersionCompareResult | null>(null);

  // Reset the selection during render when the compared pair changes, rather
  // than in an effect — an effect would render one frame with the previous
  // file selected against the new comparison.
  if (comparison !== lastComparison) {
    setLastComparison(comparison);
    setSelectedPath(
      comparison ? firstInterestingFilePath(comparison.files) : null
    );
    setShowUnchanged(false);
  }

  const selectedFile = comparison?.files.find((f) => f.path === selectedPath);
  const visibleFiles =
    comparison?.files.filter((f) => showUnchanged || f.status !== 'unchanged') ??
    [];
  const unchangedCount =
    comparison?.files.filter((f) => f.status === 'unchanged').length ?? 0;

  return (
    <Sheet open={open} onOpenChange={onOpenChange}>
      <SheetContent
        side="right"
        className="w-full sm:max-w-3xl p-0 flex flex-col gap-0"
        data-testid="version-compare-sheet"
      >
        <SheetHeader className="border-b p-4 pr-12">
          <SheetTitle>
            {comparison ? (
              <>
                v{comparison.left.version}
                {activeVersionId === comparison.left.version_id && (
                  <Badge className="ml-2 align-middle" variant="secondary">
                    active
                  </Badge>
                )}
                <span className="mx-2 text-muted-foreground font-normal">→</span>
                v{comparison.right.version}
                {activeVersionId === comparison.right.version_id && (
                  <Badge className="ml-2 align-middle" variant="secondary">
                    active
                  </Badge>
                )}
              </>
            ) : (
              'Compare versions'
            )}
          </SheetTitle>
          <SheetDescription>
            {comparison
              ? `Comparing source, entrypoint, and dependencies (${comparison.left.sha256.slice(0, 12)} → ${comparison.right.sha256.slice(0, 12)})`
              : 'Load two versions to compare'}
          </SheetDescription>
        </SheetHeader>

        {comparison && (
          <div className="flex flex-col min-h-0 flex-1 overflow-hidden">
            <div className="border-b px-4 py-3 space-y-2 text-sm">
              {comparison.entrypointChanged ? (
                <p>
                  <span className="text-muted-foreground">Entrypoint:</span>{' '}
                  <code className="text-xs">{comparison.left.entrypoint}</code>
                  <span className="mx-1 text-muted-foreground">→</span>
                  <code className="text-xs">{comparison.right.entrypoint}</code>
                </p>
              ) : (
                <p className="text-muted-foreground">
                  Entrypoint unchanged (<code className="text-xs">{comparison.left.entrypoint}</code>)
                </p>
              )}
              {(comparison.depsAdded.length > 0 || comparison.depsRemoved.length > 0) ? (
                <div className="flex flex-wrap gap-2">
                  {comparison.depsAdded.map((d) => (
                    <Badge key={`+${d}`} variant="default" className="font-mono text-[10px]">
                      + {d}
                    </Badge>
                  ))}
                  {comparison.depsRemoved.map((d) => (
                    <Badge key={`-${d}`} variant="destructive" className="font-mono text-[10px]">
                      − {d}
                    </Badge>
                  ))}
                </div>
              ) : (
                <p className="text-muted-foreground">Dependencies unchanged</p>
              )}
            </div>

            <div className="flex min-h-0 flex-1 overflow-hidden">
              <aside className="w-48 shrink-0 border-r overflow-auto">
                <div className="p-2 space-y-1">
                  {visibleFiles.map((f) => (
                    <button
                      key={f.path}
                      type="button"
                      className={cn(
                        'w-full text-left rounded-md px-2 py-1.5 text-xs hover:bg-muted/80',
                        selectedPath === f.path && 'bg-muted',
                      )}
                      onClick={() => setSelectedPath(f.path)}
                      aria-label={`Show diff for ${f.path}`}
                      aria-current={selectedPath === f.path ? 'true' : undefined}
                    >
                      <div className="font-mono truncate">{f.path}</div>
                      <Badge
                        variant={statusBadgeVariant(f.status)}
                        className="mt-1 text-[10px] capitalize"
                      >
                        {f.status}
                      </Badge>
                    </button>
                  ))}
                  {unchangedCount > 0 && (
                    <Button
                      type="button"
                      variant="ghost"
                      size="sm"
                      className="w-full h-7 text-xs text-muted-foreground"
                      onClick={() => setShowUnchanged((v) => !v)}
                    >
                      {showUnchanged
                        ? 'Hide unchanged'
                        : `Show ${unchangedCount} unchanged`}
                    </Button>
                  )}
                  {visibleFiles.length === 0 && (
                    <p className="text-xs text-muted-foreground px-2 py-1">No file changes</p>
                  )}
                </div>
              </aside>
              <div className="min-w-0 flex-1 overflow-hidden bg-muted/20">
                <DiffPane file={selectedFile} />
              </div>
            </div>
          </div>
        )}
      </SheetContent>
    </Sheet>
  );
}
