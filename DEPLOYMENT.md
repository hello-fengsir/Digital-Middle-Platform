# 天枢 TenSpur 部署指南

天枢 TenSpur — 企业产品库。面向企业的产品资料管理、分类检索、产品对比与辅助选型平台，支持软件、硬件及其他产品类型的统一管理。

Use a dedicated `.env`, strong generated secrets, private database network, persistent database volume, HTTPS reverse proxy and regular encrypted backups. Validate with `docker compose config`, build both images, apply Alembic migrations in a controlled window, then test health, anonymous access, admin authentication, CRUD and restore rehearsal. Do not expose PostgreSQL publicly.
