// @vitest-environment happy-dom
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { flushPromises, mount, type VueWrapper } from '@vue/test-utils'
import AdminApp from './AdminApp.vue'

vi.mock('./adminApi', () => ({
  createModel: vi.fn(), deleteModel: vi.fn(), deleteSeries: vi.fn(), deleteAiConfigApiKey: vi.fn(),
  getAdminMe: vi.fn(async () => ({ username: 'admin' })),
  getAdminModel: vi.fn(), getAdminModels: vi.fn(async () => []),
  getAiConfig: vi.fn(async () => ({ base_url: '', model: '', temperature: 0.2, max_tokens: 1200, enabled: false, has_api_key: false })),
  getGpuOptions: vi.fn(async () => []), loginAdmin: vi.fn(), logoutAdmin: vi.fn(), saveAiConfig: vi.fn(), testAiConfig: vi.fn(),
  getBrands: vi.fn(async () => []), getModel: vi.fn(), getModels: vi.fn(), getProductTypes: vi.fn(async () => []),
  getSeries: vi.fn(async () => []), getSpecDefinitions: vi.fn(async () => []), patchModel: vi.fn(), replaceSpecifications: vi.fn(),
  replaceCompatibleGpus: vi.fn(), downloadImportTemplate: vi.fn(), previewImportWorkbook: vi.fn(), runImportWorkbook: vi.fn(),
  previewMarkdownImport: vi.fn(), runMarkdownImport: vi.fn(), previewSpecRecognition: vi.fn(),
}))

const wrappers: VueWrapper[] = []

async function render(loggedIn: boolean) {
  if (loggedIn) sessionStorage.setItem('hpl_admin_token', 'token-1')
  const wrapper = mount(AdminApp, {
    global: {
      stubs: {
        AdminBasicForm: true, AdminAiConfigPanel: true, AdminAiAgentRulePanel: true,
        AdminCompatibleGpuPanel: true, AdminImportPanel: true, AdminModelList: true,
        AdminRecognitionPanel: true, AdminSpecEditor: true,
      },
    },
  })
  wrappers.push(wrapper)
  await flushPromises()
  return wrapper
}

beforeEach(() => sessionStorage.clear())
afterEach(() => {
  wrappers.splice(0).forEach((wrapper) => wrapper.unmount())
  sessionStorage.clear()
  vi.clearAllMocks()
})

describe('AdminApp 天仓管理库入口', () => {
  it('未登录时不显示入口', async () => {
    const wrapper = await render(false)
    expect(wrapper.find('a.session-link').exists()).toBe(false)
    expect(wrapper.text()).not.toContain('天仓管理库')
  })

  it('登录后在智能体规则与退出登录之间显示原生同源新窗口链接', async () => {
    const wrapper = await render(true)
    const session = wrapper.get('.session-box')
    const link = session.get('a.session-link')
    expect(link.text()).toBe('天仓管理库')
    expect(link.attributes()).toMatchObject({ href: '/pdf-viewer/', target: '_blank', rel: 'noopener' })
    const controls = session.findAll('button, a').map((item) => item.text())
    expect(controls).toEqual(['AI配置', '智能体规则', '天仓管理库', '退出登录'])
  })

  it('点击入口不在当前页面触发 beforeunload', async () => {
    const wrapper = await render(true)
    const beforeUnload = vi.fn()
    const link = wrapper.get('a.session-link')
    link.element.addEventListener('click', (event) => event.preventDefault(), { once: true })
    window.addEventListener('beforeunload', beforeUnload)
    await link.trigger('click')
    expect(beforeUnload).not.toHaveBeenCalled()
    window.removeEventListener('beforeunload', beforeUnload)
  })
})
