# SnackBase Documentation

Welcome to the SnackBase documentation! This directory contains comprehensive guides for deploying, using, and extending SnackBase.

---

## Quick Links

- ⚡ [Quick Start Tutorial](quick-start.md) - Get up and running in 5 minutes
- 📚 [Deployment Guide](deployment.md) - Deploy SnackBase in development and production
- 🎨 [Frontend Guide](frontend.md) - React admin UI development
- 🧠 [Conceptual Guides](concepts/) - Deep dives into core concepts
- 🔌 [Hook System](hooks.md) - Extend SnackBase with custom hooks
- 🚀 [API Examples](api-examples.md) - Practical API usage examples
- 📖 [API Reference](http://localhost:8000/docs) - Interactive Swagger documentation

---

## Documentation Overview

### Getting Started

1. **[Quick Start Tutorial](quick-start.md)**
   - 5-minute hands-on setup walkthrough
   - Create your first collection via UI
   - Add records and test the API
   - Set up roles and permissions
   - Common gotchas for new users

2. **[Conceptual Guides](concepts/)** - NEW!
   - **[Multi-Tenancy Model](concepts/multi-tenancy.md)** - Account isolation, two-tier architecture
   - **[Collections Model](concepts/collections.md)** - Dynamic schemas and table generation
   - **[Authentication Model](concepts/authentication.md)** - Auth flows and token management
   - **[Security Model](concepts/security.md)** - RBAC, permissions, and rule engine

3. **[Deployment Guide](deployment.md)**

   - Development setup
   - Production deployment with systemd
   - Nginx reverse proxy configuration
   - PostgreSQL setup
   - Environment variables
   - Health checks
   - Troubleshooting

2. **[Frontend Guide](frontend.md)**
   - React admin UI architecture
   - State management (Zustand, TanStack Query)
   - Component patterns (ShadCN)
   - Authentication flow
   - Adding new pages
   - Styling with TailwindCSS
   - Development workflow

4. **[API Examples](api-examples.md)**
   - Authentication (register, login, refresh)
   - Collections (create dynamic schemas)
   - Records (CRUD operations)
   - Invitations (user management)
   - Error handling
   - Best practices

### Advanced Topics

5. **[Hook System](hooks.md)**
   - Stable API contract
   - Architecture overview
   - Hook categories and events
   - Built-in hooks (timestamp, account_isolation, created_by)
   - Creating custom hooks
   - Advanced features (priority, filtering, aborting)
   - Best practices

### Reference

6. **[API Reference (Swagger)](http://localhost:8000/docs)**

   - Interactive API documentation
   - Try endpoints directly from browser
   - Request/response schemas
   - Authentication testing

7. **[PRD & Requirements](../PRD_PHASES.md)**
   - Phase-by-phase development plan
   - Feature specifications
   - Acceptance criteria
   - Testing requirements

---

## Documentation by Role

### For Developers

- **Getting Started**: [Quick Start Tutorial](quick-start.md)
- **Core Concepts**: [Conceptual Guides](concepts/)
- **Frontend Development**: [Frontend Guide](frontend.md)
- **API Usage**: [API Examples](api-examples.md)
- **Extending SnackBase**: [Hook System](hooks.md)
- **Testing**: [API Reference](http://localhost:8000/docs)

### For DevOps/SRE

- **Production Deployment**: [Deployment Guide](deployment.md) → Production Deployment
- **Monitoring**: [Deployment Guide](deployment.md) → Health Checks
- **Troubleshooting**: [Deployment Guide](deployment.md) → Troubleshooting
- **Security**: [Deployment Guide](deployment.md) → Security Best Practices

### For API Consumers

- **Authentication**: [API Examples](api-examples.md) → Authentication
- **CRUD Operations**: [API Examples](api-examples.md) → Records
- **Error Handling**: [API Examples](api-examples.md) → Error Handling
- **Interactive Testing**: [API Reference](http://localhost:8000/docs)

### For Plugin Developers

- **Hook System**: [Hook System](hooks.md)
- **Stable API Contract**: [Hook System](hooks.md) → Stable API Contract
- **Custom Hooks**: [Hook System](hooks.md) → Creating Custom Hooks
- **Best Practices**: [Hook System](hooks.md) → Best Practices

---

## Quick Start Guides

### 5-Minute Quickstart

```bash
# 1. Clone and install
git clone <repository-url>
cd SnackBase
uv sync

# 2. Start server
uv run python -m snackbase serve --reload

# 3. Open Swagger UI
open http://localhost:8000/docs

# 4. Register account
curl -X POST http://localhost:8000/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "account_name": "My Company",
    "email": "admin@example.com",
    "password": "SecurePass123!"
  }'
```

See [Deployment Guide](deployment.md) for detailed setup.

### Production Deployment Checklist

- [ ] Set strong `SNACKBASE_SECRET_KEY`
- [ ] Use PostgreSQL database
- [ ] Set `SNACKBASE_ENVIRONMENT=production`
- [ ] Configure proper CORS origins
- [ ] Set up Nginx reverse proxy
- [ ] Enable HTTPS/TLS
- [ ] Configure systemd service
- [ ] Set up log aggregation
- [ ] Configure automated backups
- [ ] Test health check endpoints

See [Deployment Guide](deployment.md) → Production Deployment for details.

---

## Documentation Standards

All SnackBase documentation follows these standards:

- **Markdown Format**: GitHub-flavored markdown
- **Code Examples**: Practical, runnable examples
- **Versioning**: Documentation version matches SnackBase version
- **Stability**: Breaking changes only in major versions

---

## Contributing to Documentation

Found an error or want to improve the docs?

1. **Report Issues**: [GitHub Issues](repository-url/issues)
2. **Submit PRs**: Documentation improvements are always welcome
3. **Ask Questions**: [Community Forum](community-url)

---

## Version Information

| Document         | Version | Last Updated |
| ---------------- | ------- | ------------ |
| Deployment Guide | 1.0     | 2025-12-24   |
| Hook System      | 1.0     | 2025-12-24   |
| API Examples     | 1.0     | 2025-12-24   |

---

## Additional Resources

- **GitHub Repository**: [repository-url]
- **Community Forum**: [community-url]
- **Issue Tracker**: [repository-url/issues]
- **Changelog**: [repository-url/CHANGELOG.md]

---

## License

SnackBase documentation is licensed under [LICENSE].

---

## Support

Need help?

- 📖 Read the documentation
- 💬 Ask in the community forum
- 🐛 Report bugs on GitHub
- 📧 Contact support (enterprise)
