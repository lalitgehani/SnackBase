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

---

## Tech Stack

The SnackBase admin UI is built with modern, production-ready technologies:

| Technology | Version | Purpose |
|------------|---------|---------|
| **React** | 19 | UI framework |
| **TypeScript** | 5.x | Type safety |
| **Vite** | 7 | Build tool and dev server |
| **React Router** | v7 | Client-side routing |
| **TailwindCSS** | 4 | Utility-first styling |
| **Radix UI** | Latest | Accessible component primitives |
| **ShadCN** | Latest | Pre-built component library |
| **TanStack Query** | 5.x | Server state management |
| **Zustand** | 5.x | Client state management |
| **Zod** | 3.x | Schema validation |
| **Axios** | 1.x | HTTP client |

> **Screenshot Placeholder 1**
>
> **Description**: The `ui/package.json` file showing all the key dependencies and their versions.

---

## Project Structure

```
ui/
├── src/
│   ├── main.tsx                 # Application entry point
│   ├── App.tsx                  # Root component with Router
│   ├── vite-env.d.ts            # Vite type declarations
│   │
│   ├── pages/                   # Page components (route handlers)
│   │   ├── LoginPage.tsx
│   │   ├── DashboardPage.tsx
│   │   ├── AccountsPage.tsx
│   │   ├── UsersPage.tsx
│   │   ├── GroupsPage.tsx
│   │   ├── CollectionsPage.tsx
│   │   ├── RecordsPage.tsx
│   │   ├── RolesPage.tsx
│   │   ├── AuditLogsPage.tsx
│   │   └── MigrationsPage.tsx
│   │
│   ├── components/              # Reusable components
│   │   ├── ui/                  # ShadCN components (DO NOT EDIT)
│   │   ├── accounts/            # Account-related components
│   │   ├── audit-logs/          # Audit log components
│   │   ├── collections/         # Collection builder components
│   │   ├── common/              # Shared components (layout, etc.)
│   │   ├── groups/              # Group components
│   │   ├── migrations/          # Migration components
│   │   ├── records/             # Record CRUD components
│   │   ├── roles/               # Role management components
│   │   ├── users/               # User management components
│   │   ├── AppSidebar.tsx       # Main navigation sidebar
│   │   └── ProtectedRoute.tsx   # Auth wrapper component
│   │
│   ├── services/                # API service layer
│   │   ├── api.ts               # Axios configuration
│   │   ├── auth.service.ts      # Authentication API
│   │   ├── accounts.service.ts  # Accounts API
│   │   ├── collections.service.ts
│   │   ├── records.service.ts
│   │   ├── roles.service.ts
│   │   ├── users.service.ts
│   │   ├── groups.service.ts
│   │   ├── dashboard.service.ts
│   │   ├── audit.service.ts
│   │   └── migrations.service.ts
│   │
│   ├── stores/                  # Zustand state stores
│   │   └── auth.store.ts        # Authentication state
│   │
│   ├── lib/                     # Utilities and helpers
│   │   └── utils.ts             # Utility functions
│   │
│   └── types/                   # TypeScript type definitions
│       └── index.ts             # Shared types
│
├── index.html                   # HTML entry point
├── package.json                 # Dependencies and scripts
├── tsconfig.json                # TypeScript configuration
├── vite.config.ts               # Vite build configuration
├── tailwind.config.js           # TailwindCSS configuration
├── postcss.config.js            # PostCSS configuration
└── components.json              # ShadCN component configuration
```

> **Screenshot Placeholder 2**
>
> **Description**: VS Code file explorer showing the ui/src folder structure with expanded folders revealing all pages and components.

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
   - Authentication state is global
   - Use Zustand for cross-component state

4. **Local state with React hooks**
   - Use `useState` for component-specific state
   - Use `useForm` (from react-hook-form) for form state

> **Screenshot Placeholder 3**
>
> **Description**: A diagram illustrating the data flow from User Action → Component → Service → API → Server and back with TanStack Query caching.

---

## State Management

SnackBase uses a hybrid state management approach:

### Global State: Zustand

Located in `src/stores/auth.store.ts`:

```typescript
interface AuthState {
  user: User | null;
  token: string | null;
  isAuthenticated: boolean;
  login: (email: string, password: string) => Promise<void>;
  logout: () => void;
  setToken: (token: string) => void;
}

export const useAuthStore = create<AuthState>((set) => ({
  user: null,
  token: localStorage.getItem('access_token'),
  isAuthenticated: !!localStorage.getItem('access_token'),
  // ... actions
}));
```

**When to use Zustand:**
- Authentication state
- User preferences
- Global application settings
- Cross-route data that doesn't come from the API

> **Screenshot Placeholder 4**
>
> **Description**: The `auth.store.ts` file showing the Zustand store implementation with state and actions.

### Server State: TanStack Query

All data from the API is managed by TanStack Query:

```typescript
// In a page component
const { data: collections, isLoading, error } = useQuery({
  queryKey: ['collections'],
  queryFn: collectionsService.getAll,
});
```

**Key Features:**
- Automatic caching and revalidation
- Background refetching
- Optimistic updates
- Loading and error states built-in

> **Screenshot Placeholder 5**
>
> **Description**: Code example showing TanStack Query usage in a page component with data, isLoading, and error states.

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
import api from './api';

export const collectionsService = {
  // Get all collections
  getAll: async () => {
    const response = await api.get('/collections');
    return response.data;
  },

  // Get single collection
  getById: async (id: string) => {
    const response = await api.get(`/collections/${id}`);
    return response.data;
  },

  // Create collection
  create: async (data: CreateCollectionDto) => {
    const response = await api.post('/collections', data);
    return response.data;
  },

  // Update collection
  update: async (id: string, data: UpdateCollectionDto) => {
    const response = await api.put(`/collections/${id}`, data);
    return response.data;
  },

  // Delete collection
  delete: async (id: string) => {
    const response = await api.delete(`/collections/${id}`);
    return response.data;
  },
};
```

> **Screenshot Placeholder 6**
>
> **Description**: A service file showing the CRUD operations pattern with consistent function names and TypeScript types.

### Axios Configuration

The `api.ts` file configures the Axios instance:

```typescript
// src/services/api.ts
import axios from 'axios';

const api = axios.create({
  baseURL: import.meta.env.VITE_API_URL || 'http://localhost:8000/api/v1',
  timeout: 10000,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Request interceptor - add auth token
api.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('access_token');
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => Promise.reject(error)
);

// Response interceptor - handle errors
api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      // Token expired - redirect to login
      useAuthStore.getState().logout();
      window.location.href = '/login';
    }
    return Promise.reject(error);
  }
);

export default api;
```

> **Screenshot Placeholder 7**
>
> **Description**: The `api.ts` file showing the Axios instance with request/response interceptors for auth token injection and error handling.

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
│ Store access_token   │
│ in localStorage      │
└──────┬───────────────┘
       │
       ▼
┌──────────────────────┐
│ Update Zustand store │
│ (user, token)        │
└──────┬───────────────┘
       │
       ▼
┌──────────────────────┐
│ Redirect to /        │
│ (dashboard)          │
└──────────────────────┘
```

> **Screenshot Placeholder 8**
>
> **Description**: A sequence diagram showing the login flow from LoginPage → Auth Service → API → Local Storage → Zustand Store → Dashboard.

### Protected Routes

The `ProtectedRoute` component wraps routes that require authentication:

```typescript
// src/components/ProtectedRoute.tsx
import { Navigate } from 'react-router-dom';
import { useAuthStore } from '@/stores/auth.store';

interface ProtectedRouteProps {
  children: React.ReactNode;
}

export function ProtectedRoute({ children }: ProtectedRouteProps) {
  const isAuthenticated = useAuthStore((state) => state.isAuthenticated);

  if (!isAuthenticated) {
    return <Navigate to="/login" replace />;
  }

  return <children />;
}
```

> **Screenshot Placeholder 9**
>
> **Description**: The `ProtectedRoute.tsx` component showing how it wraps children and checks authentication status.

### Usage in App.tsx

```typescript
// src/App.tsx
import { BrowserRouter, Routes, Route } from 'react-router-dom';
import { ProtectedRoute } from '@/components/ProtectedRoute';

function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/login" element={<LoginPage />} />
        <Route
          path="/*"
          element={
            <ProtectedRoute>
              <Layout />
            </ProtectedRoute>
          }
        >
          <Route path="/" element={<DashboardPage />} />
          <Route path="/accounts" element={<AccountsPage />} />
          <Route path="/users" element={<UsersPage />} />
          {/* ... more routes */}
        </Route>
      </Routes>
    </BrowserRouter>
  );
}
```

> **Screenshot Placeholder 10**
>
> **Description**: The `App.tsx` file showing the routing structure with ProtectedRoute wrapping all authenticated routes.

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

> **Screenshot Placeholder 11**
>
> **Description**: Terminal showing the ShadCN CLI command to add a new component, with the success message.

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

> **Screenshot Placeholder 12**
>
> **Description**: Code example showing how to compose ShadCN components (Button, Table, Badge) into a custom UsersTable component.

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

> **Screenshot Placeholder 13**
>
> **Description**: A page component showing conditional rendering based on loading and error states from TanStack Query.

---

## Routing

SnackBase uses React Router v7 for client-side routing.

### Route Structure

```typescript
// src/App.tsx
<Routes>
  {/* Public routes */}
  <Route path="/login" element={<LoginPage />} />

  {/* Protected routes with layout */}
  <Route path="/" element={<ProtectedRoute><Layout /></ProtectedRoute>}>
    <Route index element={<DashboardPage />} />
    <Route path="accounts" element={<AccountsPage />} />
    <Route path="users" element={<UsersPage />} />
    <Route path="groups" element={<GroupsPage />} />
    <Route path="collections" element={<CollectionsPage />} />
    <Route path="collections/:collectionId/records" element={<RecordsPage />} />
    <Route path="roles" element={<RolesPage />} />
    <Route path="audit-logs" element={<AuditLogsPage />} />
    <Route path="migrations" element={<MigrationsPage />} />
  </Route>
</Routes>
```

> **Screenshot Placeholder 14**
>
> **Description**: The complete route configuration in App.tsx showing all available routes and their hierarchy.

### Navigation

Use React Router's hooks for navigation:

```typescript
import { useNavigate } from 'react-router-dom';

function MyComponent() {
  const navigate = useNavigate();

  const handleClick = () => {
    navigate('/users'); // Programmatic navigation
  };

  return <Button onClick={handleClick}>Go to Users</Button>;
}
```

> **Screenshot Placeholder 15**
>
> **Description**: Code example showing the useNavigate hook being used for programmatic navigation.

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

> **Screenshot Placeholder 16**
>
> **Description**: A new page component file showing the basic structure with TanStack Query data fetching.

### Step 2: Create the Service (if needed)

Add API functions in `src/services/`:

```typescript
// src/services/settings.service.ts
import api from './api';

export const settingsService = {
  getAll: async () => {
    const response = await api.get('/settings');
    return response.data;
  },

  update: async (id: string, data: UpdateSettingsDto) => {
    const response = await api.put(`/settings/${id}`, data);
    return response.data;
  },
};
```

> **Screenshot Placeholder 17**
>
> **Description**: A new service file showing the standard CRUD functions pattern.

### Step 3: Add the Route

Update `src/App.tsx`:

```typescript
<Route path="settings" element={<SettingsPage />} />
```

> **Screenshot Placeholder 18**
>
> **Description**: App.tsx showing where to add the new route in the Routes configuration.

### Step 4: Add Sidebar Navigation (if needed)

Update `src/components/AppSidebar.tsx`:

```typescript
const navigationItems = [
  // ... existing items
  {
    title: 'Settings',
    href: '/settings',
    icon: Settings,
  },
];
```

> **Screenshot Placeholder 19**
>
> **Description**: The AppSidebar.tsx file showing where to add a new navigation item with title, href, and icon.

---

## Styling

SnackBase uses **TailwindCSS 4** for styling.

### Utility-First Approach

```typescript
<div className="flex items-center justify-between p-4 bg-white rounded-lg shadow-sm border">
  <h2 className="text-xl font-semibold text-gray-900">Title</h2>
  <Button className="ml-4">Action</Button>
</div>
```

> **Screenshot Placeholder 20**
>
> **Description**: Code example showing TailwindCSS utility classes for layout, spacing, colors, and typography.

### Common Patterns

| Pattern | Classes | Usage |
|---------|---------|-------|
| Card | `bg-white rounded-lg shadow-sm border p-6` | Container for content sections |
| Button Group | `flex gap-2` | Horizontal button layout |
| Grid | `grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4` | Responsive grid |
| Flex Center | `flex items-center justify-center` | Centered content |
| Section Spacing | `space-y-4` | Vertical spacing between children |

> **Screenshot Placeholder 21**
>
> **Description**: A reference table or cheat sheet showing common TailwindCSS utility patterns used in the project.

### Theme Colors

The project uses a consistent color palette via TailwindCSS configuration:

```javascript
// tailwind.config.js
export default {
  theme: {
    extend: {
      colors: {
        border: 'hsl(var(--border))',
        background: 'hsl(var(--background))',
        foreground: 'hsl(var(--foreground))',
        primary: {
          DEFAULT: 'hsl(var(--primary))',
          foreground: 'hsl(var(--primary-foreground))',
        },
        // ... more colors
      },
    },
  },
};
```

> **Screenshot Placeholder 22**
>
> **Description**: The TailwindCSS configuration showing the HSL color variables used for theming.

---

## Development Workflow

### Running the Dev Server

```bash
cd ui
npm run dev
```

The Vite dev server starts at `http://localhost:5173` with:
- Hot Module Replacement (HMR)
- Fast refresh
- TypeScript checking

> **Screenshot Placeholder 23**
>
> **Description**: Browser window showing the Vite dev server running with the SnackBase UI loaded.

### Build for Production

```bash
cd ui
npm run build
```

Creates an optimized production build in `ui/dist/`.

> **Screenshot Placeholder 24**
>
> **Description**: Terminal output showing the production build completing with bundle sizes and optimization info.

### Linting

```bash
cd ui
npm run lint
```

Runs ESLint to check code quality.

> **Screenshot Placeholder 25**
>
> **Description**: Terminal showing ESLint results with any warnings or errors found.

### Type Checking

TypeScript checks run automatically in the IDE and during build. For immediate feedback:

```bash
cd ui
npx tsc --noEmit
```

> **Screenshot Placeholder 26**
>
> **Description**: VS Code showing TypeScript errors inline in the editor with the Problems panel open.

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
      {/* Table header */}
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

> **Screenshot Placeholder 27**
>
> **Description**: Complete example showing a data table with delete functionality using TanStack Query mutations.

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

> **Screenshot Placeholder 28**
>
> **Description**: A complete form component using react-hook-form, Zod validation, and ShadCN form components.

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

> **Screenshot Placeholder 29**
>
> **Description**: Code showing optimistic updates pattern with TanStack Query mutations including rollback on error.

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
| API calls return 401 | Check that token is in localStorage; verify Axios interceptor is working |
| Styles not applying | Ensure TailwindCSS classes are correct; check for typos |
| Route not found | Verify route is registered in App.tsx; check for typos in path |
| TypeScript errors | Run `npx tsc --noEmit` to see all errors; check for missing type imports |
| HMR not working | Restart dev server; check Vite version |

> **Screenshot Placeholder 30**
>
> **Description**: A troubleshooting table showing common frontend issues and their solutions.

---

## Resources

- **React Documentation**: https://react.dev/
- **React Router**: https://reactrouter.com/
- **TanStack Query**: https://tanstack.com/query/latest
- **Zustand**: https://zustand-demo.pmnd.rs/
- **TailwindCSS**: https://tailwindcss.com/docs
- **ShadCN**: https://ui.shadcn.com/
- **Radix UI**: https://www.radix-ui.com/

---

**Ready to build?** Check out the [Quick Start Tutorial](./quick-start.md) to get the application running, then dive into the code!
