# Product Hub

A generic full-stack hardware product catalog and selection platform. It provides public catalog browsing/comparison, an authenticated administration console, schema migrations, import workflows and optional OpenAI-compatible assistance.

## Stack
Vue 3 + TypeScript + Vite, FastAPI + SQLAlchemy + Alembic, PostgreSQL 16, Nginx and Docker Compose.

## Quick start
1. Copy `.env.example` to `.env` and replace every placeholder.
2. Run `docker compose config` and review the effective settings.
3. Run `docker compose up --build -d`.
4. Open `http://localhost:8080`; verify the API and change the initial administrator credentials.

This public repository intentionally contains no production database, backups, documents, media, certificates, logos, environment file or deployment endpoints. See [DEPLOYMENT.md](DEPLOYMENT.md), [SECURITY.md](SECURITY.md), [PRIVACY.md](PRIVACY.md), [HANDOVER.md](HANDOVER.md) and [CHANGELOG.md](CHANGELOG.md).
