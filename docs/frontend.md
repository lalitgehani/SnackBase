# Frontend Developer Guide

This guide covers the SnackBase React admin UI architecture, development patterns, and how to build and extend the frontend.

---

## Table of Contents

- [Tech Stack](#tech-stack)
- [Project Structure](#project-structure)
- [Architecture Overview](#architecture-overview)
- [State Management](#state-management)
- [API Service Layer](#api-service-layer)
- [Authentication Flow](#authentication-flow)
- [Components & Patterns](#components--patterns)
- [Routing](#routing)
- [Adding New Pages](#adding-new-pages)
- [Styling](#styling)
- [Development Workflow](#development-workflow)
- [Features](#features)

---

## Tech Stack

The SnackBase admin UI is built with modern, production-ready technologies:

| Technology | Version | Purpose |
|------------|---------|---------|
| **React** | 19.2.0 | UI framework |
| **TypeScript** | 5.9.3 | Type safety |
| **Vite** | 7.2.4 | Build tool and dev server |
| **React Router** | 7.11.0 | Client-side routing |
| **TailwindCSS** | 4.1.18 | Utility-first styling with @tailwindcss/vite plugin |
| **Radix UI** | Latest | Accessible component primitives |
| **ShadCN** | Latest (new-york style) | Pre-built component library |
| **TanStack Query** | 5.90.12 | Server state management |
| **Zustand** | 5.0.9 | Client state management |
| **Zod** | 4.2.1 | Schema validation |
| **Axios** | 1.13.2 | HTTP client |
| **React Hook Form** | 7.69.0 | Form state management |
| **date-fns** | 4.1.0 | Date manipulation |
| **Lucide React** | 0.562.0 | Icon library |

---

## Project Structure

```
ui/
├── src/
│   ├── main.tsx                 # Application entry point
│   ├── App.tsx                  # Root component with Router
│   ├── App.css                  # Global styles with TailwindCSS @theme syntax
│   │
│   ├── pages/                   # Page components (15 pages, ~4,385 lines)
│   │   ├── LoginPage.tsx
│   │   ├── DashboardPage.tsx
│   │   ├── AccountsPage.tsx
│   │   ├── UsersPage.tsx
│   │   ├── GroupsPage.tsx
│   │   ├── CollectionsPage.tsx
│   │   ├── RecordsPage.tsx
│   │   ├── RolesPage.tsx
│   │   ├── AuditLogsPage.tsx
│   │   ├── MigrationsPage.tsx
│   │   ├── MacrosPage.tsx
│   │   ├── ConfigurationDashboardPage.tsx
│   │   ├── AccountProvidersTab.tsx
│   │   ├── SystemProvidersTab.tsx
│   │   └── EmailTemplatesTab.tsx
│   │
│   ├── components/              # Reusable components (83 components, ~12,419 lines)
│   │   ├── ui/                  # ShadCN components (30 components - DO NOT EDIT)
│   │   ├── accounts/            # Account-related components
│   │   ├── audit-logs/          # Audit log components
│   │   ├── collections/         # Collection builder components
│   │   ├── common/              # Shared components (ProviderLogo, ConfigurationForm, etc.)
│   │   ├── groups/              # Group components
│   │   ├── macros/              # Macro management components
│   │   ├── migrations/          # Migration components
│   │   ├── records/             # Record CRUD components
│   │   ├── roles/               # Role management components
│   │   ├── users/               # User management components
│   │   ├── AppSidebar.tsx       # Main navigation sidebar
│   │   └── ProtectedRoute.tsx   # Auth wrapper component
│   │
│   ├── layouts/                 # Layout components
│   │   └── AdminLayout.tsx      # Main admin layout with sidebar
│   │
│   ├── services/                # API service layer (15 services)
│   │   ├── api.ts               # Axios configuration with interceptors
│   │   ├── auth.service.ts      # Authentication API
│   │   ├── accounts.service.ts  # Accounts API
│   │   ├── users.service.ts     # Users API
│   │   ├── collections.service.ts
│   │   ├── records.service.ts
│   │   ├── roles.service.ts
│   │   ├── groups.service.ts
│   │   ├── dashboard.service.ts
│   │   ├── audit.service.ts
│   │   ├── migrations.service.ts
│   │   ├── macros.service.ts
│   │   ├── email.service.ts     # Email template management
│   │   ├── admin.service.ts     # Configuration/Providers API
│   │   └── files.service.ts     # File upload API
│   │
│   ├── stores/                  # Zustand state stores
│   │   └── auth.store.ts        # Authentication state with persist middleware
│   │
│   ├── hooks/                   # Custom React hooks
│   │   ├── use-mobile.ts        # Mobile detection
│   │   └── use-toast.ts         # Toast notifications
│   │
│   ├── lib/                     # Utilities and helpers
│   │   ├── api.ts               # Axios client configuration
│   │   ├── utils.ts             # Utility functions (cn())
│   │   └── form-helpers.ts      # Form helper functions
│   │
│   └── types/                   # TypeScript type definitions
│       ├── auth.types.ts        # Authentication types
│       ├── macro.ts             # Macro types
│       ├── migrations.ts        # Migration types
│       └── records.types.ts     # Record types
│
├── index.html                   # HTML entry point
├── package.json                 # Dependencies and scripts
├── tsconfig.json                # TypeScript configuration
├── vite.config.ts               # Vite build configuration
├── components.json              # ShadCN component configuration
├── .env                         # Environment variables (VITE_API_BASE_URL)
└── .env.example                 # Environment variable template
```

---

## Architecture Overview

The frontend follows a **layered architecture** with clear separation of concerns:

```
┌─────────────────────────────────────────────────────────┐
│                     Pages Layer                         │
│  (Route handlers, orchestrate components and data)      │
└────────────────────┬────────────────────────────────────┘
                     │
┌────────────────────▼────────────────────────────────────┐
│                   Components Layer                      │
│        (Reusable UI components, ShadCN, Custom)         │
└────────────────────┬────────────────────────────────────┘
                     │
┌────────────────────▼────────────────────────────────────┐
│              Business Logic Layer                       │
│  (Zustand stores, custom hooks, form validation)        │
└────────────────────┬────────────────────────────────────┘
                     │
┌────────────────────▼────────────────────────────────────┐
│                 Data Layer                              │
│         (Services with TanStack Query)                  │
└────────────────────┬────────────────────────────────────┘
                     │
┌────────────────────▼────────────────────────────────────┐
│                   Axios API                             │
│          (HTTP client with interceptors)                │
└─────────────────────────────────────────────────────────┘
```

### Key Principles

1. **Pages orchestrate, Components render**
   - Pages handle routing, data fetching, and layout
   - Components focus on presentation and user interaction

2. **Services abstract API calls**
   - All API calls go through service functions
   - Pages use TanStack Query to manage server state

3. **Global state in Zustand stores**
   - Authentication state is global with persist middleware
   - Use Zustand for cross-component state

4. **Local state with React hooks**
   - Use `useState` for component-specific state
   - Use `useForm` (from react-hook-form) for form state

---

## State Management

SnackBase uses a hybrid state management approach:

### Global State: Zustand

Located in `src/stores/auth.store.ts`:

```typescript
interface AuthState {
  // State
  user: UserInfo | null;
  account: AccountInfo | null;
  token: string | null;
  refreshToken: string | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  error: string | null;

  // Actions
  login: (email: string, password: string) => Promise<void>;
  logout: () => void;
  clearError: () => void;
  restoreSession: () => Promise<void>;
}

export const useAuthStore = create<AuthState>()(
  persist(
    (set, get) => ({
      // Initial state
      user: null,
      account: null,
      token: null,
      refreshToken: null,
      isAuthenticated: false,
      isLoading: false,
      error: null,

      // Actions...
    }),
    {
      name: 'auth-storage',
      partialize: (state) => ({
        user: state.user,
        account: state.account,
        token: state.token,
        refreshToken: state.refreshToken,
        isAuthenticated: state.isAuthenticated,
      }),
    }
  )
);
```

**Key Features:**
- Token stored in localStorage with key `auth-storage`
- Persist middleware for session persistence across page reloads
- `restoreSession()` verifies token validity on app load
- Automatic logout on 401 responses

**When to use Zustand:**
- Authentication state
- User preferences
- Global application settings
- Cross-route data that doesn't come from the API

### Server State: TanStack Query

All data from the API is managed by TanStack Query:

```typescript
// In a page component
const { data: collections, isLoading, error } = useQuery({
  queryKey: ['collections'],
  queryFn: collectionsService.getCollections,
});
```

**Key Features:**
- Automatic caching and revalidation
- Background refetching
- Optimistic updates
- Loading and error states built-in

### Local State: React Hooks

Component-specific state uses standard React hooks:

```typescript
const [isOpen, setIsOpen] = useState(false);
const [selectedId, setSelectedId] = useState<string | null>(null);
```

---

## API Service Layer

The service layer provides a clean abstraction over API calls. All services are in `src/services/`.

### Service Pattern

Each service follows a consistent pattern:

```typescript
// src/services/collections.service.ts
import { apiClient } from '@/lib/api';

export interface Collection {
  id: string;
  name: string;
  table_name: string;
  schema: FieldDefinition[];
  created_at: string;
  updated_at: string;
}

export const collectionsService = {
  // Get all collections with pagination
  getCollections: async (params?: GetCollectionsParams): Promise<CollectionListResponse> => {
    const response = await apiClient.get<CollectionListResponse>('/collections', { params });
    return response.data;
  },

  // Get single collection
  getCollectionById: async (collectionId: string): Promise<Collection> => {
    const response = await apiClient.get<Collection>(`/collections/${collectionId}`);
    return response.data;
  },

  // Create collection
  createCollection: async (data: CreateCollectionData): Promise<Collection> => {
    const response = await apiClient.post<Collection>('/collections', data);
    return response.data;
  },

  // Update collection
  updateCollection: async (
    collectionId: string,
    data: UpdateCollectionData
  ): Promise<Collection> => {
    const response = await apiClient.put<Collection>(`/collections/${collectionId}`, data);
    return response.data;
  },

  // Delete collection
  deleteCollection: async (collectionId: string): Promise<void> => {
    await apiClient.delete(`/collections/${collectionId}`);
  },
};
```

### Axios Configuration

The `lib/api.ts` file configures the Axios instance:

```typescript
// src/lib/api.ts
import axios from 'axios';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || '/api/v1';

export const apiClient = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Request interceptor - add auth token
apiClient.interceptors.request.use(
  (config) => {
    const authState = localStorage.getItem('auth-storage');
    if (authState) {
      const parsedState = JSON.parse(authState);
      const token = parsedState?.state?.token;
      if (token) {
        config.headers.Authorization = `Bearer ${token}`;
      }
    }
    return config;
  },
  (error) => Promise.reject(error)
);

// Response interceptor - handle token refresh
apiClient.interceptors.response.use(
  (response) => response,
  async (error) => {
    if (error.response?.status === 401 && !error.config._retry) {
      error.config._retry = true;
      // Attempt token refresh...
      // If refresh fails, redirect to login
    }
    return Promise.reject(error);
  }
);
```

**Key Features:**
- Automatic token injection from localStorage
- Token refresh on 401 responses
- Redirect to login on refresh failure
- Error handling with `handleApiError()` utility

---

## Authentication Flow

The authentication system handles login, token storage, and automatic token refresh.

### Login Flow

```
┌──────────────┐
│ User enters  │
│ credentials  │
└──────┬───────┘
       │
       ▼
┌──────────────────────┐
│ POST /auth/login     │
│ (auth.service.ts)    │
└──────┬───────────────┘
       │
       ▼
┌──────────────────────┐
│ Store in Zustand     │
│ store with persist   │
│ middleware           │
└──────┬───────────────┘
       │
       ▼
┌──────────────────────┐
│ Redirect to /admin   │
│ /dashboard           │
└──────────────────────┘
```

### Protected Routes

The `ProtectedRoute` component wraps routes that require authentication:

```typescript
// src/components/ProtectedRoute.tsx
import { Navigate } from 'react-router';
import { useAuthStore } from '@/stores/auth.store';

export default function ProtectedRoute({ children }: ProtectedRouteProps) {
  const { isAuthenticated, isLoading, restoreSession } = useAuthStore();

  useEffect(() => {
    restoreSession();
  }, [restoreSession]);

  if (isLoading) {
    return <div>Loading...</div>;
  }

  if (!isAuthenticated) {
    return <Navigate to="/admin/login" replace />;
  }

  return <>{children}</>;
}
```

### Usage in App.tsx

All admin routes are under the `/admin` prefix and wrapped with `ProtectedRoute`:

```typescript
// src/App.tsx
<Routes>
  {/* Redirect root to admin */}
  <Route path="/" element={<Navigate to="/admin/dashboard" replace />} />

  {/* Public routes */}
  <Route path="/admin/login" element={<LoginPage />} />

  {/* Protected admin routes */}
  <Route
    path="/admin"
    element={
      <ProtectedRoute>
        <AdminLayout />
      </ProtectedRoute>
    }
  >
    <Route index element={<Navigate to="/admin/dashboard" replace />} />
    <Route path="dashboard" element={<DashboardPage />} />
    <Route path="accounts" element={<AccountsPage />} />
    {/* ... more routes */}
  </Route>
</Routes>
```

---

## Components & Patterns

### ShadCN Components

ShadCN provides pre-built, accessible components. **Never edit ShadCN components directly** in `src/components/ui/`.

To add new ShadCN components:

```bash
cd ui
npx shadcn@latest add button
npx shadcn@latest add dialog
npx shadcn@latest add table
```

**Available ShadCN Components (30):**
- alert, alert-dialog, avatar, badge, button, card, checkbox, command, dialog, dropdown-menu, field, input, label, pagination, popover, scroll-area, select, separator, sidebar, sheet, skeleton, switch, table, tabs, tag-input, textarea, toast, toaster, tooltip

### Component Composition Pattern

Build complex components by composing ShadCN primitives:

```typescript
// Example: A data table component
import { Button } from '@/components/ui/button';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';
import { Badge } from '@/components/ui/badge';

export function UsersTable({ users, onEdit, onDelete }: UsersTableProps) {
  return (
    <Table>
      <TableHeader>
        <TableRow>
          <TableHead>Name</TableHead>
          <TableHead>Email</TableHead>
          <TableHead>Role</TableHead>
          <TableHead>Actions</TableHead>
        </TableRow>
      </TableHeader>
      <TableBody>
        {users.map((user) => (
          <TableRow key={user.id}>
            <TableCell>{user.name}</TableCell>
            <TableCell>{user.email}</TableCell>
            <TableCell>
              <Badge variant="secondary">{user.role}</Badge>
            </TableCell>
            <TableCell>
              <Button variant="ghost" size="sm" onClick={() => onEdit(user)}>Edit</Button>
              <Button variant="ghost" size="sm" onClick={() => onDelete(user)}>Delete</Button>
            </TableCell>
          </TableRow>
        ))}
      </TableBody>
    </Table>
  );
}
```

### Dialog-Based CRUD Operations

Most CRUD operations use ShadCN Dialog components:

```typescript
// Example: Create dialog
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';

export function CreateUserDialog({ open, onOpenChange, onSuccess }) {
  const form = useForm({
    resolver: zodResolver(schema),
  });

  const createUser = useMutation({
    mutationFn: usersService.create,
    onSuccess: () => {
      onSuccess();
      onOpenChange(false);
    },
  });

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Create User</DialogTitle>
        </DialogHeader>
        <Form {...form}>
          <form onSubmit={form.handleSubmit((data) => createUser.mutate(data))}>
            {/* Form fields */}
          </form>
        </Form>
      </DialogContent>
    </Dialog>
  );
}
```

### Loading & Error States

Use TanStack Query's built-in states:

```typescript
const { data, isLoading, error, refetch } = useQuery({
  queryKey: ['users'],
  queryFn: usersService.getAll,
});

if (isLoading) return <LoadingSpinner />;
if (error) return <ErrorMessage error={error} onRetry={refetch} />;
```

---

## Routing

SnackBase uses React Router v7 for client-side routing.

### Route Structure

All routes are under the `/admin` prefix:

```typescript
// src/App.tsx
<Routes>
  {/* Public routes */}
  <Route path="/admin/login" element={<LoginPage />} />

  {/* Protected routes with layout */}
  <Route path="/admin" element={<ProtectedRoute><AdminLayout /></ProtectedRoute>}>
    <Route index element={<Navigate to="/admin/dashboard" replace />} />
    <Route path="dashboard" element={<DashboardPage />} />
    <Route path="accounts" element={<AccountsPage />} />
    <Route path="users" element={<UsersPage />} />
    <Route path="groups" element={<GroupsPage />} />
    <Route path="collections" element={<CollectionsPage />} />
    <Route path="collections/:collectionName/records" element={<RecordsPage />} />
    <Route path="roles" element={<RolesPage />} />
    <Route path="audit-logs" element={<AuditLogsPage />} />
    <Route path="migrations" element={<MigrationsPage />} />
    <Route path="macros" element={<MacrosPage />} />
    <Route path="configuration" element={<ConfigurationDashboardPage />} />
  </Route>

  {/* Catch all - redirect to dashboard */}
  <Route path="*" element={<Navigate to="/admin/dashboard" replace />} />
</Routes>
```

### Navigation

Use React Router's hooks for navigation:

```typescript
import { useNavigate } from 'react-router';

function MyComponent() {
  const navigate = useNavigate();

  const handleClick = () => {
    navigate('/admin/users'); // Programmatic navigation
  };

  return <Button onClick={handleClick}>Go to Users</Button>;
}
```

### Sidebar Navigation

The `AppSidebar` component provides navigation with active route highlighting:

```typescript
// src/components/AppSidebar.tsx
const items = [
  { title: "Dashboard", url: "/admin/dashboard", icon: LayoutDashboard },
  { title: "Configuration", url: "/admin/configuration", icon: Settings },
  { title: "Accounts", url: "/admin/accounts", icon: Users },
  // ... more items
];

// Active route highlighting
<SidebarMenuButton asChild isActive={location.pathname === item.url}>
  <Link to={item.url}>
    <item.icon />
    <span>{item.title}</span>
  </Link>
</SidebarMenuButton>
```

---

## Adding New Pages

Follow this pattern when adding a new page:

### Step 1: Create the Page Component

Create a new file in `src/pages/`:

```typescript
// src/pages/SettingsPage.tsx
import { useQuery } from '@tanstack/react-query';
import { settingsService } from '@/services/settings.service';

export function SettingsPage() {
  const { data: settings, isLoading } = useQuery({
    queryKey: ['settings'],
    queryFn: settingsService.getAll,
  });

  if (isLoading) return <div>Loading...</div>;

  return (
    <div className="p-6">
      <h1 className="text-3xl font-bold">Settings</h1>
      {/* Your page content */}
    </div>
  );
}
```

### Step 2: Create the Service (if needed)

Add API functions in `src/services/`:

```typescript
// src/services/settings.service.ts
import { apiClient } from '@/lib/api';

export const settingsService = {
  getAll: async () => {
    const response = await apiClient.get('/settings');
    return response.data;
  },

  update: async (id: string, data: UpdateSettingsDto) => {
    const response = await apiClient.put(`/settings/${id}`, data);
    return response.data;
  },
};
```

### Step 3: Add the Route

Update `src/App.tsx`:

```typescript
<Route path="settings" element={<SettingsPage />} />
```

### Step 4: Add Sidebar Navigation (if needed)

Update `src/components/AppSidebar.tsx`:

```typescript
const items = [
  // ... existing items
  {
    title: 'Settings',
    url: '/admin/settings',
    icon: Settings,
  },
];
```

---

## Styling

SnackBase uses **TailwindCSS 4** with the new `@tailwindcss/vite` plugin.

### TailwindCSS 4 Features

- **Inline @theme syntax**: Theme configuration in CSS files
- **OKLCH color space**: Modern color system
- **CSS custom properties**: For theming (light/dark mode)

### Theme Configuration

Theme is configured in `src/App.css`:

```css
@import "tailwindcss";
@import "tw-animate-css";

@custom-variant dark (&:is(.dark *));

@theme inline {
  --color-background: var(--background);
  --color-foreground: var(--foreground);
  /* ... more color mappings */
}

:root {
  --background: oklch(1 0 0);
  --foreground: oklch(0.145 0 0);
  --primary: oklch(0.205 0 0);
  /* ... more color definitions */
}

.dark {
  --background: oklch(0.145 0 0);
  --foreground: oklch(0.985 0 0);
  /* ... dark mode colors */
}
```

### Utility-First Approach

```typescript
<div className="flex items-center justify-between p-4 bg-white rounded-lg shadow-sm border">
  <h2 className="text-xl font-semibold text-gray-900">Title</h2>
  <Button className="ml-4">Action</Button>
</div>
```

### Common Patterns

| Pattern | Classes | Usage |
|---------|---------|-------|
| Card | `bg-white rounded-lg shadow-sm border p-6` | Container for content sections |
| Button Group | `flex gap-2` | Horizontal button layout |
| Grid | `grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4` | Responsive grid |
| Flex Center | `flex items-center justify-center` | Centered content |
| Section Spacing | `space-y-4` | Vertical spacing between children |

### ShadCN Style Variant

The project uses the "new-york" style variant configured in `components.json`:

```json
{
  "style": "new-york",
  "tailwind": {
    "css": "src/App.css",
    "baseColor": "neutral",
    "cssVariables": true
  }
}
```

---

## Development Workflow

### Environment Setup

Create a `.env` file in the `ui` directory:

```bash
VITE_API_BASE_URL=/api/v1
```

The Vite proxy forwards `/api` requests to `localhost:8000`:

```typescript
// vite.config.ts
export default defineConfig({
  server: {
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      },
    },
  },
});
```

### Running the Dev Server

```bash
cd ui
npm run dev
```

The Vite dev server starts at `http://localhost:5173` with:
- Hot Module Replacement (HMR)
- Fast refresh
- TypeScript checking

### Build for Production

```bash
cd ui
npm run build
```

Creates an optimized production build in `ui/dist/`.

### Linting

```bash
cd ui
npm run lint
```

Runs ESLint to check code quality.

### Type Checking

TypeScript checks run automatically in the IDE and during build. For immediate feedback:

```bash
cd ui
npx tsc --noEmit
```

---

## Features

### Configuration/Providers Management

The Configuration page (`/admin/configuration`) manages external service providers:

**Features:**
- System-level and account-level configurations
- Provider categories: auth (OAuth, SAML), email, storage
- Enable/disable configurations
- View and edit configuration values
- Add new providers
- Test provider connections

**Services:**
- `admin.service.ts` - Configuration API
- Provider schema validation
- Hierarchical configuration (system → account)

**Components:**
- `SystemProvidersTab.tsx` - System-level configs
- `AccountProvidersTab.tsx` - Account-level configs
- `ConfigurationForm.tsx` - Dynamic form based on provider schema
- `AddProviderModal.tsx` - Add new provider
- `ProviderLogo.tsx` - Provider logo display

### Email Template Management

The Email Templates tab allows management of email templates:

**Features:**
- List all email templates
- Edit template subject and body
- Enable/disable templates
- Test email sending
- Preview rendered templates
- View email logs

**Services:**
- `email.service.ts` - Email template API

**Components:**
- `EmailTemplatesTab.tsx` - Main templates page
- `EmailTemplateEditDialog.tsx` - Edit template
- `EmailLogList.tsx` - Display email logs
- `EmailLogDetail.tsx` - Email log details

### Macro Management

The Macros page (`/admin/macros`) manages SQL macros:

**Features:**
- List all macros
- Create/edit/delete macros
- Test macro execution
- View macro details

**Components:**
- `MacrosTable.tsx` - Macros listing
- `MacroEditorDialog.tsx` - Create/edit macro
- `MacroDetailDialog.tsx` - View macro details
- `MacroTestDialog.tsx` - Test macro execution
- `DeleteMacroDialog.tsx` - Delete macro confirmation

### PII Masking Support

Collections support PII (Personally Identifiable Information) masking:

**Field Types:**
- `email` - Email address masking
- `ssn` - Social Security Number masking
- `phone` - Phone number masking
- `name` - Name masking
- `full` - Full masking
- `custom` - Custom masking pattern

**Usage in Collection Schema:**
```typescript
{
  name: 'email',
  type: 'email',
  pii: true,
  mask_type: 'email'
}
```

---

## Common Patterns

### Data Tables with Actions

```typescript
export function UsersPage() {
  const { data: users, isLoading } = useQuery({
    queryKey: ['users'],
    queryFn: usersService.getAll,
  });

  const deleteUser = useMutation({
    mutationFn: usersService.delete,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['users'] });
    },
  });

  return (
    <Table>
      <TableBody>
        {users?.map((user) => (
          <TableRow key={user.id}>
            <TableCell>{user.email}</TableCell>
            <TableCell>
              <Button onClick={() => deleteUser.mutate(user.id)}>Delete</Button>
            </TableCell>
          </TableRow>
        ))}
      </TableBody>
    </Table>
  );
}
```

### Form Handling

```typescript
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import {
  Form,
  FormControl,
  FormField,
  FormItem,
  FormLabel,
  FormMessage,
} from '@/components/ui/form';

const schema = z.object({
  email: z.string().email(),
  name: z.string().min(2),
});

export function CreateUserForm() {
  const form = useForm({
    resolver: zodResolver(schema),
  });

  const createUser = useMutation({
    mutationFn: usersService.create,
    onSuccess: () => {
      // Show success toast
      // Reset form
    },
  });

  return (
    <Form {...form}>
      <form onSubmit={form.handleSubmit((data) => createUser.mutate(data))}>
        <FormField
          control={form.control}
          name="email"
          render={({ field }) => (
            <FormItem>
              <FormLabel>Email</FormLabel>
              <FormControl>
                <Input {...field} />
              </FormControl>
              <FormMessage />
            </FormItem>
          )}
        />
        <Button type="submit">Create</Button>
      </form>
    </Form>
  );
}
```

### Mutations with Optimistic Updates

```typescript
const updateUser = useMutation({
  mutationFn: ({ id, data }: { id: string; data: UpdateUserDto }) =>
    usersService.update(id, data),

  onMutate: async ({ id, data }) => {
    // Cancel ongoing queries
    await queryClient.cancelQueries({ queryKey: ['users'] });

    // Snapshot previous value
    const previousUsers = queryClient.getQueryData(['users']);

    // Optimistically update
    queryClient.setQueryData(['users'], (old) =>
      old?.map((user) =>
        user.id === id ? { ...user, ...data } : user
      )
    );

    return { previousUsers };
  },

  onError: (err, variables, context) => {
    // Rollback on error
    queryClient.setQueryData(['users'], context?.previousUsers);
  },

  onSettled: () => {
    // Refetch to ensure consistency
    queryClient.invalidateQueries({ queryKey: ['users'] });
  },
});
```

---

## Best Practices

### 1. Component Organization

- Keep components focused and single-purpose
- Extract reusable logic into custom hooks
- Co-locate related components in feature folders

### 2. Type Safety

- Always define TypeScript interfaces for API responses
- Use Zod schemas for runtime validation
- Avoid `any` type - use `unknown` if truly unknown

### 3. Error Handling

- Always handle loading and error states from TanStack Query
- Show user-friendly error messages
- Implement retry logic for failed requests
- Use the `handleApiError()` utility from `lib/api.ts`

### 4. Performance

- Use TanStack Query's caching to avoid redundant requests
- Implement pagination for large datasets
- Lazy load components with React.lazy()

### 5. Accessibility

- Use semantic HTML elements
- Ensure keyboard navigation works
- Test with screen readers
- ShadCN components handle most accessibility concerns

---

## Troubleshooting

### Common Issues

| Issue | Solution |
|-------|----------|
| API calls return 401 | Check that token is in localStorage under 'auth-storage'; verify Axios interceptor is working |
| Styles not applying | Ensure TailwindCSS classes are correct; check for typos; verify App.css is imported |
| Route not found | Verify route is registered in App.tsx; check for typos in path |
| TypeScript errors | Run `npx tsc --noEmit` to see all errors; check for missing type imports |
| HMR not working | Restart dev server; check Vite version |
| Provider configuration not saving | Check that all required fields are filled; verify provider schema |

---

## Resources

- **React Documentation**: https://react.dev/
- **React Router v7**: https://reactrouter.com/
- **TanStack Query**: https://tanstack.com/query/latest
- **Zustand**: https://zustand-demo.pmnd.rs/
- **TailwindCSS 4**: https://tailwindcss.com/docs
- **ShadCN**: https://ui.shadcn.com/
- **Radix UI**: https://www.radix-ui.com/
- **Vite**: https://vite.dev/

---

**Ready to build?** Check out the main [CLAUDE.md](../CLAUDE.md) for the full project context and development setup.
