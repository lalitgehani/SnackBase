# Quick Start Guide

Get up and running with SnackBase in 5 minutes. This guide will walk you through the essential steps to set up your instance, create your first collection, add data, set up permissions, and make API requests.

---

## Prerequisites

Before you begin, ensure you have:

- **Python 3.12+** installed
- **uv** package manager installed (`curl -LsSf https://astral.sh/uv/install.sh | sh`)
- **Git** installed (for cloning the repository)

---

## Step 1: Install and Start SnackBase

### 1.1 Clone the Repository

```bash
git clone https://github.com/yourusername/snackbase.git
cd SnackBase
```

### 1.2 Install Dependencies

SnackBase uses `uv` for fast, reliable package management:

```bash
uv sync
```

> **Screenshot Placeholder 1**
>
> **Description**: Terminal window showing the `uv sync` command completing successfully. Should show installed packages and a success message.

### 1.3 Configure Environment

Create a `.env` file from the example template:

```bash
cp .env.example .env
```

For local development, the default values work fine. However, for production, update at minimum:
- `SNACKBASE_SECRET_KEY` - Generate a secure random string
- `SNACKBASE_DATABASE_URL` - Switch to PostgreSQL

> **Screenshot Placeholder 2**
>
> **Description**: Text editor showing the `.env` file with key environment variables highlighted.

### 1.4 Initialize the Database

```bash
uv run python -m snackbase init-db
```

This command:
- Creates the database file at `./sb_data/snackbase.db`
- Runs Alembic migrations to set up all tables
- Creates the `system` account (ID: `SY0000`) for superadmin operations

> **Screenshot Placeholder 3**
>
> **Description**: Terminal output showing the database initialization command with success messages.

### 1.5 Create a Superadmin User

```bash
uv run python -m snackbase create-superadmin
```

You'll be prompted to enter:
- Email address (e.g., `admin@example.com`)
- Password (minimum 8 characters, recommended: mix of letters, numbers, symbols)
- Password confirmation

> **Screenshot Placeholder 4**
>
> **Description**: Terminal showing the interactive superadmin creation prompt with filled-in values and success message.

### 1.6 Start the Server

```bash
uv run python -m snackbase serve
```

You should see output indicating the server is running:
```
INFO:     Uvicorn running on http://0.0.0.0:8000
INFO:     Application startup complete.
```

> **Screenshot Placeholder 5**
>
> **Description**: Terminal showing the server startup with Uvicorn displaying the running URL.

### 1.7 Access the Admin UI

Open your browser and navigate to:

```
http://localhost:8000
```

> **Screenshot Placeholder 6**
>
> **Description**: Browser showing the SnackBase login page with the login form centered on the screen.

---

## Step 2: Log In to the Admin UI

### 2.1 Enter Your Credentials

On the login page, enter:
- **Email**: The superadmin email you created
- **Password**: The superadmin password you created

Click **Sign In**.

> **Screenshot Placeholder 7**
>
> **Description**: Login page with credentials filled in and the cursor hovering over the Sign In button.

### 2.2 Welcome to the Dashboard

After logging in, you'll see the main dashboard with:
- Sidebar navigation on the left
- Statistics cards (collections, records, users, etc.)
- Recent activity or quick actions

> **Screenshot Placeholder 8**
>
> **Description**: The main Dashboard page showing statistics cards and the sidebar navigation menu.

---

## Step 3: Create Your First Collection

A **Collection** is like a table in a traditional database. It defines the structure of your data with fields and types.

### 3.1 Navigate to Collections

Click **Collections** in the sidebar.

> **Screenshot Placeholder 9**
>
> **Description**: Collections page showing an empty state or existing collections list with the "New Collection" button prominent.

### 3.2 Create a New Collection

Click the **+ New Collection** button.

A modal or form will appear. Enter:
- **Name**: `posts` (this will become the API endpoint: `/api/v1/posts`)
- **Description**: `Blog posts and articles` (optional)

Click **Create**.

> **Screenshot Placeholder 10**
>
> **Description**: The new collection creation modal with "posts" filled in as the name and a description added.

### 3.3 Add Fields to Your Collection

After creating the collection, you'll see the collection detail page. Now let's add fields.

Click **+ Add Field** and add the following fields:

| Field Name | Type | Required | Options |
|------------|------|----------|---------|
| `title` | Text | Yes | - |
| `content` | Text | No | Multi-line: Yes |
| `status` | Select | Yes | Options: `draft`, `published`, `archived` |
| `published_at` | Date | No | - |
| `views` | Number | No | Default: `0` |

> **Screenshot Placeholder 11**
>
> **Description**: Collection schema builder showing the `posts` collection with all 5 fields configured and their types visible.

> **Screenshot Placeholder 12**
>
> **Description**: Close-up of the "Add Field" form showing the field type dropdown with available options (text, number, email, boolean, date, JSON, select, relation).

---

## Step 4: Add Your First Records

Now that your collection is set up, let's add some data.

### 4.1 Navigate to Records

Click **Records** in the sidebar, then select the **posts** collection.

> **Screenshot Placeholder 13**
>
> **Description**: Records page showing the posts collection with an empty data table and "New Record" button.

### 4.2 Create a Record

Click **+ New Record**.

Fill in the form:
- **title**: `My First Blog Post`
- **content**: `This is my first post using SnackBase!`
- **status**: `published`
- **published_at**: Select today's date
- **views**: Leave as `0` (default)

Click **Save**.

> **Screenshot Placeholder 14**
>
> **Description**: The record creation form with all fields filled out for a blog post.

### 4.3 View Your Record

After saving, you'll see your record in the data table.

> **Screenshot Placeholder 15**
>
> **Description**: Records page showing the newly created "My First Blog Post" record in the data table.

### 4.4 Add More Records

Create a few more records to have some test data:
1. "Getting Started with SnackBase" (status: `published`)
2. "Draft Post About API Design" (status: `draft`)
3. "Archived Announcement" (status: `archived`)

> **Screenshot Placeholder 16**
>
> **Description**: Records page showing multiple blog post records with different status values visible in the table.

---

## Step 5: Set Up Roles and Permissions

SnackBase uses Role-Based Access Control (RBAC) to manage who can do what with your data.

### 5.1 Navigate to Roles

Click **Roles** in the sidebar.

> **Screenshot Placeholder 17**
>
> **Description**: Roles page showing the default "admin" role with the "New Role" button.

### 5.2 Understand Default Roles

By default, you'll see:
- **admin** - Full access to all collections and operations

The superadmin user you created has the `admin` role.

> **Screenshot Placeholder 18**
>
> **Description**: Role detail view for the "admin" role showing its permissions grid with all CRUD operations checked.

### 5.3 Create a New Role

Click **+ New Role**.

Enter:
- **Name**: `editor`
- **Description**: `Can create and edit posts, but cannot delete`

Click **Create**.

> **Screenshot Placeholder 19**
>
> **Description**: New role creation form with "editor" as the name and description filled in.

### 5.4 Configure Permissions

On the role detail page for `editor`:

1. Click **+ Add Permission**
2. Configure:
   - **Collection**: `posts`
   - **Create**: Enabled
   - **Read**: Enabled
   - **Update**: Enabled
   - **Delete**: Disabled

Click **Save**.

> **Screenshot Placeholder 20**
>
> **Description**: Permission configuration modal showing the editor role with Create, Read, Update checked, but Delete unchecked for the posts collection.

### 5.5 Create a Read-Only Role

Repeat the process to create a `viewer` role:
- **Name**: `viewer`
- **Collection**: `posts`
- **Read**: Enabled only

> **Screenshot Placeholder 21**
>
> **Description**: Roles list showing all three roles: admin (full access), editor (no delete), and viewer (read-only).

---

## Step 6: Create Additional Users

Now let's create users with different roles to test permissions.

### 6.1 Navigate to Users

Click **Users** in the sidebar.

> **Screenshot Placeholder 22**
>
> **Description**: Users page showing only the superadmin user and the "New User" button.

### 6.2 Create an Editor User

Click **+ New User**.

Enter:
- **Email**: `editor@example.com`
- **Password**: `EditorPass123!`
- **Role**: `editor`
- **Active**: Yes

Click **Create**.

> **Screenshot Placeholder 23**
>
> **Description**: New user creation form with editor account details filled in and the "editor" role selected from dropdown.

### 6.3 Create a Viewer User

Repeat to create a viewer user:
- **Email**: `viewer@example.com`
- **Password**: `ViewerPass123!`
- **Role**: `viewer`

> **Screenshot Placeholder 24**
>
> **Description**: Users page showing three users: the superadmin, editor, and viewer with their roles displayed.

---

## Step 7: Make Your First API Request

SnackBase automatically generates REST APIs for your collections. Let's test it!

### 7.1 Get Your Access Token

Open your browser's developer tools:
- Press `F12` or `Cmd+Option+I` (Mac)
- Go to the **Application** or **Storage** tab
- Find **Local Storage** → `http://localhost:8000`
- Copy the value of `access_token`

> **Screenshot Placeholder 25**
>
> **Description**: Browser DevTools showing Local Storage with the access_token value highlighted and copied.

### 7.2 Test the API with curl

Open a new terminal and try fetching all posts:

```bash
curl http://localhost:8000/api/v1/posts \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
  -H "Content-Type: application/json"
```

Replace `YOUR_ACCESS_TOKEN` with the token you copied.

> **Screenshot Placeholder 26**
>
> **Description**: Terminal showing the curl command and the JSON response with the posts data.

### 7.3 Create a Record via API

Create a new post using the API:

```bash
curl -X POST http://localhost:8000/api/v1/posts \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Created via API",
    "content": "This post was created using the REST API",
    "status": "published",
    "views": 0
  }'
```

> **Screenshot Placeholder 27**
>
> **Description**: Terminal showing the POST request and the successful response with the created record including its ID and timestamps.

### 7.4 Explore the Interactive API Docs

SnackBase includes auto-generated API documentation powered by Swagger UI.

Open in your browser:
```
http://localhost:8000/docs
```

> **Screenshot Placeholder 28**
>
> **Description**: Browser showing the Swagger UI page with all available endpoints listed, with the posts endpoints expanded.

> **Screenshot Placeholder 29**
>
> **Description**: Swagger UI showing the "Try it out" feature for the POST /api/v1/posts endpoint with the request body filled in.

---

## Step 8: Test Permissions

Let's verify that the permission system works correctly.

### 8.1 Log In as Editor

Open an incognito/private window and navigate to:
```
http://localhost:8000
```

Log in as `editor@example.com` with password `EditorPass123!`

> **Screenshot Placeholder 30**
>
> **Description**: Login page with editor credentials filled in, in an incognito window.

### 8.2 Verify Edit Capabilities

Navigate to **Records** → **posts**.

You should see:
- Edit buttons on existing records
- No Delete buttons (editor role cannot delete)

> **Screenshot Placeholder 31**
>
> **Description**: Records page as viewed by the editor user, showing Edit buttons but no Delete buttons in the action column.

### 8.3 Test Delete Restriction

Try to delete a record using the API with editor credentials:

```bash
curl -X DELETE http://localhost:8000/api/v1/posts/RECORD_ID \
  -H "Authorization: Bearer EDITOR_ACCESS_TOKEN"
```

You should receive a `403 Forbidden` error.

> **Screenshot Placeholder 32**
>
> **Description**: Terminal showing the DELETE request returning a 403 Forbidden error with a permission denied message.

---

## Common Gotchas & Tips

### Gotcha 1: Account Context in API Requests

When making API requests, your user is always associated with an **account**. All data is isolated by `account_id`, even if you're using a single account setup.

**Solution**: Be aware that filtering by account happens automatically. You don't need to specify `account_id` in your queries.

> **Screenshot Placeholder 33**
>
> **Description**: API response showing the account_id field in each record, illustrating automatic account isolation.

### Gotcha 2: Collection Names Become URL Endpoints

The collection name you choose becomes part of the API URL:
- Collection `blog-posts` → `/api/v1/blog-posts`
- Collection `posts` → `/api/v1/posts`

**Solution**: Use simple, URL-friendly names with lowercase letters, numbers, and hyphens.

> **Screenshot Placeholder 34**
>
> **Description**: Collections page showing how collection names map to their API endpoints in a dedicated column.

### Gotcha 3: Built-in Hooks Auto-Set Timestamps

Every record automatically gets `created_at` and `updated_at` timestamps. You don't need to add these as fields.

**Solution**: Don't create manual timestamp fields—they're built-in!

> **Screenshot Placeholder 35**
>
> **Description**: Record detail view or API response showing the auto-generated created_at and updated_at fields.

### Gotcha 4: Superadmin vs Admin

| Aspect | Superadmin | Admin (role) |
|--------|-----------|--------------|
| Account | `system` (SY0000) | Any account |
| Access | All accounts | Single account |

**Solution**: Use superadmin only for system-level operations. Use admin roles for day-to-day account management.

> **Screenshot Placeholder 36**
>
> **Description**: Dashboard showing a visual indicator or badge distinguishing superadmin users from regular admin users.

### Gotcha 5: Permission Caching

Permissions are cached for 5 minutes. If you change a role's permissions, it may take up to 5 minutes to take effect.

**Solution**: Wait 5 minutes or restart the server after permission changes for immediate effect.

> **Screenshot Placeholder 37**
>
> **Description**: A diagram or illustration showing the permission cache flow with TTL indicator.

---

## Next Steps

Congratulations! You've completed the SnackBase Quick Start. Here's what to explore next:

### Learn More
- **[Architecture Guide](./architecture.md)** - Understand how SnackBase works under the hood
- **[Hooks System](./hooks.md)** - Automate workflows with event-driven hooks
- **[Permissions](./permissions.md)** - Advanced permission rules and expressions
- **[API Examples](./api-examples.md)** - Comprehensive API usage examples

### Build Something
- Create a blog with public posts and admin-only drafts
- Build a product catalog with categories and inventory
- Design a task management system with assignees and status

### Contribute
- **[Contributing Guide](../CONTRIBUTING.md)** - Learn how to contribute to SnackBase
- Report bugs on GitHub Issues
- Suggest features on GitHub Discussions

---

## Need Help?

- **Documentation**: Check the [docs folder](./)
- **GitHub Issues**: Report bugs or request features
- **API Docs**: Visit `/docs` endpoint for interactive API documentation
- **Health Check**: Visit `/health` to verify your instance is running

---

**Enjoy building with SnackBase! 🚀**
