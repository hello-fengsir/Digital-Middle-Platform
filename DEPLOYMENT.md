# 天枢 TenSpur 部署指南

天枢 TenSpur — 硬件产品资料与选型平台。

Use a dedicated `.env`, strong generated secrets, private database network, persistent database volume, HTTPS reverse proxy and regular encrypted backups. Validate with `docker compose config`, build both images, apply Alembic migrations in a controlled window, then test health, anonymous access, admin authentication, CRUD and restore rehearsal. Do not expose PostgreSQL publicly.
