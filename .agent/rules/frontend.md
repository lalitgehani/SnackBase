---
trigger: model_decision
description: Use this rule when working on admin ui for the frontend development
---

# Frontend Development Rules

## Project Structure

- **Root Directory**: `ui/`
- **Source**: `ui/src/`
- **Aliases**: `@/` maps to `ui/src/` (e.g., `import { Button } from "@/components/ui/button"`)

## Technology Stack

- **Framework**: React 19+ with Vite
- **Language**: TypeScript (`.tsx`, `.ts`)
- **Styling**: Tailwind CSS v4 (using `@tailwindcss/vite` plugin)
- **UI Components**: ShadCN UI (Radix UI + Tailwind)
- **Icons**: `lucide-react`
- **Routing**: `react-router` (v6+)
- **State Management**:
  - **Global/Client State**: `zustand`
  - **Server State/Data Fetching**: `@tanstack/react-query`
- **Forms**: `react-hook-form` + `zod`

## Coding Conventions

### Components

- **Location**: `ui/src/components/`
- **Naming**: PascalCase (e.g., `UserProfile.tsx`)
- **Exports**: Default exports preferred for Pages (`export default function...`), Named exports for reusable components (`export function...`).
- **Props**: Define interfaces for props.

### UI & Styling

- **ShadCN**: Use existing components in `ui/src/components/ui/`.
- **Tailwind**: Use utility classes.
- **Class Merging**: Always use `cn()` when accepting `className` props.
  ```tsx
  import { cn } from "@/lib/utils";
  <div className={cn("bg-red-500", className)} />;
  ```

### Data Fetching

- Use **TanStack Query** hooks for API interactions.
- Create API wrappers in `ui/src/lib/api.ts` or `ui/src/services/`.

### State

- Use **Zustand** for complex global state.
- Use local `useState` for component-level state.

### File Management

- **New Files**: Always inside `ui/`.
