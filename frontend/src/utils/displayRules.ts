import type { ModelSummary, SpecValue } from '../api'

export const EMPTY_HIDDEN_SPEC_KEYS = new Set(['selection_notes', 'official_params_url', 'gpu_official_params_url', 'product_brochure_url', 'whitepaper_url'])
export const SPEC_GROUP_ORDER = ['基础信息', '处理器', '内存', '存储', 'RAID', '网络', 'PCIe与扩展', 'GPU', '电源', '管理', '尺寸与环境', '操作系统与认证', '其他']

const inspurServerGenerationModels: Record<string, string[]> = {
  第5代服务器: ['I48M5-NS5484M5', 'NP5570M5'],
  第6代服务器: ['NF5180M6', 'NF5280A6', 'NF5280M6', 'NF5266M6', 'NF5466M6', 'NF5468M6', 'NF8260M6', 'NF8480M6'],
  第7代服务器: ['NF5280M7', 'NF5280A7', 'NF5266M7', 'NF5466M7', 'NF8260M7', 'NF8480M7', 'NF5468A7', 'NF5468M7', 'NF5688M7', 'NE5260M7'],
  第8代服务器: ['NF5280A8', 'NF5280M8', 'NF5468A8', 'NF5668M8', 'NF5868M8'],
}

const inspurModelGeneration = new Map(
  Object.entries(inspurServerGenerationModels).flatMap(([generation, names]) => names.map((name) => [normalizeModelToken(name), generation]))
)

const lenovoTsGlobalModels = ['P3 GEN2', 'P5 GEN2', 'P920', 'P620', 'PGX', 'PX', 'P3', 'P4', 'P5', 'P7', 'P8']
const lenovoXinchuangModels = ['P3H G1T', 'P3H G2T', 'P5H G1T', 'P7H G1T', 'P9Z G1T']

export function displayProductType(model: ModelSummary) {
  if (model.brand_code === 'inspur' && model.product_type === '服务器' && inspurStorageApplianceGroup(model)) return '存储'
  return model.product_type
}

export function displaySeriesName(model: ModelSummary) {
  if (model.brand_code === 'inspur' && displayProductType(model) === '存储') return inspurStorageApplianceGroup(model) || model.series
  if (model.brand_code === 'inspur' && model.product_type === '服务器') return inspurServerGroup(model)
  // Lenovo series must follow the database/admin import result. Do not re-bucket
  // imported ThinkStation/开天 models into legacy synthetic groups, otherwise the
  // user page navigator looks stale after admin imports.
  if (model.brand_code === 'lenovo' && model.product_type === '工作站') return model.series
  return model.series
}

export function brandLogoText(brandCode: string) {
  if (brandCode === 'generic' || brandCode === 'generic') return 'generic'
  if (brandCode === 'inspur') return 'Inspur'
  if (brandCode === 'lenovo') return 'Lenovo'
  if (brandCode === 'dell') return 'Dell'
  if (brandCode === 'accessory') return 'GPU'
  return brandCode || 'Brand'
}

export function typeSort(a: string, b: string) {
  const order = ['服务器', '存储', '工作站', '显卡', '其他']
  const ai = order.includes(a) ? order.indexOf(a) : order.length
  const bi = order.includes(b) ? order.indexOf(b) : order.length
  return ai === bi ? a.localeCompare(b, 'zh-CN') : ai - bi
}

export function seriesSort(a: string, b: string, type: string) {
  const generationOrder = ['第5代服务器', '第6代服务器', '第7代服务器', '第8代服务器', '其他服务器']
  const storageOrder = ['分布式存储', '备份一体机', '集中式存储']
  const workstationOrder = ['ThinkPad 移动工作站', 'TS全球系列机型', '信创机型', '其他工作站']
  const gpuOrder = ['GPU加速卡', 'AI推理卡', '国产显卡', '通用图形卡']
  const order = type === '服务器' ? generationOrder : type === '存储' ? storageOrder : type === '工作站' ? workstationOrder : type === '显卡' ? gpuOrder : []
  const ai = order.indexOf(a)
  const bi = order.indexOf(b)
  if (ai !== -1 || bi !== -1) return (ai === -1 ? order.length : ai) - (bi === -1 ? order.length : bi)
  return a.localeCompare(b, 'zh-CN')
}

export function isLinkSpec(spec: SpecValue) {
  return ['official_params_url', 'gpu_official_params_url', 'product_brochure_url', 'whitepaper_url'].includes(spec.field_key)
}

export function isCpuSpec(spec: SpecValue) {
  return ['cpu_family', 'hardware_compatibility'].includes(spec.field_key) || spec.group_name === '处理器'
}

export function splitSpecValue(value: string, fieldKey = '', cpuMode = false) {
  const storageNormalized = fieldKey === 'storage' ? normalizeStorageLayoutBreaks(value) : value
  const cpuNormalized = cpuMode ? normalizeCpuValue(storageNormalized) : storageNormalized
  return normalizeSentenceBreaks(cpuNormalized)
    .replace(/；(?![/?=&])/g, '；\n')
    .replace(/;(?![/?=&])/g, ';\n')
    .split(/\n+/)
    .map((item) => item.trim())
    .filter(Boolean)
}

export function summarizeSpec(value: string, fieldKey = '', maxItems = 3) {
  const items = splitSpecValue(value, fieldKey)
  if (!items.length) return value
  return items.slice(0, maxItems).join('；')
}

export function specLineClass(line: string, spec: SpecValue) {
  return {
    'spec-line': true,
    'cpu-heading': isCpuSpec(spec) && /[:：]$/.test(line),
    'cpu-bullet': isCpuSpec(spec) && /^[-•]/.test(line),
    'cpu-model': isCpuSpec(spec) && (/^(Platinum|Gold|Silver|Bronze|EPYC|Xeon|Intel|AMD|Hygon|海光|鲲鹏|飞腾|龙芯)\b/i.test(line) || /^\d{4}[A-Z+]?\s+\d+\/\d+\s+\d/.test(line)),
  }
}

function inspurServerGroup(model: ModelSummary) {
  const businessGroup = inspurStorageApplianceGroup(model)
  if (businessGroup) return businessGroup
  if (model.series === '信创服务器') return '信创服务器'
  const exact = inspurModelGeneration.get(normalizeModelToken(model.model_name))
  if (exact) return exact
  const generation = detectGeneration(model)
  return generation ? `第${generation}代服务器` : '其他服务器'
}

function inspurStorageApplianceGroup(model: ModelSummary) {
  const text = `${model.model_name} ${model.title} ${model.series}`.toUpperCase()
  const token = normalizeModelToken(model.model_name)
  if (text.includes('分布式存储') || token.startsWith('AS13000')) return '分布式存储'
  if (text.includes('备份一体机') || token.startsWith('DP3000')) return '备份一体机'
  if (text.includes('集中式存储') || /^HF(2000|3000)G7/.test(token)) return '集中式存储'
  return ''
}

function detectGeneration(model: ModelSummary) {
  const text = `${model.model_name} ${model.title} ${model.series} ${model.generation || ''}`.toUpperCase()
  const generationMatch = text.match(/(?:GEN|G|M|A|V)([5-8])(?=[^0-9]|$)/) || text.match(/(?:^|[^A-Z0-9])([5-8])(?:[^0-9]|$)/)
  if (generationMatch) return generationMatch[1]
  const chineseMatch = text.match(/第([五六七八5-8])代/)
  return chineseMatch ? chineseGenerationToNumber(chineseMatch[1]) : ''
}

function chineseGenerationToNumber(value: string) {
  return ({ 五: '5', 六: '6', 七: '7', 八: '8' } as Record<string, string>)[value] || value
}

function lenovoWorkstationGroup(model: ModelSummary) {
  const text = normalizeLenovoText(`${model.model_name} ${model.title} ${model.series}`)
  if (text.includes('THINKPAD')) return 'ThinkPad 移动工作站'
  if (matchesAnyModel(text, lenovoXinchuangModels)) return '信创机型'
  if (matchesAnyModel(text, lenovoTsGlobalModels)) return 'TS全球系列机型'
  return '其他工作站'
}

function normalizeModelToken(value: string) {
  return value.toUpperCase().replace(/[^A-Z0-9]/g, '')
}

function normalizeLenovoText(value: string) {
  return value
    .replace(/【企业购】/g, ' ')
    .toUpperCase()
    .replace(/[^A-Z0-9]+/g, ' ')
    .replace(/\s+/g, ' ')
    .trim()
}

function matchesAnyModel(text: string, modelsToMatch: string[]) {
  return modelsToMatch.some((name) => new RegExp(`(^|\\s)${name.replace(/\s+/g, '\\s+')}($|\\s)`).test(text))
}

function normalizeStorageLayoutBreaks(value: string) {
  return value
    .replace(/([；;])\s*(前置[:：])/g, '$1\n$2')
    .replace(/([；;])\s*(后置[:：])/g, '$1\n$2')
    .replace(/([；;])\s*(内置[:：])/g, '$1\n$2')
    .replace(/\s+(前置[:：])/g, '\n$1')
    .replace(/\s+(后置[:：])/g, '\n$1')
    .replace(/\s+(内置[:：])/g, '\n$1')
}

function normalizeCpuValue(value: string) {
  return value
    .replace(/([：:])\s*(Platinum|Gold|Silver|Bronze|EPYC|Xeon|Intel|AMD|Hygon|海光|鲲鹏|飞腾|龙芯)/gi, '$1\n$2')
    .replace(/([；;。])\s*(-\s*)/g, '$1\n$2')
    .replace(/([；;。])\s*((?:Platinum|Gold|Silver|Bronze|EPYC|Xeon|Intel|AMD|Hygon|海光|鲲鹏|飞腾|龙芯)\b)/gi, '$1\n$2')
    .replace(/,\s*((?:Platinum|Gold|Silver|Bronze|EPYC)\b)/g, '\n$1')
    .replace(/，\s*((?:Platinum|Gold|Silver|Bronze|EPYC)\b)/g, '\n$1')
    .replace(/\s+(?=\d{4}[A-Z+]?\s+\d+\/\d+\s+\d)/g, '\n')
}

function normalizeSentenceBreaks(value: string) {
  return value
    .replace(/。\s*/g, '。\n')
    .replace(/(?<=[\u4e00-\u9fa5])\.\s*(?=[\u4e00-\u9fa5A-Z0-9])/g, '.\n')
    .replace(/(?<=[a-zA-Z])\.\s+(?=[A-Z\u4e00-\u9fa5])/g, '.\n')
}
