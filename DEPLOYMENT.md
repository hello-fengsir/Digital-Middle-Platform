# 天枢 TenSpur 部署指南

天枢 TenSpur — 企业产品库。面向企业的产品资料管理、分类检索、产品对比与辅助选型平台，支持软件、硬件及其他产品类型的统一管理。

Use a dedicated `.env`, strong generated secrets, private database network, persistent database volume, HTTPS reverse proxy and regular encrypted backups. Validate with `docker compose config`, build both images, apply Alembic migrations in a controlled window, then test health, anonymous access, admin authentication, CRUD and restore rehearsal. Do not expose PostgreSQL publicly.

## 天仓 TianCang

天仓是企业产品库的产品文档管理子模块。Compose 中 `tiancang` 使用独立命名卷 `tiancang-pdfs`（默认空）并默认映射 `8087`。部署前必须设置强随机 `TIANCANG_ADMIN_PASSWORD`、`TIANCANG_SESSION_SECRET`，并通过 HTTPS 反向代理发布；只导入已获授权的 PDF。验证健康、匿名管理 302/401、登录、目录/上传/删除、公开 PDF 与 PDF.js 后再开放访问。Viewer 返回 URL 必须携带编码后的 `return=/`；服务只接受同源且路径严格为 `/` 的目标，其他输入回退 `/`，点击后使用 `location.assign()`，不得改成历史栈返回。验收后确认卷内 PDF 数量为 0，再导入获授权材料。
