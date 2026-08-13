// @vitest-environment happy-dom
import { afterEach, describe, expect, it, vi } from 'vitest'
import { flushPromises, mount, type VueWrapper } from '@vue/test-utils'
import AdminAiAgentRulePanel from './AdminAiAgentRulePanel.vue'

const initial = { content: '# 初始规则', sha256: 'a'.repeat(64), updated_at: '2026-08-12T08:00:00Z', source: 'runtime' as const }
const wrappers: VueWrapper[] = []

function response(body: unknown, status = 200) {
  return new Response(typeof body === 'string' ? body : JSON.stringify(body), { status, headers: { 'Content-Type': 'application/json' } })
}

async function mounted(fetchMock = vi.spyOn(globalThis, 'fetch').mockResolvedValue(response(initial))) {
  const wrapper = mount(AdminAiAgentRulePanel, { props: { token: 'token-1' } })
  wrappers.push(wrapper)
  await flushPromises()
  return { wrapper, fetchMock }
}

afterEach(() => {
  wrappers.splice(0).forEach((wrapper) => wrapper.unmount())
  vi.restoreAllMocks()
})

describe('AdminAiAgentRulePanel', () => {
  it('loads the fixed rule and server metadata', async () => {
    const { wrapper, fetchMock } = await mounted()
    expect(fetchMock.mock.calls[0][0]).toBe('/api/v1/admin/ai-agent-rule')
    expect((fetchMock.mock.calls[0][1]?.headers as Record<string, string>).Authorization).toBe('Bearer token-1')
    expect((wrapper.get('textarea').element as HTMLTextAreaElement).value).toBe(initial.content)
    expect(wrapper.text()).toContain('固定文件：AI_SELECTION_AGENT.md')
    expect(wrapper.text()).toContain('aaaaaaaaaaaa')
    expect(wrapper.get('textarea').attributes('maxlength')).toBe('20000')
    expect(wrapper.find('input[type="file"]').exists()).toBe(false)
  })

  it('tracks dirty state and discards without a request', async () => {
    const { wrapper, fetchMock } = await mounted()
    await wrapper.get('textarea').setValue('# 草稿')
    expect(wrapper.text()).toContain('未保存')
    await wrapper.get('button.ghost').trigger('click')
    expect((wrapper.get('textarea').element as HTMLTextAreaElement).value).toBe(initial.content)
    expect(fetchMock).toHaveBeenCalledTimes(1)
  })

  it('retains draft on failure and adopts complete server response on success', async () => {
    const saved = { content: '# 服务端规范化规则\n', sha256: 'b'.repeat(64), updated_at: '2026-08-12T09:30:00Z', source: 'runtime' as const }
    const fetchMock = vi.spyOn(globalThis, 'fetch')
      .mockResolvedValueOnce(response(initial))
      .mockResolvedValueOnce(response('save failed', 500))
      .mockResolvedValueOnce(response(saved))
    const { wrapper } = await mounted(fetchMock)
    await wrapper.get('textarea').setValue('# 用户草稿')
    await wrapper.findAll('button').find((button) => button.text().includes('保存规则'))!.trigger('click')
    await flushPromises()
    expect((wrapper.get('textarea').element as HTMLTextAreaElement).value).toBe('# 用户草稿')
    expect(wrapper.text()).toContain('保存失败')
    expect(wrapper.text()).toContain('未保存')
    await wrapper.findAll('button').find((button) => button.text().includes('保存规则'))!.trigger('click')
    await flushPromises()
    expect((wrapper.get('textarea').element as HTMLTextAreaElement).value).toBe(saved.content)
    expect(wrapper.text()).toContain('bbbbbbbbbbbb')
    expect(wrapper.find('.ai-agent-rule-count').text()).not.toContain('· 未保存')
  })

  it('blocks dirty beforeunload but not clean beforeunload', async () => {
    const { wrapper } = await mounted()
    const clean = new Event('beforeunload', { cancelable: true })
    window.dispatchEvent(clean)
    expect(clean.defaultPrevented).toBe(false)
    await wrapper.get('textarea').setValue('# changed')
    const dirty = new Event('beforeunload', { cancelable: true })
    window.dispatchEvent(dirty)
    expect(dirty.defaultPrevented).toBe(true)
  })

  it('shows exact character count after editing', async () => {
    const { wrapper } = await mounted()
    await wrapper.get('textarea').setValue('12345')
    expect(wrapper.find('.ai-agent-rule-count').text()).toContain('5 / 20000')
  })

  it('guards blank content and shows the evidence safety boundary', async () => {
    const { wrapper } = await mounted()
    await wrapper.get('textarea').setValue('   ')
    const save = wrapper.findAll('button').find((button) => button.text().includes('保存规则'))!
    expect(save.attributes('disabled')).toBeDefined()
    expect(wrapper.text()).toContain('候选型号、匹配状态、兼容关系和 BOM 事实')
  })
})
