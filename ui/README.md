# SnackBase Admin UI

React admin console for [SnackBase](../README.md) — the open-source, self-hosted Backend-as-a-Service.

## Stack

| Technology | Purpose |
|------------|---------|
| React 19 + TypeScript | UI |
| Vite 7 | Dev server and production build |
| TailwindCSS 4 + ShadCN/Radix | Design system |
| TanStack Query | Server state |
| Zustand | Client auth presentation state |
| @snackbase/sdk | Instance API client (collections, records, auth, automation) |
| next-themes | Light / Dark / System appearance |
| Vitest + Testing Library | Unit tests |
| Playwright | E2E tests |

## Quick start

```bash
# From repo root — backend
uv run python -m snackbase serve --reload

# From ui/
npm install
npm run dev        # http://localhost:5173
```

Proxy: Vite forwards `/api` to `http://localhost:8000` (see `vite.config.ts`).

## SDK dependency

The Studio is an SDK consumer. The instance client comes from `@snackbase/sdk`, resolved from
the npm registry like any other dependency, and is provided by `InstanceClientProvider` in
`src/lib/snackbase/`.

To develop the Studio against an unpublished SDK change, link a local checkout of
[`SnackBase-sdk-js`](https://github.com/lalitgehani/SnackBase-sdk-js) instead of editing
`package.json`:

```bash
# From SnackBase-sdk-js/, after building the packages
npm link ./packages/sdk ./packages/react

# From SnackBase/ui/
npm link @snackbase/sdk @snackbase/react
```

`npm unlink @snackbase/sdk @snackbase/react && npm install` restores the published versions.
Keep the link out of commits — `package.json` must always name a registry version so the
repository builds from a clean clone.

- **Self-host**: tokens persist under `snackbase-auth` in localStorage; `loadConfig()` resolves `apiBaseUrl` from runtime `/config.js` or `VITE_*` env.
- **Platform** (future): proxied `baseUrl` and external `getAccessToken`; instance storage is in-memory only.

Service modules expose `createXxxService(client)`, `useXxxService()`, and bound exports for legacy call sites. Do not import `axios` or add a module-level HTTP client.

## Scripts

| Command | Description |
|---------|-------------|
| `npm run dev` | Vite dev server |
| `npm run build` | Typecheck + production build |
| `npm run lint` | ESLint |
| `npm run test` | Vitest unit suite |
| `npm run test:coverage` | Unit tests with coverage |
| `npm run test:e2e` | Playwright E2E (backend required for most suites) |
| `npm run preview` | Preview production build |

## Dark / light mode

Theme preference is **client-only** (no backend API). Users choose **Light**, **Dark**, or **System**.

### How it works

1. **`ThemeProvider`** (`src/components/theme-provider.tsx`) wraps the app in `src/main.tsx` via `next-themes`.
2. **Class strategy**: `attribute="class"` toggles `class="dark"` on `<html>`, matching Tailwind’s `@custom-variant dark (&:is(.dark *))` in `src/App.css`.
3. **Persistence**: `localStorage` key **`snackbase.theme`** (`defaultTheme="system"`, `enableSystem`).
4. **FOUC prevention**: inline boot script in `index.html` reads the same key before React paints and applies/removes `dark` on `document.documentElement`.
5. **Palette source of truth**: light tokens on `:root` and dark tokens under `.dark` in `src/App.css` (oklch CSS variables). Do not invent ad-hoc hex palettes for chrome.

### Where toggles live

| Control | Component | Placement |
|---------|-----------|-----------|
| Header icon menu | `ModeToggle` / `ThemeToggleButton` | `AdminLayout` header |
| Account submenu | `ThemeMenuItems` | `AppSidebar` user dropdown |
| Login | `ModeToggle` | `LoginPage` |

Accept-invitation page theme control is intentionally deferred; theme still applies via the root provider and FOUC script.

### Contributor guidance

- Prefer **semantic tokens**: `bg-background`, `text-foreground`, `bg-card`, `border-border`, `text-muted-foreground`, etc.
- For status/alert colors that need both themes, pair utilities with **`dark:`** variants (or use design-system tokens that already flip under `.dark`).
- **Do not** wrap oklch tokens in `hsl(var(--…))` — tokens are raw `oklch(...)` values (`var(--background)` is correct).
- Charts: use helpers in `src/components/charts/theme.ts`; `ChartContainer` remounts on theme flip so Recharts rebinds CSS variables.
- **Intentional non-theme surfaces** (leave as-is):
  - Email HTML preview iframe canvas (`EmailTemplateEditDialog`) — realistic light email canvas
  - Macro SQL / terminal blocks (`MacroDetailDialog`) — always-dark IDE contrast
  - Modal overlays (`dialog` / `sheet` / `alert-dialog`) — always `bg-black/50`

### Tests

- Unit: `src/components/__tests__/theme-provider.test.tsx`, `src/components/__tests__/mode-toggle.test.tsx`
- E2E: `e2e/tests/theme.test.ts` (login-page toggle, reload persistence, system preference, a11y smoke)

### Accessibility checklist (theme controls)

- [x] Trigger has accessible name (`aria-label="Toggle theme"` / menu item “Theme”)
- [x] Options labeled Light / Dark / System (`menuitemradio`)
- [x] Selected state via radio `aria-checked` + indicator (not color alone)
- [x] Keyboard: focus trigger, Enter/Space opens menu, options selectable
- [x] Focus styles from ShadCN/Radix in both themes

### Manual QA (optional)

1. Hard reload with `snackbase.theme=dark` — no light flash.
2. Switch Light / Dark / System from header and sidebar; preference survives reload.
3. Clear `localStorage` key → default System follows OS.
4. Spot-check primary sidebar destinations in dark mode (dashboard, collections, users, roles, macros, migrations, audit logs, configuration).

Full product requirements: [`PRD_DARK_LIGHT_MODE.md`](../PRD_DARK_LIGHT_MODE.md).

## Project layout

See [`docs/frontend.md`](../docs/frontend.md) for architecture, services, routing, and patterns.

```
ui/src/
  main.tsx                 # ThemeProvider + QueryClient + Router
  App.tsx                  # Routes
  App.css                  # Design tokens (light/dark)
  components/
    theme-provider.tsx
    mode-toggle.tsx
    ui/                    # ShadCN (install via CLI, do not hand-edit)
  layouts/AdminLayout.tsx
  pages/
  services/
  stores/
e2e/                       # Playwright
```

## ShadCN

Use existing components under `src/components/ui/`. Install new ones only via:

```bash
npx shadcn@latest add <component>
```

Never hand-create ShadCN component files.

## Further reading

- [Frontend developer guide](../docs/frontend.md)
- [E2E testing](./e2e/README.md)
- [Root project docs](../docs/README.md)
