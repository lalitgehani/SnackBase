# SnackBase To-Do App

A multi-user to-do application demonstrating SnackBase as a Backend-as-a-Service (BaaS). Features email authentication, account-based multi-tenancy, and full CRUD operations for todos.

## Features

- **Authentication**: Email/password registration and login with secure JWT tokens
- **Multi-Tenancy**: Each account's todos are isolated using SnackBase's account-based isolation
- **Todo Management**: Create, read, update, and delete todos
- **Priority Levels**: Set todo priority (low, medium, high)
- **Filtering**: View all, active, or completed todos
- **Responsive Design**: Clean UI built with Tailwind CSS V4

## Tech Stack

- **Frontend**: React 19 + TypeScript + Vite 7
- **Routing**: react-router-dom v7
- **State Management**: Zustand with persistence
- **Forms**: react-hook-form + zod validation
- **API Client**: Axios with interceptors for token refresh
- **Styling**: Tailwind CSS V4
- **Components**: Radix UI primitives

## Prerequisites

1. **SnackBase server running** on `http://localhost:8000`
2. **Superadmin credentials** for creating the todos collection

## Setup

### 1. Start SnackBase Server

```bash
cd /path/to/SnackBase
uv run python -m snackbase serve --reload
```

### 2. Create the "todos" Collection

First, login to get an authentication token:

```bash
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "account": "SY0000",
    "email": "admin@admin.com",
    "password": "Admin@123456"
  }'
```

Copy the `token` from the response, then create the collection:

```bash
curl -sL -X POST http://localhost:8000/api/v1/collections/ \
  -H "Authorization: Bearer <YOUR_TOKEN>" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "todos",
    "schema": [
      {
        "name": "title",
        "type": "text",
        "required": true
      },
      {
        "name": "description",
        "type": "text",
        "required": false
      },
      {
        "name": "completed",
        "type": "boolean",
        "default": false
      },
      {
        "name": "priority",
        "type": "text",
        "default": "medium"
      }
    ]
  }'
```

> **Note**: Use `-sL` flag with curl to follow redirects (the endpoint redirects from `/api/v1/collections/` to `/api/v1/collections`)

### 3. Install Dependencies

```bash
npm install
```

### 4. Configure Environment

Create a `.env` file in the project root:

```
VITE_API_BASE_URL=http://localhost:8000/api/v1
```

### 5. Start the Dev Server

```bash
npm run dev
```

The app will be available at `http://localhost:5173`

## Usage

### Register a New Account

1. Navigate to `http://localhost:5173/register`
2. Fill in:
   - **Account Name**: Display name for your account
   - **Account Slug**: URL-friendly identifier (auto-generated from account name)
   - **Email**: Your email address
   - **Password**: Must be 12+ characters with uppercase, lowercase, number, and special character
3. Click "Create Account"
4. You'll be automatically logged in and redirected to the todos page

### Login

1. Navigate to `http://localhost:5173/login`
2. Enter your account slug/ID, email, and password
3. Click "Login"

### Manage Todos

- **Create Todo**: Click the "Add Todo" button and fill in the form
- **Complete Todo**: Click the checkbox next to a todo
- **Edit Todo**: Click the pencil icon to modify a todo
- **Delete Todo**: Click the trash icon to remove a todo
- **Filter Todos**: Use the "All", "Active", or "Completed" buttons

## Project Structure

```
src/
├── lib/
│   ├── api.ts          # Axios client with interceptors
│   └── utils.ts        # Utility functions
├── types/
│   └── index.ts        # TypeScript interfaces
├── services/
│   ├── auth.service.ts # Auth API calls
│   └── todos.service.ts# Todo CRUD operations
├── stores/
│   └── auth.store.ts   # Zustand auth state
├── components/
│   ├── ui/             # Reusable UI components
│   ├── auth/           # Login, Register, ProtectedRoute
│   └── todos/          # TodoList, TodoItem, TodoForm
└── App.tsx             # Routing configuration
```

## API Endpoints Used

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/v1/auth/register` | POST | Create new account + user |
| `/api/v1/auth/login` | POST | Login with credentials |
| `/api/v1/auth/refresh` | POST | Refresh access token |
| `/api/v1/auth/me` | GET | Get current user info |
| `/api/v1/records/todos` | GET | List todos (filtered by account) |
| `/api/v1/records/todos` | POST | Create new todo |
| `/api/v1/records/todos/{id}` | GET | Get single todo |
| `/api/v1/records/todos/{id}` | PATCH | Update todo |
| `/api/v1/records/todos/{id}` | DELETE | Delete todo |

## Authentication Flow

1. User registers/logs in → receives `access_token` (1 hour) and `refresh_token` (7 days)
2. Tokens stored in localStorage via Zustand persist middleware
3. Axios request interceptor injects `Authorization: Bearer <token>` header
4. On 401 error → response interceptor attempts token refresh
5. If refresh fails → user redirected to login

## Multi-Tenancy

SnackBase automatically filters records by `account_id`, ensuring each account only sees their own data. This is handled server-side via the built-in `account_isolation_hook`.

## Development

```bash
# Run dev server
npm run dev

# Build for production
npm run build

# Preview production build
npm run preview

# Run linter
npm run lint
```

## Troubleshooting

### "Collection not found" error

The `todos` collection may not exist. Run the curl commands in the Setup section to create it.

### Authentication errors

- Ensure SnackBase server is running on `http://localhost:8000`
- Verify your superadmin credentials are correct
- Check that the `VITE_API_BASE_URL` in `.env` points to the correct URL

### CORS errors

Ensure SnackBase is configured with the correct CORS origins. Add `http://localhost:5173` to `SNACKBASE_CORS_ORIGINS` in your SnackBase `.env` file.

## License

MIT
