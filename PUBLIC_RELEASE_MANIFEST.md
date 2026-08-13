# 天枢 TenSpur 公开发布范围

天枢 TenSpur — 企业产品库。面向企业的产品资料管理、分类检索、产品对比与辅助选型平台，支持软件、硬件及其他产品类型的统一管理。

| Live area | Public treatment |
|---|---|
| Backend app, Alembic, tests | Included, readable text sanitized |
| Frontend src/tests/config | Included, organization image assets removed |
| Compose/Nginx/env | Replaced with generic examples |
| Production `.git`, `.env`, certs | Excluded |
| DB/dumps/backups/input/import evidence | Excluded |
| PDFs, media, screenshots, logos, built/dependency trees | Excluded |

| TianCang product-document submodule | Source, tests, bundled PDF.js and generic Docker/Compose included; runtime PDF volume is empty; no real PDFs/data/endpoints/credentials included |
