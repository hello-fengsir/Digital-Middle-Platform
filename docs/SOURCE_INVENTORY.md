# Product Hub public 源码机器清单

- 扫描根：`tenspur-public-release-final-work-20260813/`（不记录绝对部署路径）
- 统计：`{"source_files": 112, "python_files": 39, "ts_files": 25, "vue_files": 18, "routes": 42, "components": 18, "migrations": 12, "compose_services": 3}`

## 完整受检源码文件树
```text
CHANGELOG.md
DEPLOYMENT.md
HANDOVER.md
PRIVACY.md
PUBLIC_RELEASE_MANIFEST.md
README.md
SECURITY.md
SENSITIVE_SCAN.json
backend/Dockerfile
backend/alembic.ini
backend/alembic/env.py
backend/alembic/versions/0001_initial_schema.py
backend/alembic/versions/0002_cpu_compatibility.py
backend/alembic/versions/0003_gpu_slot_cooling.py
backend/alembic/versions/0004_ai_config_compatible_gpu.py
backend/alembic/versions/0005_gpu_relation_constraints_acceptance_cleanup.py
backend/alembic/versions/0006_gpu_parent_guard_import_trim_whitepaper.py
backend/alembic/versions/0007_nf5468a7_cross_platform_cleanup.py
backend/alembic/versions/0008_nf5468a7_cn_cpu_notes_cleanup.py
backend/alembic/versions/0009_controlled_lifecycle_tags.py
backend/alembic/versions/0010_field_dictionary_guard.py
backend/alembic/versions/0011_merge_auto_field_definitions.py
backend/alembic/versions/0012_normalize_interface_fields.py
backend/app/__init__.py
backend/app/ai_agent_rule.py
backend/app/ai_service.py
backend/app/catalog.py
backend/app/config.py
backend/app/db.py
backend/app/importer.py
backend/app/main.py
backend/app/model_matching.py
backend/app/models.py
backend/app/routes/__init__.py
backend/app/routes/admin.py
backend/app/routes/public.py
backend/app/schemas.py
backend/app/security.py
backend/entrypoint.sh
backend/pyproject.toml
backend/tests/test_ai_agent_rule.py
backend/tests/test_ai_input_contract.py
backend/tests/test_ai_numeric_constraints.py
backend/tests/test_api.py
backend/tests/test_field_dictionary_governance.py
backend/tests/test_gpu_constraints_cleanup.py
backend/tests/test_lifecycle_migration_contract.py
backend/tests/test_public_schema_only_migrations.py
backend/tests/test_validation_error_redaction.py
docker-compose.yml
docs/DEVELOPER_GUIDE.md
docs/SOURCE_INVENTORY.json
docs/SOURCE_INVENTORY.md
frontend/Dockerfile
frontend/index.html
frontend/nginx.conf
frontend/package-lock.json
frontend/package.json
frontend/src/App.vue
frontend/src/admin/AdminApp.test.ts
frontend/src/admin/AdminApp.vue
frontend/src/admin/admin-components.css
frontend/src/admin/admin.css
frontend/src/admin/adminAiAgentRuleApi.test.ts
frontend/src/admin/adminApi.test.ts
frontend/src/admin/adminApi.ts
frontend/src/admin/components/AdminAiAgentRulePanel.test.ts
frontend/src/admin/components/AdminAiAgentRulePanel.vue
frontend/src/admin/components/AdminAiConfigPanel.test.ts
frontend/src/admin/components/AdminAiConfigPanel.vue
frontend/src/admin/components/AdminBasicForm.vue
frontend/src/admin/components/AdminCompatibleGpuPanel.test.ts
frontend/src/admin/components/AdminCompatibleGpuPanel.vue
frontend/src/admin/components/AdminImportPanel.test.ts
frontend/src/admin/components/AdminImportPanel.vue
frontend/src/admin/components/AdminModelList.vue
frontend/src/admin/components/AdminRecognitionPanel.vue
frontend/src/admin/components/AdminSpecEditor.vue
frontend/src/admin/components/SeriesSelector.vue
frontend/src/admin/components/SpecRows.vue
frontend/src/api.ts
frontend/src/components/AiAssistant.vue
frontend/src/components/BrandHeader.vue
frontend/src/components/ModelDetail.vue
frontend/src/components/ModelNavigator.vue
frontend/src/components/ProductBadges.vue
frontend/src/components/ProductCompare.vue
frontend/src/env.d.ts
frontend/src/main.ts
frontend/src/style.css
frontend/src/styles/compare.css
frontend/src/styles/mobile-public.css
frontend/src/styles/mobile-scroll-admin.css
frontend/src/utils/adminRedirect.test.ts
frontend/src/utils/adminRedirect.ts
frontend/src/utils/aiRecommendation.test.ts
frontend/src/utils/aiRecommendation.ts
frontend/src/utils/catalogLoader.test.ts
frontend/src/utils/catalogLoader.ts
frontend/src/utils/displayRules.ts
frontend/src/utils/gpuDisplay.test.ts
frontend/src/utils/gpuDisplay.ts
frontend/src/utils/homeUx.test.ts
frontend/src/utils/productBadges.test.ts
frontend/src/utils/productBadges.ts
frontend/tests/api-error.test.ts
frontend/tests/gpu-display-browser.mjs
frontend/tests/gpu-save-browser.mjs
frontend/tsconfig.json
frontend/vite.config.ts
tools/tenspur_source_inventory.py
tools/verify_handover_docs.py
```

## FastAPI 路由
- `POST /api/v1/admin/auth/login` → `backend/app/routes/admin.py::admin_login()`；依赖：`未在装饰器声明`
- `GET /api/v1/admin/auth/nginx` → `backend/app/routes/admin.py::admin_nginx_auth()`；依赖：`未在装饰器声明`
- `GET /api/v1/admin/auth/me` → `backend/app/routes/admin.py::admin_me()`；依赖：`未在装饰器声明`
- `POST /api/v1/admin/auth/logout` → `backend/app/routes/admin.py::admin_logout()`；依赖：`未在装饰器声明`
- `GET /api/v1/admin/spec-groups` → `backend/app/routes/admin.py::admin_spec_groups()`；依赖：`未在装饰器声明`
- `GET /api/v1/admin/spec-definitions` → `backend/app/routes/admin.py::admin_spec_definitions()`；依赖：`未在装饰器声明`
- `PATCH /api/v1/admin/spec-definitions/{spec_id}` → `backend/app/routes/admin.py::admin_patch_spec_definition()`；依赖：`未在装饰器声明`
- `DELETE /api/v1/admin/series/{series_id}` → `backend/app/routes/admin.py::admin_delete_series()`；依赖：`未在装饰器声明`
- `GET /api/v1/admin/models` → `backend/app/routes/admin.py::admin_models()`；依赖：`未在装饰器声明`
- `GET /api/v1/admin/models/{model_id}` → `backend/app/routes/admin.py::admin_model_detail()`；依赖：`未在装饰器声明`
- `POST /api/v1/admin/spec-recognition/preview` → `backend/app/routes/admin.py::admin_spec_recognition_preview()`；依赖：`未在装饰器声明`
- `GET /api/v1/admin/import/template` → `backend/app/routes/admin.py::admin_import_template()`；依赖：`未在装饰器声明`
- `POST /api/v1/admin/import/preview` → `backend/app/routes/admin.py::admin_import_preview()`；依赖：`未在装饰器声明`
- `POST /api/v1/admin/import/run` → `backend/app/routes/admin.py::admin_import_run()`；依赖：`未在装饰器声明`
- `POST /api/v1/admin/import/markdown/preview` → `backend/app/routes/admin.py::admin_markdown_import_preview()`；依赖：`未在装饰器声明`
- `POST /api/v1/admin/import/markdown/run` → `backend/app/routes/admin.py::admin_markdown_import_run()`；依赖：`未在装饰器声明`
- `POST /api/v1/admin/models` → `backend/app/routes/admin.py::admin_create()`；依赖：`未在装饰器声明`
- `PATCH /api/v1/admin/models/{model_id}` → `backend/app/routes/admin.py::admin_patch()`；依赖：`未在装饰器声明`
- `PUT /api/v1/admin/models/{model_id}/compatible-gpus` → `backend/app/routes/admin.py::admin_replace_compatible_gpus()`；依赖：`未在装饰器声明`
- `DELETE /api/v1/admin/models/{model_id}` → `backend/app/routes/admin.py::admin_delete()`；依赖：`未在装饰器声明`
- `PUT /api/v1/admin/models/{model_id}/specifications` → `backend/app/routes/admin.py::admin_put_specs()`；依赖：`未在装饰器声明`
- `POST /api/v1/admin/models/upsert` → `backend/app/routes/admin.py::admin_upsert()`；依赖：`未在装饰器声明`
- `GET /api/v1/admin/gpu-options` → `backend/app/routes/admin.py::admin_gpu_options()`；依赖：`未在装饰器声明`
- `GET /api/v1/admin/ai-config` → `backend/app/routes/admin.py::admin_ai_config()`；依赖：`未在装饰器声明`
- `PUT /api/v1/admin/ai-config` → `backend/app/routes/admin.py::admin_put_ai_config()`；依赖：`未在装饰器声明`
- `DELETE /api/v1/admin/ai-config/api-key` → `backend/app/routes/admin.py::admin_delete_ai_config_api_key()`；依赖：`未在装饰器声明`
- `POST /api/v1/admin/ai-config/test` → `backend/app/routes/admin.py::admin_test_ai_config()`；依赖：`未在装饰器声明`
- `GET /api/v1/admin/ai-agent-rule` → `backend/app/routes/admin.py::admin_ai_agent_rule()`；依赖：`未在装饰器声明`
- `PUT /api/v1/admin/ai-agent-rule` → `backend/app/routes/admin.py::admin_put_ai_agent_rule()`；依赖：`未在装饰器声明`
- `GET /api/v1/health` → `backend/app/routes/public.py::health()`；依赖：`未在装饰器声明`
- `GET /api/v1/brands` → `backend/app/routes/public.py::brands()`；依赖：`未在装饰器声明`
- `GET /api/v1/product-types` → `backend/app/routes/public.py::product_types()`；依赖：`未在装饰器声明`
- `GET /api/v1/spec-definitions` → `backend/app/routes/public.py::spec_definitions()`；依赖：`未在装饰器声明`
- `GET /api/v1/series` → `backend/app/routes/public.py::series()`；依赖：`未在装饰器声明`
- `GET /api/v1/models` → `backend/app/routes/public.py::models()`；依赖：`未在装饰器声明`
- `GET /api/v1/models/{model_id}` → `backend/app/routes/public.py::model_detail()`；依赖：`未在装饰器声明`
- `GET /api/v1/models/{model_id}/specifications` → `backend/app/routes/public.py::model_specifications()`；依赖：`未在装饰器声明`
- `GET /api/v1/search` → `backend/app/routes/public.py::search()`；依赖：`未在装饰器声明`
- `GET /api/v1/cpu-compatibility/summary` → `backend/app/routes/public.py::cpu_compatibility_summary()`；依赖：`未在装饰器声明`
- `GET /api/v1/cpu-compatibility` → `backend/app/routes/public.py::cpu_compatibility()`；依赖：`未在装饰器声明`
- `POST /api/v1/ai/recommend` → `backend/app/routes/public.py::ai_recommend()`；依赖：`未在装饰器声明`
- `POST /validation-probe` → `backend/tests/test_validation_error_redaction.py::validation_probe()`；依赖：`未在装饰器声明`

## Vue 组件
- `frontend/src/App.vue` / `App`：props=[]；events=[]；state=['brandOptions', 'browseScrollY', 'catalogLoading', 'collapsedSeries', 'collapsedTypes', 'compareBusy', 'compareOnlyDiff', 'compareOpen', 'compareRowsFiltered', 'currentBrandName', 'currentCount', 'detailLoading', 'filteredModels', 'groupedSpecs', 'isMobileViewport', 'keyword', 'mobileNavigatorOpen', 'mobileOverlayOpen', 'navigationGroups', 'pageProductTitle', 'selectedBrand', 'selectedType', 'selectionNotesText', 'summaryCards', 'suppressBrandWatch', 'suppressKeywordWatch', 'typeFilteredModels', 'typeFilters']；media=[]
- `frontend/src/admin/AdminApp.vue` / `AdminApp`：props=[]；events=[]；state=['adminToken', 'adminUser', 'aiAgentRuleOpen', 'aiConfigBusy', 'aiConfigDeleting', 'aiConfigHasKey', 'aiConfigOpen', 'aiConfigTesting', 'basicForm', 'canWrite', 'compatibleGpusDirty', 'creating', 'filteredModels', 'formSeriesBrand', 'formSeriesLoading', 'formSeriesMessage', 'formSeriesOptions', 'formSeriesPlaceholder', 'hasApiKey', 'importBusy', 'isDeletedDetail', 'isGpuAccessoryDetail', 'isLoggedIn', 'keyword', 'loading', 'loginForm', 'markdownImportText', 'newSeriesName', 'notice', 'productTypes', 'recognitionMessage', 'recognitionText', 'recognizingSpecs', 'savingBasic', 'savingCompatibleGpus', 'savingSpecs', 'selectedBrand', 'selectedFormBrand', 'selectedFormSeries', 'selectedSeries', 'selectedType', 'seriesOptions', 'sortedSpecDefinitions', 'storagePreviewSpec', 'storagePreviewText']；media=[]
- `frontend/src/admin/components/AdminAiAgentRulePanel.vue` / `AdminAiAgentRulePanel`：props=[]；events=['saved']；state=['canSave', 'content', 'dirty', 'editorFullscreen', 'formattedUpdatedAt', 'isCompact', 'loading', 'message', 'saving', 'serverContent']；media=[]
- `frontend/src/admin/components/AdminAiConfigPanel.vue` / `AdminAiConfigPanel`：props=['busy', 'deleting', 'form', 'hasApiKey', 'testing']；events=['deleteKey', 'save', 'test']；state=[]；media=[]
- `frontend/src/admin/components/AdminBasicForm.vue` / `AdminBasicForm`：props=['basicForm', 'brands', 'creating', 'detailModelName', 'formSeriesLoading', 'formSeriesMessage', 'formSeriesOptions', 'formSeriesPlaceholder', 'hasApiKey', 'isDeletedDetail', 'newSeriesName', 'productTypeOptions', 'savingBasic', 'selectedFormSeries']；events=['remove-current', 'remove-selected-series', 'save-basic', 'update:newSeriesName']；state=['newSeriesNameProxy']；media=[]
- `frontend/src/admin/components/AdminCompatibleGpuPanel.vue` / `AdminCompatibleGpuPanel`：props=['dirty', 'disabled', 'gpuOptions', 'saving', 'selectedIds']；events=['save', 'update:selectedIds']；state=['filteredOptions', 'gpuExpanded', 'isCompact', 'keyword', 'visibleOptions']；media=[]
- `frontend/src/admin/components/AdminImportPanel.vue` / `AdminImportPanel`：props=['importBusy', 'importFile', 'importPreview', 'markdownText']；events=['clear-preview', 'download-template', 'preview-import', 'preview-markdown', 'run-import', 'run-markdown', 'update:importFile', 'update:markdownText']；state=['isCompact', 'markdownFullscreen']；media=[]
- `frontend/src/admin/components/AdminModelList.vue` / `AdminModelList`：props=['brands', 'creating', 'detailId', 'filteredModels', 'keyword', 'loading', 'productTypes', 'selectedBrand', 'selectedSeries', 'selectedType', 'seriesOptions', 'statusFilter']；events=['active', 'all', 'deleted', 'refresh', 'select-model', 'start-create', 'update:keyword', 'update:selectedBrand', 'update:selectedSeries', 'update:selectedType', 'update:statusFilter']；state=['canCollapseModels', 'currentModel', 'hasMoreModels', 'isResponsive', 'navigatorOpen', 'visibleCount', 'visibleModels']；media=[]
- `frontend/src/admin/components/AdminRecognitionPanel.vue` / `AdminRecognitionPanel`：props=['creating', 'definitionOptionLabel', 'isDeletedDetail', 'recognitionMessage', 'recognitionText', 'recognizedSpecs', 'recognizingSpecs', 'sortedSpecDefinitions', 'visible']；events=['apply', 'recognize', 'recognized-field-change', 'update:recognitionText']；state=[]；media=[]
- `frontend/src/admin/components/AdminSpecEditor.vue` / `AdminSpecEditor`：props=['creating', 'hasApiKey', 'isDeletedDetail', 'savingSpecs', 'specDefinitionOptionsFor', 'specsForm', 'storagePreviewText']；events=['add-spec', 'definition-change', 'remove-spec', 'save-specs']；state=[]；media=[]
- `frontend/src/admin/components/SeriesSelector.vue` / `SeriesSelector`：props=['basicForm', 'creating', 'formSeriesLoading', 'formSeriesMessage', 'formSeriesOptions', 'formSeriesPlaceholder', 'hasApiKey', 'newSeriesName', 'selectedFormSeries']；events=['remove-selected-series', 'update:newSeriesName']；state=['disabled', 'newSeriesNameProxy', 'seriesSelectRequired']；media=[]
- `frontend/src/admin/components/SpecRows.vue` / `SpecRows`：props=['showAdvanced', 'specDefinitionOptionsFor', 'specsForm']；events=['definition-change', 'remove-spec']；state=[]；media=[]
- `frontend/src/components/AiAssistant.vue` / `AiAssistant`：props=[]；events=['jump-model', 'open-change']；state=['busy', 'input', 'open']；media=[]
- `frontend/src/components/BrandHeader.vue` / `BrandHeader`：props=['brandOptions', 'currentBrandName', 'currentCount', 'pageProductTitle', 'selectedBrand']；events=['update:selectedBrand']；state=[]；media=[]
- `frontend/src/components/ModelDetail.vue` / `ModelDetail`：props=['detail', 'groupedSpecs', 'isCompareSelected', 'loading', 'selectionNotesText', 'summaryCards']；events=['jump-model', 'refresh-detail', 'toggle-compare']；state=['collapsedGroups']；media=[]
- `frontend/src/components/ModelNavigator.vue` / `ModelNavigator`：props=['isTypeOpen', 'keyword', 'loading', 'navigationGroups', 'selectedModelId', 'selectedType', 'typeFilters']；events=['select-model', 'select-type', 'toggle-series', 'toggle-type', 'update:keyword']；state=[]；media=[]
- `frontend/src/components/ProductBadges.vue` / `ProductBadges`：props=[]；events=[]；state=['items']；media=[]
- `frontend/src/components/ProductCompare.vue` / `ProductCompare`：props=['compareBusy', 'compareDetails', 'compareIds', 'compareOnlyDiff', 'compareOpen', 'compareRowsFiltered']；events=['clear', 'close', 'open', 'remove', 'update:compareOnlyDiff']；state=[]；media=[]

## Alembic 迁移
- `0001_initial_schema` ← `None`：`backend/alembic/versions/0001_initial_schema.py`
- `0002_cpu_compatibility` ← `0001_initial_schema`：`backend/alembic/versions/0002_cpu_compatibility.py`
- `0003_gpu_slot_cooling` ← `0002_cpu_compatibility`：`backend/alembic/versions/0003_gpu_slot_cooling.py`
- `0004_ai_config_compatible_gpu` ← `0003_gpu_slot_cooling`：`backend/alembic/versions/0004_ai_config_compatible_gpu.py`
- `0005_gpu_rel_cleanup` ← `0004_ai_config_compatible_gpu`：`backend/alembic/versions/0005_gpu_relation_constraints_acceptance_cleanup.py`
- `0006_gpu_parent_guard_import_trim_whitepaper` ← `0005_gpu_relation_constraints_acceptance_cleanup`：`backend/alembic/versions/0006_gpu_parent_guard_import_trim_whitepaper.py`
- `0007_nf5468a7_cross_platform_cleanup` ← `0006_gpu_parent_guard_import_trim_whitepaper`：`backend/alembic/versions/0007_nf5468a7_cross_platform_cleanup.py`
- `0008_nf5468a7_cn_cpu_notes_cleanup` ← `0007_nf5468a7_cross_platform_cleanup`：`backend/alembic/versions/0008_nf5468a7_cn_cpu_notes_cleanup.py`
- `0009_controlled_lifecycle_tags` ← `0008_nf5468a7_cn_notes`：`backend/alembic/versions/0009_controlled_lifecycle_tags.py`
- `0010_field_dictionary_guard` ← `0009_controlled_lifecycle_tags`：`backend/alembic/versions/0010_field_dictionary_guard.py`
- `0011_merge_auto_fields` ← `0010_field_dictionary_guard`：`backend/alembic/versions/0011_merge_auto_field_definitions.py`
- `0012_normalize_interface_fields` ← `0011_merge_auto_fields`：`backend/alembic/versions/0012_normalize_interface_fields.py`

## Compose
- `docker-compose.yml`
  - `db`：ports=[] volumes=['db-data:/var/lib/postgresql/data'] networks=[]
  - `api`：ports=[] volumes=[] networks=[]
  - `web`：ports=['8080:80'] volumes=[] networks=[]

## 依赖版本（来自声明文件）
```json
{
  "backend/pyproject.toml": {
    "requires_python": ">=3.12",
    "dependencies": [
      "alembic==1.13.2",
      "beautifulsoup4==4.12.3",
      "fastapi==0.111.1",
      "psycopg[binary]==3.2.1",
      "pydantic==2.8.2",
      "pydantic-settings==2.4.0",
      "sqlalchemy==2.0.31",
      "uvicorn[standard]==0.30.3",
      "openpyxl==3.1.5"
    ],
    "optional_dependencies": {
      "test": [
        "httpx==0.27.0",
        "pytest==8.3.2"
      ]
    }
  },
  "frontend/package.json": {
    "name": "hardware-product-library-web",
    "version": "0.1.0",
    "dependencies": {
      "@vitejs/plugin-vue": "5.1.2",
      "element-plus": "2.7.8",
      "typescript": "5.5.4",
      "vite": "5.4.2",
      "vue": "3.4.38",
      "vue-tsc": "2.0.29"
    },
    "devDependencies": {
      "@playwright/test": "^1.61.1",
      "@vue/test-utils": "^2.4.11",
      "happy-dom": "^15.11.7",
      "vitest": "^2.1.9"
    },
    "scripts": {
      "dev": "vite --host 0.0.0.0",
      "build": "vue-tsc -b && vite build",
      "test": "vitest run",
      "preview": "vite preview --host 0.0.0.0"
    }
  }
}
```
