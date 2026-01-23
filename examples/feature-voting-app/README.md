# Feature Voting App

A feature request and voting application demonstrating SnackBase-js SDK integration. Features email authentication, multi-tenancy, real-time updates, and a voting system for feature requests.

## Features

- **Authentication**: Email/password registration and login using SnackBase-js SDK
- **Feature Submission**: Users can submit new feature requests with title and description
- **Voting System**: Users can upvote features they want (one vote per user per feature)
- **Real-Time Updates**: Instant updates using SnackBase WebSocket/SSE subscriptions
- **Status Management**: Feature creators can update status (Open, In Progress, Completed)
- **Multi-Tenancy**: Each account's features are isolated using SnackBase's account-based isolation
- **Responsive Design**: Clean UI built with Tailwind CSS V4

## Tech Stack

- **Frontend**: React 19 + TypeScript + Vite 7
- **Routing**: react-router-dom v7
- **SDK**: @snackbase/sdk - Official JavaScript/TypeScript SDK
- **React Integration**: @snackbase/sdk/react - React hooks and context provider
- **Styling**: Tailwind CSS V4
- **Components**: Custom Radix-style UI components

## Prerequisites

1. **SnackBase server running** on `http://localhost:8000`
2. **Superadmin credentials** for creating the features collection
3. **SnackBase-js SDK built locally** (in the monorepo)

## Setup

### 1. Start SnackBase Server

```bash
cd /path/to/SnackBase
uv run python -m snackbase serve --reload
```

### 2. Create the "features" Collection

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
    "name": "features",
    "schema": [
      {
        "name": "title",
        "type": "text",
        "required": true
      },
      {
        "name": "description",
        "type": "text",
        "required": true
      },
      {
        "name": "votes",
        "type": "number",
        "default": 0
      },
      {
        "name": "status",
        "type": "text",
        "default": "open"
      },
      {
        "name": "voted_by",
        "type": "json",
        "default": "[]"
      }
    ]
  }'
```

### 2.5. Configure Collection Permissions

Configure permissions so that:
- All authenticated users can view and create features
- All authenticated users can upvote (update only `votes` and `voted_by` fields)
- Only the creator can delete their own features

```bash
curl -X PUT http://localhost:8000/api/v1/collections/features/rules \
  -H "Authorization: Bearer <YOUR_TOKEN>" \
  -H "Content-Type: application/json" \
  -d '{
    "list_rule": "",
    "view_rule": "",
    "create_rule": "",
    "update_rule": "",
    "delete_rule": "created_by = @request.auth.id",
    "list_fields": "*",
    "view_fields": "*",
    "create_fields": "[\"title\", \"description\"]",
    "update_fields": "[\"votes\", \"voted_by\"]"
  }'
```

**Permission breakdown:**

| Operation | Rule | Fields | Result |
|-----------|------|--------|--------|
| list | `""` | `*` | All authenticated users can list features |
| view | `""` | `*` | All authenticated users can view features |
| create | `""` | `["title", "description"]` | All authenticated users can create features |
| update | `""` | `["votes", "voted_by"]` | All authenticated users can upvote |
| delete | `created_by = @request.auth.id` | N/A | Only creator can delete |

> **Note:** With this configuration, no one (including the creator) can edit `title` or `description` after creation. If you need creators to edit their own features, consider implementing a custom backend endpoint for voting.

### 3. Build and Link the SnackBase-js SDK

Since the SDK is not published to npm yet, you need to build it locally and link it:

```bash
# From the monorepo root, build the SDK
cd SnackBase-js
npm run build

# Link the SDK globally
npm link

# Go to the feature voting app and link the SDK
cd ../SnackBase/examples/feature-voting-app
npm link @snackbase/sdk
```

### 4. Install Other Dependencies

```bash
npm install
```

### 5. Configure Environment

Create a `.env` file in the project root:

```
VITE_SNACKBASE_URL=http://localhost:8000
```

### 6. Start the Dev Server

```bash
npm run dev
```

The app will be available at `http://localhost:5173`

## Usage

### Register a New Account

1. Navigate to `http://localhost:5173/register`
2. Fill in:
   - **Name**: Your display name
   - **Email**: Your email address
   - **Password**: Must be 8+ characters
   - **Confirm Password**: Re-enter your password
3. Click "Create Account"
4. **Check your email** for a verification link
5. Click the verification link in the email to verify your account
6. Return to the app and log in

### Login

1. Navigate to `http://localhost:5173/login`
2. Enter your email and password
3. Click "Sign In"

### Manage Features

- **Submit Feature**: Click the "New Feature" button and fill in the form
- **Vote**: Click the vote button on any feature (one vote per user per feature)
- **Change Status**: If you created a feature, you can change its status (Open, In Progress, Completed)
- **Delete**: Feature creators can delete their own features
- **Sort**: Sort features by votes or most recent

## Project Structure

```
src/
├── lib/
│   └── utils.ts          # Utility functions (cn for class merging)
├── types/
│   └── index.ts          # TypeScript interfaces (Feature types)
├── components/
│   ├── ui/               # Reusable UI components (Button, Input, Label, Card)
│   ├── auth/             # Login, Register, ProtectedRoute
│   └── features/         # FeatureList component
└── App.tsx               # Routing configuration
```

## SDK Integration

This app uses the **SnackBase-js SDK** rather than direct API calls. Key patterns:

### Initialization

```tsx
import { SnackBaseClient, SnackBaseProvider } from '@snackbase/sdk'

const client = new SnackBaseClient({
  baseUrl: import.meta.env.VITE_SNACKBASE_URL
})

<SnackBaseProvider client={client}>
  <App />
</SnackBaseProvider>
```

### Authentication Hook

```tsx
import { useAuth } from '@snackbase/sdk/react'

const { user, login, logout, isAuthenticated, isLoading } = useAuth()
```

### Query Hook

```tsx
import { useQuery } from '@snackbase/sdk/react'

const { data, loading, error, refetch } = useQuery<Feature>('features', {
  sort: '-votes'
})
```

### Mutation Hook

```tsx
import { useMutation } from '@snackbase/sdk/react'

const { create, update, del, loading } = useMutation<Feature>('features')

await create({ title, description, votes: 0 })
```

### Real-Time Subscriptions

```tsx
import { useSnackBase } from '@snackbase/sdk/react'

const client = useSnackBase()

const unsubscribe = client.realtime.subscribe('features', (event) => {
  if (event.action === 'create') {
    // Handle new feature
  }
})
```

## API Endpoints Used

| Endpoint                     | Method | Description                      |
| ---------------------------- | ------ | -------------------------------- |
| `/api/v1/auth/register`      | POST   | Create new account + user        |
| `/api/v1/auth/login`         | POST   | Login with credentials           |
| `/api/v1/records/features`   | GET    | List features (filtered by account) |
| `/api/v1/records/features`   | POST   | Create new feature               |
| `/api/v1/records/features/{id}` | PATCH | Update feature                   |
| `/api/v1/records/features/{id}` | DELETE | Delete feature                   |
| WebSocket endpoint           | WS     | Real-time feature updates        |

## Authentication Flow

1. User registers → receives success message to check email
2. User clicks verification link in email → email is verified
3. User logs in → SDK stores auth state automatically
4. SDK handles token management and refresh automatically
5. All SDK calls include auth headers automatically

## Real-Time Updates

The app subscribes to feature collection changes:

```tsx
useEffect(() => {
  const unsubscribe = client.realtime.subscribe('features', (event) => {
    // Update local state based on event.action
    // - create: Add new feature
    // - update: Update existing feature
    // - delete: Remove feature
  })

  return () => unsubscribe()
}, [client])
```

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

The `features` collection may not exist. Run the curl commands in the Setup section to create it.

### Authentication errors

- Ensure SnackBase server is running on `http://localhost:8000`
- Verify your superadmin credentials are correct
- Check that the `VITE_SNACKBASE_URL` in `.env` points to the correct URL

### CORS errors

Ensure SnackBase is configured with the correct CORS origins. Add `http://localhost:5173` to `SNACKBASE_CORS_ORIGINS` in your SnackBase `.env` file.

## License

MIT
