import {
  useEffect,
  useRef,
  useState,
  type CSSProperties,
  type MutableRefObject,
} from 'react';
import {
  EditorState,
  Compartment,
  type Extension,
} from '@codemirror/state';
import {
  EditorView,
  keymap,
  lineNumbers,
  highlightActiveLine,
  highlightActiveLineGutter,
  drawSelection,
  dropCursor,
  rectangularSelection,
  crosshairCursor,
} from '@codemirror/view';
import {
  defaultKeymap,
  history,
  historyKeymap,
  indentWithTab,
} from '@codemirror/commands';
import {
  foldGutter,
  foldKeymap,
  bracketMatching,
  indentOnInput,
  indentUnit,
} from '@codemirror/language';
import {
  highlightSelectionMatches,
  searchKeymap,
} from '@codemirror/search';
import {
  closeBrackets,
  closeBracketsKeymap,
  autocompletion,
  completionKeymap,
} from '@codemirror/autocomplete';
import { languageExtensionFor, resolveLanguageId } from './language';
import {
  snackbaseEditorTheme,
  snackbaseSyntaxHighlighting,
} from './theme';
import type { CodeEditorProps, EditorLanguageContext } from './types';

function isDocumentDark(): boolean {
  return (
    typeof document !== 'undefined' &&
    document.documentElement.classList.contains('dark')
  );
}

/** Observe `html.dark` so CodeMirror's light/dark theme flag tracks ThemeProvider. */
function useDocumentDark(): boolean {
  const [dark, setDark] = useState(isDocumentDark);

  useEffect(() => {
    const root = document.documentElement;
    const sync = () => setDark(root.classList.contains('dark'));
    sync();
    const observer = new MutationObserver(sync);
    observer.observe(root, { attributes: true, attributeFilter: ['class'] });
    return () => observer.disconnect();
  }, []);

  return dark;
}

function buildBaseExtensions(): Extension[] {
  return [
    lineNumbers(),
    highlightActiveLineGutter(),
    highlightActiveLine(),
    drawSelection(),
    dropCursor(),
    rectangularSelection(),
    crosshairCursor(),
    history(),
    foldGutter(),
    indentOnInput(),
    bracketMatching(),
    closeBrackets(),
    autocompletion(),
    highlightSelectionMatches(),
    indentUnit.of('    '),
    EditorState.allowMultipleSelections.of(true),
    // Line wrapping intentionally omitted — long lines scroll horizontally.
    keymap.of([
      indentWithTab,
      ...closeBracketsKeymap,
      ...defaultKeymap,
      ...historyKeymap,
      ...foldKeymap,
      ...searchKeymap,
      ...completionKeymap,
    ]),
    EditorView.contentAttributes.of({ spellcheck: 'false' }),
    snackbaseSyntaxHighlighting(),
  ];
}

function createEditorState(options: {
  doc: string;
  readOnly: boolean;
  dark: boolean;
  language: EditorLanguageContext | undefined;
  path: string;
  languageCompartment: Compartment;
  readOnlyCompartment: Compartment;
  themeCompartment: Compartment;
  onChangeRef: MutableRefObject<((value: string) => void) | undefined>;
}): EditorState {
  const langCtx: EditorLanguageContext = {
    ...options.language,
    path: options.language?.path ?? options.path,
    languageId:
      options.language?.languageId ??
      resolveLanguageId(options.language?.path ?? options.path),
  };

  return EditorState.create({
    doc: options.doc,
    extensions: [
      ...buildBaseExtensions(),
      options.themeCompartment.of(snackbaseEditorTheme(options.dark)),
      options.languageCompartment.of(languageExtensionFor(langCtx)),
      options.readOnlyCompartment.of(EditorState.readOnly.of(options.readOnly)),
      EditorView.updateListener.of((update) => {
        if (update.docChanged) {
          options.onChangeRef.current?.(update.state.doc.toString());
        }
      }),
    ],
  });
}

/**
 * SnackBase CodeMirror 6 adapter.
 *
 * Maintains one EditorState per `path` so switching files preserves cursor,
 * selection, scroll, and undo history. Does not expose CodeMirror types to
 * page-level business logic.
 */
export default function CodeEditor({
  path,
  value,
  onChange,
  language,
  readOnly = false,
  height = 420,
  className,
  autoFocus = false,
  'aria-label': ariaLabel,
  openPaths,
}: CodeEditorProps) {
  const dark = useDocumentDark();
  const hostRef = useRef<HTMLDivElement | null>(null);
  const viewRef = useRef<EditorView | null>(null);
  const statesRef = useRef<Map<string, EditorState>>(new Map());
  const activePathRef = useRef(path);
  const languageCompartment = useRef(new Compartment()).current;
  const readOnlyCompartment = useRef(new Compartment()).current;
  const themeCompartment = useRef(new Compartment()).current;
  const onChangeRef = useRef(onChange);
  onChangeRef.current = onChange;
  const languageRef = useRef(language);
  languageRef.current = language;
  const readOnlyRef = useRef(readOnly);
  readOnlyRef.current = readOnly;
  const darkRef = useRef(dark);
  darkRef.current = dark;
  const valueRef = useRef(value);
  valueRef.current = value;

  const heightStyle: CSSProperties = {
    height: typeof height === 'number' ? `${height}px` : height,
    minHeight: typeof height === 'number' ? `${Math.max(height, 240)}px` : height,
    minWidth: 0,
    overflow: 'hidden',
  };

  // Mount once; unmount disposes the view and clears cached states.
  useEffect(() => {
    if (!hostRef.current || viewRef.current) return;

    const state = createEditorState({
      doc: valueRef.current,
      readOnly: readOnlyRef.current,
      dark: darkRef.current,
      language: languageRef.current,
      path,
      languageCompartment,
      readOnlyCompartment,
      themeCompartment,
      onChangeRef,
    });
    statesRef.current.set(path, state);
    activePathRef.current = path;

    const view = new EditorView({
      state,
      parent: hostRef.current,
    });
    viewRef.current = view;

    if (autoFocus) {
      view.focus();
    }

    const states = statesRef.current;
    return () => {
      if (viewRef.current) {
        states.set(activePathRef.current, viewRef.current.state);
        viewRef.current.destroy();
        viewRef.current = null;
      }
      states.clear();
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps -- mount once
  }, []);

  // Switch file path: cache old state, restore or create new
  useEffect(() => {
    const view = viewRef.current;
    if (!view) return;

    const prevPath = activePathRef.current;
    if (prevPath === path) return;

    statesRef.current.set(prevPath, view.state);

    let next = statesRef.current.get(path);
    if (!next || next.doc.toString() !== valueRef.current) {
      next = createEditorState({
        doc: valueRef.current,
        readOnly: readOnlyRef.current,
        dark: darkRef.current,
        language: languageRef.current,
        path,
        languageCompartment,
        readOnlyCompartment,
        themeCompartment,
        onChangeRef,
      });
      statesRef.current.set(path, next);
    }

    view.setState(next);
    view.dispatch({
      effects: themeCompartment.reconfigure(snackbaseEditorTheme(darkRef.current)),
    });
    activePathRef.current = path;
    statesRef.current.set(path, view.state);
  }, [path, languageCompartment, readOnlyCompartment, themeCompartment]);

  // Drop cached states for closed files
  useEffect(() => {
    if (!openPaths) return;
    const keep = new Set(openPaths);
    for (const key of [...statesRef.current.keys()]) {
      if (!keep.has(key)) statesRef.current.delete(key);
    }
  }, [openPaths]);

  // Sync external value changes for the active path
  useEffect(() => {
    const view = viewRef.current;
    if (!view) return;
    if (activePathRef.current !== path) return;
    const current = view.state.doc.toString();
    if (current === value) return;

    view.dispatch({
      changes: { from: 0, to: current.length, insert: value },
    });
    statesRef.current.set(path, view.state);
  }, [value, path]);

  // Update language / readOnly without recreating history
  useEffect(() => {
    const view = viewRef.current;
    if (!view) return;
    const langCtx: EditorLanguageContext = {
      ...language,
      path: language?.path ?? path,
    };
    view.dispatch({
      effects: [
        languageCompartment.reconfigure(languageExtensionFor(langCtx)),
        readOnlyCompartment.reconfigure(EditorState.readOnly.of(readOnly)),
      ],
    });
    statesRef.current.set(activePathRef.current, view.state);
  }, [language, path, readOnly, languageCompartment, readOnlyCompartment]);

  // Flip CodeMirror cm-light / cm-dark when ThemeProvider toggles html.dark
  useEffect(() => {
    const view = viewRef.current;
    if (!view) return;
    view.dispatch({
      effects: themeCompartment.reconfigure(snackbaseEditorTheme(dark)),
    });
    statesRef.current.set(activePathRef.current, view.state);
  }, [dark, themeCompartment]);

  return (
    <div
      ref={hostRef}
      className={className}
      style={heightStyle}
      data-testid="code-editor"
      data-path={path}
      data-readonly={readOnly ? 'true' : 'false'}
      data-theme={dark ? 'dark' : 'light'}
      aria-label={ariaLabel ?? `Code editor for ${path}`}
      aria-readonly={readOnly || undefined}
    />
  );
}
