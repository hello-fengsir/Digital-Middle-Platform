<template>
  <div class="admin-shell">
    <header class="admin-topbar">
      <div class="admin-brand">
        <div class="admin-brand-mark text-brand" aria-label="Product Hub">PH</div>
        <div class="admin-brand-copy">
          <p class="admin-kicker">Hardware Product Library</p>
          <h1>轻量产品管理</h1>
          <p class="admin-subtitle">产品型号、基础信息、规格参数与模板导入统一维护</p>
        </div>
      </div>
      <div v-if="isLoggedIn" class="key-box session-box">
        <span class="session-user">已登录：{{ adminUser || 'admin' }}</span>
        <button type="button" class="ghost" @click="openAiConfig">AI配置</button>
        <button type="button" class="ghost" @click="openAiAgentRule">智能体规则</button>
        <a class="ghost session-link" href="/pdf-viewer/" target="_blank" rel="noopener">天仓管理库</a>
        <button type="button" class="ghost" @click="logout">退出登录</button>
      </div>
    </header>

    <div v-if="notice" class="notice global-notice" :class="noticeType">{{ notice }}</div>

    <section v-if="!isLoggedIn" class="login-wrap">
      <div class="login-visual">
        <p class="admin-kicker">Secure Console</p>
        <h2>Product Hub 后台</h2>
        <p>沿用前台产品库的红蓝视觉系统，管理操作保持聚焦、清晰、可追踪。</p>
      </div>
      <section class="editor-panel login-panel">
        <p class="admin-kicker">Admin Login</p>
        <h2>后台登录</h2>
        <form class="basic-form" @submit.prevent="login">
          <label><span>账号</span><input v-model.trim="loginForm.username" autocomplete="username" /></label>
          <label><span>密码</span><input v-model="loginForm.password" type="password" autocomplete="current-password" /></label>
          <div class="form-actions"><button type="submit">登录</button></div>
        </form>
      </section>
    </section>

    <main v-else class="admin-layout">
      <AdminModelList
        v-model:selected-brand="selectedBrand"
        v-model:selected-type="selectedType"
        v-model:selected-series="selectedSeries"
        v-model:status-filter="statusFilter"
        v-model:keyword="keyword"
        :brands="brands"
        :product-types="productTypes"
        :series-options="seriesOptions"
        :filtered-models="filteredModels"
        :loading="loading"
        :creating="creating"
        :detail-id="detail?.id || null"
        @refresh="loadModels"
        @start-create="startCreate"
        @select-model="selectModel"
      />

      <section class="admin-content">
        <div class="dictionary-freeze-notice" role="note">
          <b>字段字典已冻结</b>
          <span>型号规格只能选择现有字段；导入与 AI 识别不会创建、改名或重排字段。</span>
        </div>
        <AdminBasicForm
          v-model:new-series-name="newSeriesName"
          :basic-form="basicForm"
          :brands="brands"
          :product-type-options="productTypeOptions"
          :creating="creating"
          :detail-model-name="detail?.model_name || ''"
          :is-deleted-detail="isDeletedDetail"
          :has-api-key="hasApiKey"
          :saving-basic="savingBasic"
          :form-series-loading="formSeriesLoading"
          :form-series-options="formSeriesOptions"
          :selected-form-series="selectedFormSeries"
          :form-series-placeholder="formSeriesPlaceholder"
          :form-series-message="formSeriesMessage"
          @save-basic="saveBasic"
          @remove-current="removeCurrent"
          @remove-selected-series="removeSelectedSeries"
        />

          <AdminCompatibleGpuPanel
          v-if="Boolean(detail) && !creating && !isGpuAccessoryDetail"
          :gpu-options="gpuOptions"
          :selected-ids="compatibleGpuIds"
          :disabled="!canWrite || isDeletedDetail"
          :saving="savingCompatibleGpus"
          :dirty="compatibleGpusDirty"
          @update:selected-ids="compatibleGpuIds = $event"
          @save="saveCompatibleGpus"
        />

        <AdminRecognitionPanel
            v-model:recognition-text="recognitionText"
            :visible="creating || Boolean(detail)"
            :creating="creating"
            :is-deleted-detail="isDeletedDetail"
            :recognizing-specs="recognizingSpecs"
            :recognition-message="recognitionMessage"
            :recognized-specs="recognizedSpecs"
            :sorted-spec-definitions="sortedSpecDefinitions"
            :definition-option-label="definitionOptionLabel"
            @recognize="recognizeSpecText"
            @apply="applyRecognizedSpecs"
            @recognized-field-change="onRecognizedFieldChange"
          />

          <AdminSpecEditor
            v-if="creating && specsForm.length"
            :creating="true"
            :specs-form="specsForm"
            storage-preview-text=""
            :has-api-key="hasApiKey"
            :saving-specs="savingSpecs"
            :is-deleted-detail="isDeletedDetail"
            :spec-definition-options-for="specDefinitionOptionsFor"
            :definition-option-key="definitionOptionKey"
            :definition-option-label="definitionOptionLabel"
            :is-legacy-spec-definition="isLegacySpecDefinition"
            :display-spec-sort-order="displaySpecSortOrder"
            @definition-change="onSpecDefinitionChange($event.spec, $event.event)"
            @remove-spec="removeSpec"
          />

        <AdminSpecEditor
          v-if="detail && !creating"
          :creating="false"
          :specs-form="specsForm"
          :storage-preview-text="storagePreviewSpec ? storagePreviewText : ''"
          :has-api-key="hasApiKey"
          :saving-specs="savingSpecs"
          :is-deleted-detail="isDeletedDetail"
          :spec-definition-options-for="specDefinitionOptionsFor"
          :definition-option-key="definitionOptionKey"
          :definition-option-label="definitionOptionLabel"
          :is-legacy-spec-definition="isLegacySpecDefinition"
          :display-spec-sort-order="displaySpecSortOrder"
          @definition-change="onSpecDefinitionChange($event.spec, $event.event)"
          @remove-spec="removeSpec"
          @add-spec="addSpec"
          @save-specs="saveSpecs"
        />

        <AdminImportPanel
          v-model:import-file="importFile"
          v-model:markdown-text="markdownImportText"
          :import-busy="importBusy"
          :import-preview="importPreview"
          @clear-preview="importPreview = null"
          @download-template="downloadTemplate"
          @preview-import="previewImport"
          @run-import="runImport"
          @preview-markdown="previewMarkdown"
          @run-markdown="runMarkdown"
        />

      </section>
    </main>

    <div v-if="aiConfigOpen" class="admin-modal-mask" @click.self="closeAiConfig">
      <div ref="aiConfigDialog" class="admin-modal-panel" role="dialog" aria-modal="true" aria-labelledby="ai-config-dialog-title" tabindex="-1" @keydown="trapDialogFocus($event, 'config')">
        <h2 id="ai-config-dialog-title" class="admin-dialog-title">AI 配置</h2>
        <button type="button" class="admin-modal-close" aria-label="关闭 AI 配置" @click="closeAiConfig">×</button>
        <AdminAiConfigPanel
          :form="aiConfigForm"
          :has-api-key="aiConfigHasKey"
          :busy="aiConfigBusy"
          :testing="aiConfigTesting"
          :deleting="aiConfigDeleting"
          @save="saveAiSettings"
          @test="testAiSettings"
          @delete-key="deleteAiKey"
        />
      </div>
    </div>

    <div v-if="aiAgentRuleOpen" class="admin-modal-mask" @click.self="requestCloseAiAgentRule">
      <div ref="aiAgentRuleDialog" class="admin-modal-panel ai-agent-rule-modal" role="dialog" aria-modal="true" aria-labelledby="ai-agent-rule-dialog-title" tabindex="-1" @keydown="trapDialogFocus($event, 'rule')">
        <h2 id="ai-agent-rule-dialog-title" class="admin-dialog-title">智能体规则</h2>
        <button type="button" class="admin-modal-close" aria-label="关闭智能体规则" @click="requestCloseAiAgentRule">×</button>
        <AdminAiAgentRulePanel ref="aiAgentRulePanel" :token="adminToken" @saved="showNotice('智能体规则已保存')" />
      </div>
    </div>

  </div>
</template>

<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, onMounted, reactive, ref, watch } from 'vue'
import AdminBasicForm from './components/AdminBasicForm.vue'
import AdminAiConfigPanel from './components/AdminAiConfigPanel.vue'
import AdminAiAgentRulePanel from './components/AdminAiAgentRulePanel.vue'
import AdminCompatibleGpuPanel from './components/AdminCompatibleGpuPanel.vue'
import AdminImportPanel from './components/AdminImportPanel.vue'
import AdminModelList from './components/AdminModelList.vue'
import AdminRecognitionPanel from './components/AdminRecognitionPanel.vue'
import AdminSpecEditor from './components/AdminSpecEditor.vue'
import {
  createModel,
  deleteModel,
  deleteSeries,
  deleteAiConfigApiKey,
  getAdminMe,
  getAdminModel,
  getAdminModels,
  getAiConfig,
  getGpuOptions,
  loginAdmin,
  logoutAdmin,
  saveAiConfig,
  testAiConfig,
  getBrands,
  getModel,
  getModels,
  getProductTypes,
  getSeries,
  getSpecDefinitions,
  patchModel,
  replaceSpecifications,
  replaceCompatibleGpus,
  downloadImportTemplate,
  previewImportWorkbook,
  runImportWorkbook,
  previewMarkdownImport,
  runMarkdownImport,
  previewSpecRecognition,
  type AiConfigPayload,
  type Brand,
  type CompatibleGpu,
  type ModelDetail,
  type ModelSummary,
  type ProductType,
  type Series,
  type SpecDefinition,
  type SpecInput,
  type SpecValue,
  type ImportPreviewOut,
} from './adminApi'
import { validatedPdfViewerNext } from '../utils/adminRedirect'

const ADMIN_TOKEN_STORAGE = 'hpl_admin_token'
const STORAGE_PREVIEW_KEY = 'storage_sheet_preview'
const DEFAULT_SORT_ORDER = 9999
const REQUIRED_LEADING_SPEC_KEYS = ['selection_notes', 'official_params_url', 'product_brochure_url'] as const

const brands = ref<Brand[]>([])
const productTypeOptions = ref<ProductType[]>([])
const formSeriesCatalog = ref<Series[]>([])
const formSeriesBrand = ref('')
const models = ref<ModelSummary[]>([])
const detail = ref<ModelDetail | null>(null)
const selectedBrand = ref('')
const selectedType = ref('')
const selectedSeries = ref('')
const statusFilter = ref<'active' | 'deleted' | 'all'>('active')
const keyword = ref('')
const newSeriesName = ref('')
const loading = ref(false)
const formSeriesLoading = ref(false)
const creating = ref(false)
const savingBasic = ref(false)
const savingSpecs = ref(false)
const savingCompatibleGpus = ref(false)
const recognizingSpecs = ref(false)
const notice = ref('')
const noticeType = ref<'ok' | 'error'>('ok')
const adminToken = ref(sessionStorage.getItem(ADMIN_TOKEN_STORAGE) || '')
const adminUser = ref('')
const loginForm = reactive({ username: 'admin', password: '' })
const specsForm = ref<SpecInput[]>([])
const specDefinitions = ref<SpecDefinition[]>([])
const recognitionText = ref('')
const recognitionMessage = ref('')
const recognizedSpecs = ref<RecognizedSpecRow[]>([])
const importFile = ref<File | null>(null)
const importPreview = ref<ImportPreviewOut | null>(null)
const markdownImportText = ref('')
const importBusy = ref(false)
const gpuOptions = ref<CompatibleGpu[]>([])
const compatibleGpuIds = ref<number[]>([])
const savedCompatibleGpuIds = ref<number[]>([])
const aiConfigHasKey = ref(false)
const aiConfigOpen = ref(false)
const aiAgentRuleOpen = ref(false)
const aiConfigDialog = ref<HTMLElement | null>(null)
const aiAgentRuleDialog = ref<HTMLElement | null>(null)
let dialogReturnFocus: HTMLElement | null = null
let bodyOverflowBeforeDialog = ''
const aiAgentRulePanel = ref<InstanceType<typeof AdminAiAgentRulePanel> | null>(null)
const aiConfigBusy = ref(false)
const aiConfigTesting = ref(false)
const aiConfigDeleting = ref(false)
const aiConfigForm = reactive<AiConfigPayload>({ base_url: '', api_key: '', model: '', temperature: 0.2, max_tokens: 1200, enabled: false })

const basicForm = reactive({
  brand_code: '',
  brand_name: '',
  product_type: '',
  series: '',
  model_name: '',
  title: '',
  platform_vendor: '',
  generation: '',
  lifecycle_status: '' as '' | 'npi' | 'rts' | 'rtq' | 'eos' | 'eol',
  featured: false,
  source_ref: 'admin',
  raw_source_id: '',
})

const isLoggedIn = computed(() => adminToken.value.trim().length > 0)
const canWrite = computed(() => isLoggedIn.value)
const hasApiKey = computed(() => canWrite.value)
const isDeletedDetail = computed(() => Boolean(detail.value?.deleted_at) || detail.value?.status === 'deleted')
const isGpuAccessoryDetail = computed(() => Boolean(detail.value && detail.value.brand_code.toLowerCase() === 'accessory' && detail.value.product_type === '显卡'))
const compatibleGpusDirty = computed(() => normalizedIds(compatibleGpuIds.value).join(',') !== normalizedIds(savedCompatibleGpuIds.value).join(','))

const filteredModels = computed(() => {
  const q = keyword.value.trim().toLowerCase()
  return models.value.filter((model) => {
    if (selectedType.value && model.product_type !== selectedType.value) return false
    if (selectedSeries.value && model.series !== selectedSeries.value) return false
    if (!q) return true
    return [model.model_name, model.title, model.series, model.brand_name].some((value) => value.toLowerCase().includes(q))
  })
})

const productTypes = computed(() => [...new Set(models.value.map((model) => model.product_type))].sort())
const seriesOptions = computed(() => {
  return [...new Set(models.value.filter((model) => !selectedType.value || model.product_type === selectedType.value).map((model) => model.series))].sort()
})
const selectedFormBrand = computed(() => brands.value.find((brand) => brand.code === basicForm.brand_code) || null)
const formSeriesOptions = computed(() => {
  return formSeriesCatalog.value
    .filter((series) => !basicForm.product_type || series.product_type === basicForm.product_type)
    .sort((a, b) => a.name.localeCompare(b.name, 'zh-CN'))
})
const selectedFormSeries = computed(() => formSeriesOptions.value.find((series) => series.name === basicForm.series) || null)
const formSeriesPlaceholder = computed(() => {
  if (!basicForm.brand_code) return '请先选择品牌'
  if (!basicForm.product_type) return '请先选择产品类型'
  if (formSeriesLoading.value) return '系列加载中'
  if (formSeriesOptions.value.length === 0) return '暂无可选系列'
  return '选择系列'
})
const formSeriesMessage = computed(() => {
  if (!basicForm.brand_code || !basicForm.product_type || formSeriesLoading.value) return ''
  if (creating.value) return '先下拉选择已有系列；如需新增，在下方输入新系列名，创建型号时会自动新增该系列'
  if (formSeriesOptions.value.length === 0) return '暂无可选系列，请先维护系列'
  return ''
})
const storagePreviewSpec = computed(() => detail.value?.specifications.find((spec) => spec.field_key === STORAGE_PREVIEW_KEY) || null)
const storagePreviewText = computed(() => {
  const value = storagePreviewSpec.value?.value || ''
  try {
    return JSON.stringify(JSON.parse(value), null, 2)
  } catch {
    return value
  }
})

function groupSortOrder(definition: { name: string }) {
  const groupName = definition.name
  const definitionGroup = specDefinitions.value.find((item) => item.group_name === groupName)
  if (definitionGroup?.group_sort_order != null) return definitionGroup.group_sort_order
  const groupIndex = specGroupOptionsFallback.indexOf(groupName || '其他')
  return groupIndex === -1 ? DEFAULT_SORT_ORDER : (groupIndex + 1) * 100
}
function specSortOrder(spec: SpecInput) {
  return spec.sort_order ?? DEFAULT_SORT_ORDER
}
function leadingSpecIndex(fieldKey: string) {
  return REQUIRED_LEADING_SPEC_KEYS.indexOf(fieldKey as typeof REQUIRED_LEADING_SPEC_KEYS[number])
}
function sortSpecInputs(items: SpecInput[]) {
  return [...items].sort((a, b) =>
    (leadingSpecIndex(a.field_key) === -1 ? REQUIRED_LEADING_SPEC_KEYS.length : leadingSpecIndex(a.field_key))
    - (leadingSpecIndex(b.field_key) === -1 ? REQUIRED_LEADING_SPEC_KEYS.length : leadingSpecIndex(b.field_key))
    ||
    groupSortOrder({ name: a.group || '其他' }) - groupSortOrder({ name: b.group || '其他' })
    || specSortOrder(a) - specSortOrder(b)
    || (a.label || a.field_key).localeCompare(b.label || b.field_key, 'zh-CN')
  )
}
const specGroupOptionsFallback = ['基础信息', '处理器', '内存', '存储', 'RAID', '网络', 'PCIe与扩展', 'GPU', '电源', '管理', '尺寸与环境', '操作系统与认证', '其他']

const sortedSpecDefinitions = computed(() => {
  return specDefinitions.value.filter((definition) =>
    definition.group_code !== 'storage_preview' && isVisibleAdminField(definition.field_key, definition.label)
  ).sort((a, b) =>
    (a.group_sort_order ?? groupSortOrder({ name: a.group_name || '其他' })) - (b.group_sort_order ?? groupSortOrder({ name: b.group_name || '其他' }))
    || a.sort_order - b.sort_order
    || a.label.localeCompare(b.label, 'zh-CN')
  )
})

function specDefinitionByKey(fieldKey: string) {
  return specDefinitions.value.find((definition) => definition.field_key === fieldKey) || null
}

function isRequiredLeadingSpec(fieldKey: string) {
  return leadingSpecIndex(fieldKey) !== -1
}

function requiredLeadingSpecInput(fieldKey: typeof REQUIRED_LEADING_SPEC_KEYS[number]): SpecInput | null {
  const definition = specDefinitionByKey(fieldKey)
  if (!definition) return null
  return normalizeSpecWithDefinition({
    field_key: definition.field_key,
    label: definition.label,
    group: definition.group_name || '其他',
    sort_order: definition.sort_order ?? DEFAULT_SORT_ORDER,
    value: '',
    raw_label: definition.label,
    source_ref: 'admin',
  })
}

function withRequiredLeadingSpecs(items: SpecInput[]) {
  const byKey = new Map(items.map((item) => [item.field_key, item]))
  const missingRequired = REQUIRED_LEADING_SPEC_KEYS
    .filter((fieldKey) => !byKey.has(fieldKey))
    .map(requiredLeadingSpecInput)
    .filter((spec): spec is SpecInput => Boolean(spec))
  return sortSpecInputs([...items, ...missingRequired])
}

type SpecDefinitionOption = SpecDefinition & { is_legacy?: boolean }

interface RecognizedSpecRow {
  raw_label: string
  value: string
  field_key: string
  confidence: string
  remark: string
  include: boolean
}

function specDefinitionOptionsFor(spec: SpecInput): SpecDefinitionOption[] {
  if (!spec.field_key || specDefinitionByKey(spec.field_key)) return sortedSpecDefinitions.value
  return [
    {
      id: -1,
      group_code: '',
      group_name: spec.group || '其他',
      field_key: spec.field_key,
      label: `${spec.label || spec.field_key}（未在字段字典中）`,
      group_sort_order: groupSortOrder({ name: spec.group || '其他' }),
      sort_order: spec.sort_order ?? DEFAULT_SORT_ORDER,
      is_legacy: true,
    },
    ...sortedSpecDefinitions.value,
  ]
}

function isLegacySpecDefinition(definition: SpecDefinitionOption) {
  return Boolean(definition.is_legacy)
}

function definitionOptionKey(definition: SpecDefinitionOption) {
  return `${definition.is_legacy ? 'legacy' : 'dict'}-${definition.field_key}`
}

function definitionOptionLabel(definition: SpecDefinitionOption) {
  return `${definition.group_name || '其他'} · ${definition.label}`
}

function displaySpecSortOrder(spec: SpecInput) {
  const definition = specDefinitionByKey(spec.field_key)
  const groupOrder = definition?.group_sort_order ?? groupSortOrder({ name: spec.group || '其他' })
  return `group ${groupOrder} / field ${spec.sort_order ?? DEFAULT_SORT_ORDER}`
}

function bindSpecDefinition(spec: SpecInput, definition: SpecDefinition) {
  spec.field_key = definition.field_key
  spec.label = definition.label
  spec.group = definition.group_name || '其他'
  spec.sort_order = definition.sort_order ?? DEFAULT_SORT_ORDER
  spec.raw_label = definition.label
}

function normalizeSpecWithDefinition(spec: SpecInput) {
  const definition = specDefinitionByKey(spec.field_key.trim())
  if (!definition) return null
  return {
    ...spec,
    field_key: definition.field_key,
    label: definition.label,
    group: definition.group_name || '其他',
    sort_order: definition.sort_order ?? DEFAULT_SORT_ORDER,
    raw_label: definition.label,
  }
}

function onSpecDefinitionChange(spec: SpecInput, event: Event) {
  const fieldKey = (event.target as HTMLSelectElement).value
  const definition = specDefinitionByKey(fieldKey)
  if (!definition) {
    spec.field_key = ''
    spec.label = ''
    spec.group = ''
    spec.sort_order = null
    spec.raw_label = ''
    return
  }
  bindSpecDefinition(spec, definition)
}

function normalizeRecognitionText(value: string) {
  return value.toLowerCase().replace(/[：:\s\-_（）()【】\[\]\/]+/g, '')
}

function candidateDefinitionText(definition: SpecDefinition) {
  return [
    definition.label,
    definition.field_key,
    definition.group_name ? `${definition.group_name}${definition.label}` : '',
  ].map(normalizeRecognitionText).filter(Boolean)
}

function matchSpecDefinition(rawLabel: string) {
  const normalizedLabel = normalizeRecognitionText(rawLabel)
  if (!normalizedLabel) return { definition: null as SpecDefinition | null, confidence: '低', remark: '未匹配，需人工选择字段' }
  const exact = sortedSpecDefinitions.value.find((definition) => candidateDefinitionText(definition).includes(normalizedLabel))
  if (exact) return { definition: exact, confidence: '高', remark: '字段字典精确匹配' }
  const contains = sortedSpecDefinitions.value.find((definition) =>
    candidateDefinitionText(definition).some((candidate) => candidate.includes(normalizedLabel) || normalizedLabel.includes(candidate))
  )
  if (contains) return { definition: contains, confidence: '中', remark: '字段字典近似匹配，请确认' }
  return { definition: null as SpecDefinition | null, confidence: '低', remark: '未匹配，需人工选择字段' }
}

function parseSpecLine(line: string) {
  const cleaned = line.replace(/^[\s|,，;；]+|[\s|,，;；]+$/g, '').replace(/\s*\|\s*/g, ' ')
  if (!cleaned) return null
  const colonMatch = cleaned.match(/^(.{2,40}?)[：:]\s*(.+)$/)
  if (colonMatch) return { raw_label: colonMatch[1].trim(), value: colonMatch[2].trim() }
  const tabParts = cleaned.split(/\t+/).map((part) => part.trim()).filter(Boolean)
  if (tabParts.length >= 2) return { raw_label: tabParts[0], value: tabParts.slice(1).join(' ') }
  const spacedMatch = cleaned.match(/^([\u4e00-\u9fa5A-Za-z0-9（）()\/\-\s]{2,28}?)\s{2,}(.+)$/)
  if (spacedMatch) return { raw_label: spacedMatch[1].trim(), value: spacedMatch[2].trim() }
  const looseMatch = cleaned.match(/^([\u4e00-\u9fa5A-Za-z0-9（）()\/\-]{2,18})\s+(.+)$/)
  if (looseMatch) return { raw_label: looseMatch[1].trim(), value: looseMatch[2].trim() }
  return null
}

function localRecognizeSpecText() {
  const lines = recognitionText.value.split(/\r?\n/).map((line) => line.trim()).filter(Boolean)
  const rows = lines.map(parseSpecLine).filter((row): row is { raw_label: string; value: string } => Boolean(row?.raw_label && row.value))
  const deduped = new Map<string, RecognizedSpecRow>()
  for (const row of rows) {
    const matched = matchSpecDefinition(row.raw_label)
    const key = `${normalizeRecognitionText(row.raw_label)}::${row.value}`
    if (!deduped.has(key)) {
      deduped.set(key, {
        raw_label: row.raw_label,
        value: row.value,
        field_key: matched.definition?.field_key || '',
        confidence: matched.confidence,
        remark: `本地规则兜底；${matched.remark}`,
        include: Boolean(matched.definition),
      })
    }
  }
  recognizedSpecs.value = [...deduped.values()]
  recognitionMessage.value = recognizedSpecs.value.length
    ? `本地规则兜底识别 ${recognizedSpecs.value.length} 项；未匹配项需人工选择字段后再应用。`
    : '未识别到可预览参数，请按“参数名：值”或“参数名 值”格式粘贴。'
}
async function recognizeSpecText() {
  if (!recognitionText.value.trim()) return showNotice('请先粘贴服务器参数文本', 'error')
  if (!adminToken.value) return showNotice('请先登录后台', 'error')
  recognizingSpecs.value = true
  try {
    const result = await previewSpecRecognition(adminToken.value, {
      raw_text: recognitionText.value,
      brand_code: basicForm.brand_code || undefined,
      product_type: basicForm.product_type || undefined,
      series: basicForm.series || undefined,
      model_name: basicForm.model_name || undefined,
    })
    recognizedSpecs.value = result.items.map((item) => {
      const definition = item.matched_field_key ? specDefinitionByKey(item.matched_field_key) : null
      return {
        raw_label: item.raw_label,
        value: item.value,
        field_key: definition?.field_key || '',
        confidence: item.confidence >= 0.8 ? '高' : item.confidence >= 0.5 ? '中' : '低',
        remark: item.note || (definition ? 'AI/规则识别匹配字段字典' : '未匹配，需人工选择字段'),
        include: Boolean(definition),
      }
    })
    recognitionMessage.value = recognizedSpecs.value.length
      ? `已调用后端 AI/规则识别 ${recognizedSpecs.value.length} 项；未匹配项需人工选择字段后再应用。`
      : '后端未识别到可预览参数，请调整文本格式或手工新增参数。'
  } catch (error) {
    console.warn('后端识别失败，使用本地规则兜底', error)
    localRecognizeSpecText()
  } finally {
    recognizingSpecs.value = false
  }
}
function onRecognizedFieldChange(row: RecognizedSpecRow) {
  const definition = specDefinitionByKey(row.field_key)
  if (!definition) {
    row.confidence = '低'
    row.remark = '未匹配，需人工选择字段'
    row.include = false
    return
  }
  row.confidence = row.confidence === '高' ? row.confidence : '人工'
  row.remark = '人工确认字段字典'
  row.include = true
}

function applyRecognizedSpecs() {
  const selectedRows = recognizedSpecs.value.filter((row) => row.include)
  const unbound = selectedRows.find((row) => !specDefinitionByKey(row.field_key))
  if (unbound) return showNotice(`请先为“${unbound.raw_label}”选择字段字典项`, 'error')
  let applied = 0
  for (const row of selectedRows) {
    const definition = specDefinitionByKey(row.field_key)
    if (!definition) continue
    const value = row.value.trim()
    if (!value) continue
    const existing = specsForm.value.find((spec) => spec.field_key === definition.field_key)
    if (existing) {
      bindSpecDefinition(existing, definition)
      if (existing.value.trim() && existing.value.trim() !== value) {
        const labelPrefix = row.raw_label && row.raw_label !== definition.label ? row.raw_label + '：' : ''
        existing.value = existing.value.trim() + '\n' + labelPrefix + value
      } else {
        existing.value = value
      }
    } else {
      specsForm.value.push({
        field_key: definition.field_key,
        label: definition.label,
        group: definition.group_name || '其他',
        sort_order: definition.sort_order ?? DEFAULT_SORT_ORDER,
        value,
        raw_label: row.raw_label,
        source_ref: 'text-recognition',
      })
    }
    applied += 1
  }
  specsForm.value = withRequiredLeadingSpecs(sortSpecInputs(specsForm.value))
  recognitionText.value = ""
  recognizedSpecs.value = []
  recognitionMessage.value = ""
  showNotice(creating.value ? `已应用 ${applied} 项到新型号规格，确认后点击“创建型号”` : `已应用 ${applied} 项到当前型号规格表单，请确认后点击“保存规格”`)
}

let formSeriesRequestId = 0

watch(selectedType, () => {
  if (selectedSeries.value && !seriesOptions.value.includes(selectedSeries.value)) selectedSeries.value = ''
})

watch(selectedFormBrand, (brand) => {
  basicForm.brand_name = brand?.name || ''
})

watch(() => basicForm.brand_code, async (brandCode) => {
  await loadFormSeries(brandCode)
})

watch(() => basicForm.product_type, () => {
  if (
    basicForm.series
    && formSeriesBrand.value === basicForm.brand_code
    && !formSeriesLoading.value
    && !formSeriesOptions.value.some((series) => series.name === basicForm.series)
  ) basicForm.series = ''
  if (!creating.value) newSeriesName.value = ''
})

function showNotice(message: string, type: 'ok' | 'error' = 'ok') {
  notice.value = message
  noticeType.value = type
  window.setTimeout(() => {
    if (notice.value === message) notice.value = ''
  }, 4000)
}

async function login() {
  try {
    const session = await loginAdmin(loginForm.username.trim(), loginForm.password)
    adminToken.value = session.token
    adminUser.value = session.username
    sessionStorage.setItem(ADMIN_TOKEN_STORAGE, session.token)
    loginForm.password = ''
    const next = validatedPdfViewerNext(window.location.search, window.location.origin)
    if (next) {
      window.location.assign(next)
      return
    }
    await loadAuthenticatedData()
    showNotice('登录成功')
  } catch (error) {
    showNotice(`登录失败：${error instanceof Error ? error.message : String(error)}`, 'error')
  }
}

async function logout() {
  try {
    await logoutAdmin()
  } catch (error) {
    console.warn('服务端退出失败，继续清理本地会话', error)
  } finally {
    adminToken.value = ''
    adminUser.value = ''
    sessionStorage.removeItem(ADMIN_TOKEN_STORAGE)
    showNotice('已退出登录')
  }
}

async function restoreLogin() {
  if (!adminToken.value) return
  try {
    const me = await getAdminMe(adminToken.value)
    adminUser.value = me.username
  } catch {
    logout()
  }
}

async function loadAuthenticatedData() {
  if (!isLoggedIn.value) return
  await Promise.all([loadGpuOptions(), loadAiSettings()])
  await loadModels()
}

function resetForm() {
  Object.assign(basicForm, {
    brand_code: selectedBrand.value || '',
    brand_name: brands.value.find((brand) => brand.code === selectedBrand.value)?.name || '',
    product_type: '',
    series: '',
    model_name: '',
    title: '',
    platform_vendor: '',
    generation: '',
    lifecycle_status: '',
    featured: false,
    source_ref: 'admin',
    raw_source_id: '',
  })
  specsForm.value = []
  compatibleGpuIds.value = []
  savedCompatibleGpuIds.value = []
  newSeriesName.value = ''
  recognitionText.value = ''
  recognitionMessage.value = ''
  recognizedSpecs.value = []
  newSeriesName.value = ''
}

function syncFromDetail(model: ModelDetail) {
  Object.assign(basicForm, {
    brand_code: model.brand_code,
    brand_name: model.brand_name,
    product_type: model.product_type,
    series: model.series,
    model_name: model.model_name,
    title: model.title,
    platform_vendor: model.platform_vendor || '',
    generation: model.generation || '',
    lifecycle_status: ['npi', 'rts', 'rtq', 'eos', 'eol'].includes(model.lifecycle_status || '') ? model.lifecycle_status as 'npi' | 'rts' | 'rtq' | 'eos' | 'eol' : '',
    featured: Array.isArray(model.business_tags) && model.business_tags.includes('featured'),
    source_ref: model.source_ref || 'admin',
    raw_source_id: model.raw_source_id || '',
  })
  specsForm.value = withRequiredLeadingSpecs(model.specifications.filter(isVisibleAdminSpec).map((spec) => {
    const input = specToInput(spec)
    return normalizeSpecWithDefinition(input) || input
  }))
  recognitionMessage.value = ''
  recognizedSpecs.value = []
  const ids = (model.brand_code.toLowerCase() === 'accessory' && model.product_type === '显卡') ? [] : (model.compatible_gpus?.map((gpu) => gpu.id) || [])
  compatibleGpuIds.value = [...ids]
  savedCompatibleGpuIds.value = [...ids]
}

function normalizedIds(ids: number[]) {
  return [...new Set(ids)].sort((a, b) => a - b)
}

function specToInput(spec: SpecValue): SpecInput {
  return {
    field_key: spec.field_key,
    label: spec.label,
    group: spec.group_name || '其他',
    sort_order: (spec as SpecValue & { sort_order?: number | null }).sort_order ?? DEFAULT_SORT_ORDER,
    value: spec.value,
    raw_label: spec.raw_label || spec.label,
    source_ref: spec.source_ref || 'admin',
  }
}

function isVisibleAdminSpec(spec: SpecValue) {
  return spec.field_key !== STORAGE_PREVIEW_KEY && isVisibleAdminField(spec.field_key, spec.label)
}

function isVisibleAdminField(fieldKey: string, labelText: string) {
  const key = fieldKey.toLowerCase()
  const label = labelText.toLowerCase()
  return !key.startsWith('raw_')
    && !key.startsWith('source_')
    && !['source_title', 'source_ref', 'raw_label', 'raw_value', 'original_source', 'raw_source_id'].includes(key)
    && !label.includes('来源')
    && !label.includes('原始')
    && !label.includes('source')
    && !label.includes('raw_')
}

async function loadBrands() {
  brands.value = await getBrands()
}

async function loadProductTypes() {
  productTypeOptions.value = await getProductTypes()
}

async function loadFormSeries(brandCode: string) {
  const requestId = ++formSeriesRequestId
  if (!brandCode) {
    formSeriesCatalog.value = []
    formSeriesBrand.value = ''
    basicForm.series = ''
    return
  }
  formSeriesLoading.value = true
  try {
    const rows = await getSeries(brandCode)
    if (requestId !== formSeriesRequestId) return
    formSeriesCatalog.value = rows
    formSeriesBrand.value = brandCode
    if (basicForm.series && !formSeriesOptions.value.some((series) => series.name === basicForm.series)) basicForm.series = ''
  } catch (error) {
    if (requestId !== formSeriesRequestId) return
    formSeriesCatalog.value = []
    formSeriesBrand.value = brandCode
    basicForm.series = ''
    showNotice(`系列加载失败：${error instanceof Error ? error.message : String(error)}`, 'error')
  } finally {
    if (requestId === formSeriesRequestId) formSeriesLoading.value = false
  }
}


async function loadGpuOptions() {
  if (!adminToken.value) return
  try {
    gpuOptions.value = await getGpuOptions(adminToken.value)
  } catch (error) {
    showNotice(`显卡选项加载失败：${error instanceof Error ? error.message : String(error)}`, 'error')
  }
}

function focusableElements(root: HTMLElement) {
  return [...root.querySelectorAll<HTMLElement>('button:not([disabled]), a[href], input:not([disabled]), select:not([disabled]), textarea:not([disabled]), [tabindex]:not([tabindex="-1"])')]
    .filter((element) => !element.hasAttribute('hidden') && element.getClientRects().length > 0)
}

function lockDialogScroll() {
  document.body.style.overflow = 'hidden'
}

function syncDialogViewport() {
  const viewport = window.visualViewport
  const root = document.documentElement
  root.style.setProperty('--admin-vv-height', `${Math.round(viewport?.height || window.innerHeight)}px`)
  root.style.setProperty('--admin-vv-top', `${Math.round(viewport?.offsetTop || 0)}px`)
}

function startDialogViewportSync() {
  syncDialogViewport()
  window.visualViewport?.addEventListener('resize', syncDialogViewport)
  window.visualViewport?.addEventListener('scroll', syncDialogViewport)
}

function stopDialogViewportSync() {
  window.visualViewport?.removeEventListener('resize', syncDialogViewport)
  window.visualViewport?.removeEventListener('scroll', syncDialogViewport)
  document.documentElement.style.removeProperty('--admin-vv-height')
  document.documentElement.style.removeProperty('--admin-vv-top')
}

function restoreDialogFocus() {
  if (aiConfigOpen.value || aiAgentRuleOpen.value) return
  stopDialogViewportSync()
  document.body.style.overflow = bodyOverflowBeforeDialog
  nextTick(() => dialogReturnFocus?.focus())
}

async function enterDialog(dialog: typeof aiConfigDialog) {
  lockDialogScroll()
  startDialogViewportSync()
  await nextTick()
  const root = dialog.value
  if (root) (focusableElements(root)[0] || root).focus()
}

function trapDialogFocus(event: KeyboardEvent, kind: 'config' | 'rule') {
  if (event.key === 'Escape') {
    event.preventDefault()
    kind === 'config' ? closeAiConfig() : requestCloseAiAgentRule()
    return
  }
  if (event.key !== 'Tab') return
  const root = kind === 'config' ? aiConfigDialog.value : aiAgentRuleDialog.value
  if (!root) return
  const items = focusableElements(root)
  if (!items.length) { event.preventDefault(); root.focus(); return }
  const first = items[0]
  const last = items[items.length - 1]
  if (event.shiftKey && document.activeElement === first) { event.preventDefault(); last.focus() }
  else if (!event.shiftKey && document.activeElement === last) { event.preventDefault(); first.focus() }
}

function openAiConfig(event: MouseEvent) {
  dialogReturnFocus = event.currentTarget as HTMLElement
  bodyOverflowBeforeDialog = document.body.style.overflow
  aiConfigOpen.value = true
  enterDialog(aiConfigDialog)
}

function closeAiConfig() {
  aiConfigOpen.value = false
  restoreDialogFocus()
}

function openAiAgentRule(event: MouseEvent) {
  dialogReturnFocus = event.currentTarget as HTMLElement
  bodyOverflowBeforeDialog = document.body.style.overflow
  aiAgentRuleOpen.value = true
  enterDialog(aiAgentRuleDialog)
}

function requestCloseAiAgentRule() {
  if (aiAgentRulePanel.value?.isDirty() && !window.confirm('存在未保存的智能体规则，确认离开并丢弃修改吗？')) return
  aiAgentRuleOpen.value = false
  restoreDialogFocus()
}

async function loadAiSettings() {
  if (!adminToken.value) return
  try {
    const cfg = await getAiConfig(adminToken.value)
    aiConfigForm.base_url = cfg.base_url
    aiConfigForm.model = cfg.model
    aiConfigForm.temperature = cfg.temperature
    aiConfigForm.max_tokens = cfg.max_tokens
    aiConfigForm.enabled = cfg.enabled
    aiConfigForm.api_key = ''
    aiConfigHasKey.value = cfg.has_api_key
  } catch (error) {
    showNotice(`AI配置加载失败：${error instanceof Error ? error.message : String(error)}`, 'error')
  }
}

async function saveAiSettings() {
  aiConfigBusy.value = true
  try {
    const cfg = await saveAiConfig(adminToken.value, aiConfigForm)
    aiConfigHasKey.value = cfg.has_api_key
    aiConfigForm.api_key = ''
    showNotice('AI配置已保存')
  } catch (error) {
    showNotice(`AI配置保存失败：${error instanceof Error ? error.message : String(error)}`, 'error')
  } finally {
    aiConfigBusy.value = false
  }
}

async function deleteAiKey() {
  if (!aiConfigHasKey.value || aiConfigDeleting.value) return
  aiConfigDeleting.value = true
  try {
    const cfg = await deleteAiConfigApiKey(adminToken.value)
    aiConfigForm.base_url = cfg.base_url
    aiConfigForm.model = cfg.model
    aiConfigForm.temperature = cfg.temperature
    aiConfigForm.max_tokens = cfg.max_tokens
    aiConfigForm.enabled = cfg.enabled
    aiConfigForm.api_key = ''
    aiConfigHasKey.value = cfg.has_api_key
    showNotice('当前模型 Key 已删除，AI 功能已自动停用；Base URL、模型和参数已保留')
  } catch (error) {
    showNotice(`模型 Key 删除失败：${error instanceof Error ? error.message : String(error)}`, 'error')
  } finally {
    aiConfigDeleting.value = false
  }
}

async function testAiSettings() {
  aiConfigTesting.value = true
  try {
    const result = await testAiConfig(adminToken.value, aiConfigForm)
    showNotice(`AI连接成功：${result.message}`)
  } catch (error) {
    showNotice(`AI连接失败：${error instanceof Error ? error.message : String(error)}`, 'error')
  } finally {
    aiConfigTesting.value = false
  }
}

async function loadSpecDefinitions() {
  try {
    specDefinitions.value = await getSpecDefinitions()
  } catch (error) {
    showNotice(`字段字典加载失败：${error instanceof Error ? error.message : String(error)}`, 'error')
  }
}

async function loadModels() {
  loading.value = true
  try {
    models.value = await getAdminModels(adminToken.value, selectedBrand.value, statusFilter.value)
    if (!creating.value && detail.value && !models.value.some((model) => model.id === detail.value?.id)) {
      detail.value = null
      resetForm()
    }
  } catch (error) {
    showNotice(`型号加载失败：${error instanceof Error ? error.message : String(error)}`, 'error')
  } finally {
    loading.value = false
  }
}

async function selectModel(id: number) {
  creating.value = false
  try {
    detail.value = await getAdminModel(adminToken.value, id)
    syncFromDetail(detail.value)
  } catch (error) {
    showNotice(`详情加载失败：${error instanceof Error ? error.message : String(error)}`, 'error')
  }
}

function startCreate() {
  creating.value = true
  detail.value = null
  resetForm()
}

async function removeSelectedSeries() {
  if (!hasApiKey.value) return showNotice('请先登录后台', 'error')
  const series = selectedFormSeries.value
  if (!series) return showNotice('请先选择要删除的系列', 'error')
  if (series.model_count > 0) return showNotice(`该系列下有 ${series.model_count} 个在架型号，不能删除`, 'error')
  if (!window.confirm(`确认删除空系列「${series.name}」？`)) return
  try {
    await deleteSeries(adminToken.value, series.id)
    showNotice('空系列已删除')
    basicForm.series = ''
    await loadFormSeries(basicForm.brand_code)
    await loadModels()
  } catch (error) {
    showNotice(`系列删除失败：${error instanceof Error ? error.message : String(error)}`, 'error')
  }
}

function basePayload() {
  const lifecycleStatus = basicForm.lifecycle_status
  if (!['npi', 'rts', 'rtq', 'eos', 'eol'].includes(lifecycleStatus)) throw new Error('请选择生命周期')
  return {
    brand_code: basicForm.brand_code,
    brand_name: basicForm.brand_name || null,
    product_type: basicForm.product_type,
    series: creating.value && newSeriesName.value.trim() ? newSeriesName.value.trim() : basicForm.series,
    model_name: basicForm.model_name,
    title: basicForm.title || basicForm.model_name,
    platform_vendor: basicForm.platform_vendor || null,
    generation: basicForm.generation || null,
    lifecycle_status: lifecycleStatus as 'npi' | 'rts' | 'rtq' | 'eos' | 'eol',
    business_tags: basicForm.featured ? ['featured' as const] : [],
    source_ref: basicForm.source_ref || 'admin',
    raw_source_id: basicForm.raw_source_id || null,
  }
}

function normalizedSpecsForSubmit({ includeEmptyRequired = false } = {}) {
  return specsForm.value
    .map((spec): SpecInput | null => {
      const normalized = normalizeSpecWithDefinition(spec)
      if (!normalized) return null
      const field_key = normalized.field_key.trim()
      const label = normalized.label.trim()
      const value = normalized.value.trim()
      if (!value && !(includeEmptyRequired && isRequiredLeadingSpec(field_key))) return null
      return {
        ...normalized,
        field_key,
        label,
        value,
        raw_label: normalized.raw_label || label,
        source_ref: normalized.source_ref || 'admin',
      }
    })
    .filter((spec): spec is SpecInput => Boolean(spec?.field_key && spec.label && spec.value.trim()))
}

function validateSpecsForSubmit() {
  const missingField = specsForm.value.find((spec) => spec.value.trim() && !spec.field_key.trim())
  if (missingField) return '存在已填写值但未选择参数项的规格行'
  const unboundField = specsForm.value.find((spec) => spec.value.trim() && !specDefinitionByKey(spec.field_key.trim()))
  if (unboundField) return `请从字段字典下拉选择参数项：${unboundField.label || unboundField.field_key || '未选择行'}`
  return ''
}

async function saveBasic() {
  if (!hasApiKey.value) return showNotice('请先登录后台', 'error')
  if (isDeletedDetail.value) return showNotice('已下架型号仅支持查看和永久删除，不能编辑保存', 'error')
  if (!basicForm.brand_code) return showNotice('请选择品牌代码', 'error')
  if (!basicForm.product_type) return showNotice('请选择产品类型', 'error')
  if (!['npi', 'rts', 'rtq', 'eos', 'eol'].includes(basicForm.lifecycle_status)) return showNotice('请选择生命周期', 'error')
  const effectiveSeries = creating.value && newSeriesName.value.trim() ? newSeriesName.value.trim() : basicForm.series
  if (!effectiveSeries) return showNotice(creating.value ? '请选择已有系列，或在下方输入新系列名' : '请选择系列；暂无可选系列时请先维护系列', 'error')
  savingBasic.value = true
  try {
    if (creating.value) {
      const specError = validateSpecsForSubmit()
      if (specError) {
        showNotice(specError, 'error')
        return
      }
      const createSpecs = normalizedSpecsForSubmit()
      const created = await createModel(adminToken.value, { ...basePayload(), specifications: createSpecs })
      creating.value = false
      detail.value = created
      selectedBrand.value = created.brand_code
      selectedType.value = created.product_type
      selectedSeries.value = created.series
      await loadModels()
      syncFromDetail(created)
      showNotice(`型号已创建，用户页刷新后可见：/?brand=${encodeURIComponent(created.brand_code)}`)
    } else if (detail.value) {
      const updated = await patchModel(adminToken.value, detail.value.id, basePayload())
      detail.value = updated
      await loadModels()
      syncFromDetail(updated)
      showNotice('基础信息已保存')
    }
  } catch (error) {
    showNotice(`保存失败：${error instanceof Error ? error.message : String(error)}`, 'error')
  } finally {
    savingBasic.value = false
  }
}

function addSpec() {
  specsForm.value.push({
    field_key: '',
    label: '',
    group: '',
    sort_order: null,
    value: '',
    raw_label: '',
    source_ref: 'admin',
  })
}

function removeSpec(index: number) {
  if (isRequiredLeadingSpec(specsForm.value[index]?.field_key || '')) {
    showNotice('固定前三参数项不可删除，可清空值后保存', 'error')
    return
  }
  specsForm.value.splice(index, 1)
}

async function saveSpecs() {
  if (!detail.value) return
  if (compatibleGpusDirty.value) return showNotice('兼容显卡选择已变化，请先点击“保存兼容显卡”，再保存规格', 'error')
  if (!hasApiKey.value) return showNotice('请先登录后台', 'error')
  if (isDeletedDetail.value) return showNotice('已下架型号仅支持查看和永久删除，不能编辑保存', 'error')
  const missingField = specsForm.value.find((spec) => !spec.field_key.trim())
  if (missingField) return showNotice('请先为每一行规格选择参数项', 'error')
  const fieldKeys = specsForm.value.map((spec) => spec.field_key.trim()).filter(Boolean)
  const unboundField = specsForm.value.find((spec) => !specDefinitionByKey(spec.field_key.trim()))
  if (unboundField) return showNotice(`请从字段字典下拉选择参数项：${unboundField.label || unboundField.field_key || '未选择行'}`, 'error')
  const duplicatedField = fieldKeys.find((fieldKey, index) => fieldKeys.indexOf(fieldKey) !== index)
  if (duplicatedField) {
    const definition = specDefinitionByKey(duplicatedField)
    return showNotice(`参数项重复：${definition?.label || duplicatedField}`, 'error')
  }
  const editableItems = specsForm.value
      .map((spec): SpecInput | null => {
        const normalized = normalizeSpecWithDefinition(spec)
        if (!normalized) return null
        const field_key = normalized.field_key.trim()
        const label = normalized.label.trim()
        if (isRequiredLeadingSpec(field_key) && !normalized.value.trim()) return null
        return {
          ...normalized,
          field_key,
          label,
          raw_label: label,
          source_ref: normalized.source_ref || 'admin',
        }
      })
      .filter((spec): spec is SpecInput => Boolean(spec?.field_key && spec.label))
  const editable = sortSpecInputs(editableItems)
  const preserved = storagePreviewSpec.value ? [specToInput(storagePreviewSpec.value)] : []
  savingSpecs.value = true
  try {
    const saved = await replaceSpecifications(adminToken.value, detail.value.id, [...editable, ...preserved])
    detail.value = { ...detail.value, specifications: saved }
    specsForm.value = withRequiredLeadingSpecs(saved.filter(isVisibleAdminSpec).map(specToInput))
    showNotice('规格参数已保存')
  } catch (error) {
    showNotice(`规格保存失败：${error instanceof Error ? error.message : String(error)}`, 'error')
  } finally {
    savingSpecs.value = false
  }
}

async function saveCompatibleGpus() {
  if (!detail.value) return
  if (!hasApiKey.value) return showNotice('请先登录后台', 'error')
  if (isDeletedDetail.value) return showNotice('已下架型号仅支持查看，不能保存兼容显卡', 'error')
  if (!compatibleGpusDirty.value) return showNotice('兼容显卡选择没有变化')
  savingCompatibleGpus.value = true
  try {
    const result = await replaceCompatibleGpus(adminToken.value, detail.value.id, normalizedIds(compatibleGpuIds.value))
    const saved = Array.isArray(result) ? result : result.compatible_gpus
    detail.value = { ...detail.value, compatible_gpus: saved }
    compatibleGpuIds.value = saved.map((gpu) => gpu.id)
    savedCompatibleGpuIds.value = [...compatibleGpuIds.value]
    showNotice('兼容显卡已保存，用户页刷新后可见')
  } catch (error) {
    showNotice(`兼容显卡保存失败：${error instanceof Error ? error.message : String(error)}`, 'error')
  } finally {
    savingCompatibleGpus.value = false
  }
}

async function removeCurrent() {
  if (!detail.value) return
  if (!hasApiKey.value) return showNotice('请先登录后台', 'error')
  const permanent = isDeletedDetail.value
  const actionText = permanent ? '永久删除' : '软删除/下架'
  if (!window.confirm(`确认${actionText} ${detail.value.model_name}？${permanent ? ' 此操作会删除规格参数且不可恢复。' : ''}`)) return
  try {
    await deleteModel(adminToken.value, detail.value.id)
    showNotice(permanent ? '已下架型号已永久删除' : '型号已软删除/下架')
    detail.value = null
    resetForm()
    await loadModels()
  } catch (error) {
    showNotice(`删除失败：${error instanceof Error ? error.message : String(error)}`, 'error')
  }
}


async function downloadTemplate() {
  const response = await downloadImportTemplate(adminToken.value)
  if (!response.ok) return showNotice('模板下载失败', 'error')
  const blob = await response.blob()
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = 'hardware-product-library-import-template.xlsx'
  a.click()
  URL.revokeObjectURL(url)
}
async function previewImport() {
  if (!importFile.value) return
  importBusy.value = true
  try {
    const response = await previewImportWorkbook(adminToken.value, importFile.value)
    if (!response.ok) throw new Error(await response.text())
    importPreview.value = await response.json()
    showNotice('导入预览完成')
  } catch (e) { showNotice('预览失败：' + (e instanceof Error ? e.message : String(e)), 'error') }
  finally { importBusy.value = false }
}
async function runImport() {
  if (!importFile.value) return
  importBusy.value = true
  try {
    const response = await runImportWorkbook(adminToken.value, importFile.value)
    if (!response.ok) throw new Error(await response.text())
    const result = await response.json()
    showNotice('导入完成：新增 ' + result.created + '，更新 ' + result.updated)
    await loadModels()
  } catch (e) { showNotice('导入失败：' + (e instanceof Error ? e.message : String(e)), 'error') }
  finally { importBusy.value = false }
}

async function previewMarkdown() {
  if (!markdownImportText.value.trim()) return
  importBusy.value = true
  try {
    importPreview.value = await previewMarkdownImport(adminToken.value, markdownImportText.value)
    showNotice('Markdown 导入预览完成')
  } catch (e) { showNotice('Markdown 预览失败：' + (e instanceof Error ? e.message : String(e)), 'error') }
  finally { importBusy.value = false }
}

async function runMarkdown() {
  if (!markdownImportText.value.trim()) return
  importBusy.value = true
  try {
    const result = await runMarkdownImport(adminToken.value, markdownImportText.value)
    showNotice('Markdown 导入完成：新增 ' + result.created + '，更新 ' + result.updated)
    await loadModels()
  } catch (e) { showNotice('Markdown 导入失败：' + (e instanceof Error ? e.message : String(e)), 'error') }
  finally { importBusy.value = false }
}

onBeforeUnmount(() => {
  document.body.style.overflow = bodyOverflowBeforeDialog
})

onMounted(async () => {
  await restoreLogin()
  await loadBrands()
  await loadProductTypes()
  await loadSpecDefinitions()
  selectedBrand.value = new URLSearchParams(window.location.search).get('brand') || ''
  await loadAuthenticatedData()
})
</script>
