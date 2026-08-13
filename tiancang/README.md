# 天仓 TianCang

天仓是天枢 TenSpur 企业产品库的**产品文档管理子模块**，提供受认证的 PDF/目录管理和匿名公开阅读能力。

## 功能范围

- 管理员 Cookie 认证；目录与 PDF 清单 API。
- PDF 上传、新建目录、删除 PDF、删除空目录。
- 匿名公开 PDF（`application/pdf`）与内置 PDF.js 在线预览（缩放、旋转、确定性返回天仓目录）。
- 移动端/PC 响应式布局和服务端路径越界防护。
- 独立 Docker 服务、健康检查和持久化资料卷。

## 公开边界

源码**不包含任何真实产品材料、生产数据、客户信息、内部 IP/域名或凭据**。`/data/pdfs` 默认空；部署者只能导入已获授权的资料。PDF.js 按 Apache-2.0 使用，详见 `PDFJS-LICENSE.txt`。

## 运行

由仓库根目录 Compose 启动。必须在 `.env` 设置强随机 `TIANCANG_ADMIN_PASSWORD` 和 `TIANCANG_SESSION_SECRET`。资料卷挂载到 `/data/pdfs`。


## Viewer 返回契约

从天仓管理目录打开 PDF（包括 `target=_blank` 新标签）后，Viewer 的“返回天仓目录”按钮必须回到同源管理目录 `/`。Viewer 优先读取 `return` 参数，其次读取 `document.referrer`，但仅接受与当前 Viewer 同源且路径严格为 `/` 的目标；任何跨源、协议相对、其他本源路径或不可解析值均拒绝并回退 `/`。实现不得依赖 `history.back()`，也不得形成 open redirect。
