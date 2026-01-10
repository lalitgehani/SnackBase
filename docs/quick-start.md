# Quick Start Guide

Get up and running with SnackBase in 5 minutes. This guide will walk you through the essential steps to set up your instance, create your first collection, add data, set up permissions, and make API requests.

---

## Prerequisites

Before you begin, ensure you have:

- **Python 3.12+** installed
- **Node.js 18+** installed (for the admin UI)
- **uv** package manager installed
  - **macOS/Linux**: `curl -LsSf https://astral.sh/uv/install.sh | sh`
  - **Windows**: `powershell -c "irm https://astral.sh/uv/install.ps1 | iex"`
- **Git** installed (for cloning the repository)

> **Windows Users**: If you don't have Node.js installed, download it from [nodejs.org](https://nodejs.org/). For Python, use the [Microsoft Store](https://apps.microsoft.com/store/detail/python-3-12/9NRWMJP3717K) or [python.org](https://www.python.org/downloads/).

---

## Step 1: Install and Start SnackBase

### 1.1 Clone the Repository

```bash
git clone https://github.com/yourusername/snackbase.git
cd SnackBase
```

### 1.2 Install Backend Dependencies

SnackBase uses `uv` for fast, reliable package management:

```bash
uv sync
```

> **Screenshot Placeholder 1**
>
> **Description**: Terminal window showing the `uv sync` command completing successfully. Should show installed packages and a success message.

### 1.3 Install Frontend Dependencies

Navigate to the UI directory and install Node.js dependencies:

```bash
cd ui
npm install
cd ..
```

> **Screenshot Placeholder 1b**
>
> **Description**: Terminal showing npm install completing with UI dependencies.

### 1.4 Configure Environment

Create a `.env` file from the example template:

```bash
cp .env.example .env
```

For local development, the default values work fine. However, for production, update at minimum:
- `SNACKBASE_SECRET_KEY` - Generate a secure random string
- `SNACKBASE_DATABASE_URL` - Switch to PostgreSQL
- `SNACKBASE_CORS_ORIGINS` - Add your frontend URL

> **Screenshot Placeholder 2**
>
> **Description**: Text editor showing the `.env` file with key environment variables highlighted.

### 1.5 Initialize the Database

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

### 1.6 Configure Email (Optional but Recommended)

SnackBase requires email configuration for user email verification. Choose one of these options:

**Option A: Use a Development SMTP Server (Recommended for Testing)**

```bash
# Install MailHog for local email testing
# macOS
brew install mailhog

# Start MailHog
mailhog
```

Then update your `.env`:
```bash
# For MailHog (localhost:1025)
EMAIL_PROVIDER=smtp
SMTP_HOST=localhost
SMTP_PORT=1025
SMTP_USER=
SMTP_PASSWORD=
SMTP_FROM=noreply@snackbase.local
```

**Option B: Use Resend (Recommended for Production)**

Sign up at [resend.com](https://resend.com) and get an API key:
```bash
EMAIL_PROVIDER=resend
RESEND_API_KEY=re_xxxxxxxxxxxxx
EMAIL_FROM=noreply@yourdomain.com
```

**Option C: Use AWS SES**

```bash
EMAIL_PROVIDER=aws_ses
AWS_SES_REGION=us-east-1
AWS_ACCESS_KEY_ID=your_key
AWS_SECRET_ACCESS_KEY=your_secret
EMAIL_FROM=noreply@yourdomain.com
```

> **Screenshot Placeholder 3b**
>
> **Description**: Text editor showing email configuration in the `.env` file.

### 1.7 Create a Superadmin User

```bash
uv run python -m snackbase create-superadmin
```

You'll be prompted to enter:
- Email address (e.g., `admin@example.com`)
- Password (minimum 8 characters, recommended: mix of letters, numbers, symbols)
- Password confirmation

> **Note**: The superadmin account will require email verification if email is configured. You can verify the email via the API or auto-verify superadmin emails in development mode.

> **Screenshot Placeholder 4**
>
> **Description**: Terminal showing the interactive superadmin creation prompt with filled-in values and success message.

### 1.8 Start the Backend Server

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

### 1.9 Start the Frontend (New Terminal)

Open a new terminal and start the React development server:

```bash
cd ui
npm run dev
```

You should see:
```
VITE v7.x.x ready in xxx ms
➜  Local:   http://localhost:5173/
```

> **Screenshot Placeholder 5b**
>
> **Description**: Terminal showing the Vite dev server starting with the local URL.

### 1.10 Access the Admin UI

Open your browser and navigate to:

```
http://localhost:5173
```

> **Screenshot Placeholder 6**
>
> **Description**: Browser showing the SnackBase login page with the login form centered on the screen.

---

## Step 2: Log In to the Admin UI

### 2.1 Enter Your Credentials

On the login page, enter:
- **Account**: `system` (or `SY0000`)
- **Email**: The superadmin email you created
- **Password**: The superadmin password you created

Click **Sign In**.

> **Important**: The superadmin account is always linked to the `system` account (ID: `SY0000`). Use "system" as the account field when logging in.

> **Screenshot Placeholder 7**
>
> **Description**: Login page with credentials filled in and the cursor hovering over the Sign In button.

### 2.2 Verify Your Email (If Required)

If email verification is enabled, you'll see a message asking you to verify your email.

**For Development with MailHog:**
1. Open `http://localhost:8025` in your browser
2. Find the verification email
3. Click the verification link

**To Skip Verification in Development:**
Use the admin API to verify your email:
```bash
# Get your access token first, then:
curl -X POST http://localhost:8000/api/v1/admin/verify-email \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"email": "admin@example.com"}'
```

> **Screenshot Placeholder 7b**
>
> **Description**: MailHog interface showing the verification email with the verification link highlighted.

### 2.3 Welcome to the Dashboard

After logging in (and verifying your email if required), you'll see the main dashboard with:
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
- **Name**: `posts` (this will become the API endpoint: `/api/v1/records/posts`)
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
- Find **Local Storage** → `http://localhost:5173`
- Copy the value of `access_token`

> **Screenshot Placeholder 25**
>
> **Description**: Browser DevTools showing Local Storage with the access_token value highlighted and copied.

### 7.2 Test the API with curl

Open a new terminal and try fetching all posts:

```bash
curl http://localhost:8000/api/v1/records/posts \
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
curl -X POST http://localhost:8000/api/v1/records/posts \
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
> **Description**: Swagger UI showing the "Try it out" feature for the POST /api/v1/records/posts endpoint with the request body filled in.

---

## Step 8: Test Permissions

Let's verify that the permission system works correctly.

### 8.1 Log In as Editor

Open an incognito/private window and navigate to:
```
http://localhost:5173
```

Log in as:
- **Account**: `system`
- **Email**: `editor@example.com`
- **Password**: `EditorPass123!`

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
curl -X DELETE http://localhost:8000/api/v1/records/posts/RECORD_ID \
  -H "Authorization: Bearer EDITOR_ACCESS_TOKEN"
```

You should receive a `403 Forbidden` error.

> **Screenshot Placeholder 32**
>
> **Description**: Terminal showing the DELETE request returning a 403 Forbidden error with a permission denied message.

---

## Development Commands

### Backend Commands

```bash
# Server management
uv run python -m snackbase serve          # Start server (0.0.0.0:8000)
uv run python -m snackbase serve --reload # Dev mode with auto-reload
uv run python -m snackbase info           # Show configuration

# Database
uv run python -m snackbase init-db        # Initialize database (dev only)
uv run python -m snackbase create-superadmin  # Create superadmin user

# Interactive shell
uv run python -m snackbase shell          # IPython REPL with pre-loaded context

# Code quality
uv run ruff check .                        # Lint
uv run ruff format .                       # Format
uv run mypy src/                           # Type check

# Testing
uv run pytest                              # Run all tests
uv run pytest tests/unit/                  # Unit tests only
uv run pytest tests/integration/           # Integration tests only
uv run pytest --cov=snackbase              # With coverage
uv run pytest -k "test_name"               # Run specific test
```

### Frontend Commands

```bash
cd ui
npm run dev        # Start dev server (Vite)
npm run build      # Production build
npm run lint       # ESLint
npm run preview    # Preview production build
```

---

## Troubleshooting

### Database Errors

**Problem**: `sqlite3.OperationalError: unable to open database file`

**Solution**: Ensure the `sb_data` directory exists and is writable:
```bash
mkdir -p sb_data
chmod 755 sb_data
```

**Windows**: Create the folder manually in File Explorer if needed.

### Port Conflicts

**Problem**: `Error: listen tcp 0.0.0.0:8000: bind: address already in use`

**Solution**: Another process is using port 8000. Find and stop it:

**macOS/Linux**:
```bash
# Find the process
lsof -ti:8000 | xargs kill -9
```

**Windows**:
```cmd
# Find the process
netstat -ano | findstr :8000
# Kill the process (replace PID with the actual process ID)
taskkill /PID PID /F
```

Alternatively, change the port in `.env`:
```bash
SNACKBASE_PORT=8001
```

### Permission Issues

**Problem**: Permission denied errors when running commands

**Solution**: Ensure you have the correct permissions:

**macOS/Linux**:
```bash
# Fix directory permissions
chmod -R 755 .
```

**Windows**: Run your terminal as Administrator:
1. Right-click Command Prompt or PowerShell
2. Select "Run as administrator"

### Email Verification Problems

**Problem**: Users can't log in due to unverified email

**Solution**: Manually verify the user via API:
```bash
curl -X POST http://localhost:8000/api/v1/admin/verify-email \
  -H "Authorization: Bearer YOUR_SUPERADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"email": "user@example.com"}'
```

**Problem**: Verification emails not being sent

**Solution**: Check your email configuration:
1. Verify email settings in `.env`
2. If using MailHog, ensure it's running (`mailhog` command)
3. Check server logs for email errors: `tail -f logs/snackbase.log`

### UV Installation Issues

**Problem**: `uv: command not found`

**Solution**: Ensure uv is installed and in your PATH:

**macOS/Linux**:
```bash
# Reinstall uv
curl -LsSf https://astral.sh/uv/install.sh | sh

# Add to PATH (add to ~/.bashrc or ~/.zshrc)
export PATH="$HOME/.cargo/bin:$PATH"
```

**Windows**:
```powershell
# Reinstall uv
powershell -c "irm https://astral.sh/uv/install.ps1 | iex"

# Restart your terminal
```

### Node.js/npm Issues

**Problem**: `npm: command not found`

**Solution**: Install Node.js:
- **macOS**: `brew install node`
- **Windows**: Download from [nodejs.org](https://nodejs.org/)
- **Linux**: `sudo apt install nodejs npm` (Debian/Ubuntu)

**Problem**: `Cannot find module 'vite'`

**Solution**: Install dependencies:
```bash
cd ui
npm install
```

### Windows-Specific Notes

1. **Path Separators**: Windows uses backslashes (`\`) but commands in this doc use forward slashes (`/`). Most tools accept both.

2. **Terminal**: Use PowerShell or Git Bash for best compatibility with the commands in this guide.

3. **Database Locking**: SQLite can have issues on Windows with multiple processes. If you see "database is locked" errors:
   - Stop the server before running tests
   - Use `uv run python -m snackbase init-db` before starting the server

4. **Long Paths**: Windows has a 260 character path limit. If you encounter path-related errors:
   - Move the project closer to the drive root (e.g., `C:\projects\SnackBase`)
   - Enable long path support in Windows 10/11 (requires registry change)

---

## API Endpoints Reference

SnackBase provides 20+ API routers:

| Router | Endpoints | Description |
|--------|-----------|-------------|
| `/api/v1/auth` | Login, register, refresh, me | Authentication |
| `/api/v1/auth/oauth` | OAuth flow (Google, GitHub, etc.) | OAuth authentication |
| `/api/v1/auth/saml` | SAML SSO flow | SAML authentication |
| `/api/v1/accounts` | CRUD operations | Account management |
| `/api/v1/collections` | CRUD operations | Collection management |
| `/api/v1/records/{collection}` | CRUD operations | Dynamic collection records |
| `/api/v1/users` | CRUD operations | User management |
| `/api/v1/roles` | CRUD, permissions | Role management |
| `/api/v1/permissions` | CRUD operations | Permission management |
| `/api/v1/macros` | CRUD, execute | SQL macro management |
| `/api/v1/groups` | CRUD operations | Group management |
| `/api/v1/invitations` | Create, accept | User invitations |
| `/api/v1/dashboard` | Statistics | Dashboard data |
| `/api/v1/audit-logs` | List, export, filter | Audit log retrieval |
| `/api/v1/migrations` | Status, history | Alembic migration status |
| `/api/v1/files` | Upload, download, delete | File management |
| `/api/v1/admin` | System configuration | Admin controls |
| `/api/v1/admin/email` | Email templates, settings | Email management |

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
- Collection `blog-posts` → `/api/v1/records/blog-posts`
- Collection `posts` → `/api/v1/records/posts`

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

### Gotcha 6: Email Verification Required

New users must verify their email before logging in (if email is configured).

**Solution**:
- **Development**: Use MailHog to catch verification emails locally
- **Testing**: Use the admin API to manually verify users
- **Production**: Ensure your email provider is properly configured

---

## Production Considerations

Before deploying to production, review these important security and configuration items:

### Security Settings

```bash
# Generate a secure secret key
python -c "import secrets; print(secrets.token_urlsafe(32))"

# Update .env with secure values
SNACKBASE_SECRET_KEY=your_generated_secret_key_here
```

### Database Setup

For production, switch from SQLite to PostgreSQL:

```bash
# Install PostgreSQL
# macOS
brew install postgresql

# Ubuntu/Debian
sudo apt install postgresql postgresql-contrib

# Update .env
SNACKBASE_DATABASE_URL=postgresql+asyncpg://user:password@localhost/snackbase
```

### Environment Variables

Key production environment variables:

```bash
# Required
SNACKBASE_SECRET_KEY=<generate with secrets.token_urlsafe(32)>
SNACKBASE_DATABASE_URL=postgresql+asyncpg://...

# Recommended
SNACKBASE_ENVIRONMENT=production
SNACKBASE_DEBUG=false
SNACKBASE_CORS_ORIGINS=https://yourdomain.com

# Email Configuration
EMAIL_PROVIDER=smtp  # or resend, aws_ses
SMTP_HOST=smtp.yourprovider.com
SMTP_PORT=587
SMTP_USER=your_email
SMTP_PASSWORD=your_password
SMTP_FROM=noreply@yourdomain.com
```

### HTTPS/SSL

Always use HTTPS in production:
- Use a reverse proxy (nginx, Caddy)
- Configure SSL certificates (Let's Encrypt)
- Update CORS origins to include HTTPS URLs

---

## Next Steps

Congratulations! You've completed the SnackBase Quick Start. Here's what to explore next:

### Learn More
- **[Architecture Guide](./concepts/architecture.md)** - Understand how SnackBase works under the hood
- **[Authentication Model](./concepts/authentication.md)** - Deep dive into auth, multi-account users, and tokens
- **[Multi-Tenancy Model](./concepts/multi-tenancy.md)** - How accounts and data isolation work
- **[Hooks System](./concepts/hooks.md)** - Automate workflows with event-driven hooks
- **[Permissions](./concepts/permissions.md)** - Advanced permission rules and expressions
- **[API Reference](./api-reference.md)** - Complete API documentation

### Build Something
- Create a blog with public posts and admin-only drafts
- Build a product catalog with categories and inventory
- Design a task management system with assignees and status
- Implement a multi-tenant SaaS application

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
- **Ready Check**: Visit `/ready` to verify database connectivity

---

**Enjoy building with SnackBase!**
