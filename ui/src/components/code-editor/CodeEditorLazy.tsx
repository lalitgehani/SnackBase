import { lazy, Suspense, type ComponentProps } from 'react';
import type CodeEditorType from './CodeEditor';

const LazyCodeEditor = lazy(() => import('./CodeEditor'));

export type LazyCodeEditorProps = ComponentProps<typeof CodeEditorType>;

/**
 * Lazy-loaded CodeMirror editor. Keeps editor packages out of the initial
 * Admin UI bundle until a Function (or future SQL) page renders it.
 */
export default function CodeEditorLazy(props: LazyCodeEditorProps) {
  return (
    <Suspense
      fallback={
        <div
          className="flex items-center justify-center bg-muted/30 text-sm text-muted-foreground min-h-[420px]"
          data-testid="code-editor-loading"
        >
          Loading editor…
        </div>
      }
    >
      <LazyCodeEditor {...props} />
    </Suspense>
  );
}
