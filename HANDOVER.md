# 天枢 TenSpur 公开交接说明

天枢 TenSpur — 企业产品库。面向企业的产品资料管理、分类检索、产品对比与辅助选型平台，支持软件、硬件及其他产品类型的统一管理。

This is a source-only sanitized release. Included: application source, schema migrations, tests, Dockerfiles and generic deployment examples. Excluded: Git history from production, environment files, certificates, databases/dumps, backups, imports, PDFs/media, logos/screenshots, production endpoints and credentials. The private recovery package is maintained separately and must never be merged into this tree.

## 天仓 TianCang 交接边界

公开源码新增 `tiancang/` 产品文档管理子模块及通用 Docker/Compose 配置，但不附带真实材料。资料卷默认空；数据库、PDF、客户数据、内部 IP/域名与凭据均不在公开交付范围。接手方须自行生成凭据并仅导入有权使用的文档。Viewer 的确定性返回契约固定为：`return` → 同源 `/` referrer → `/` fallback，目标必须同源且 pathname 严格为 `/`，最终调用 `location.assign()`；禁止 `history.back()` 与开放重定向。360/390 工具栏采用自有覆盖层分行，不改写 PDF.js 上游核心。
