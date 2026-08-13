// @vitest-environment happy-dom
import { mount } from '@vue/test-utils'
import { afterEach, describe, expect, it, vi } from 'vitest'
import AdminAiConfigPanel from './AdminAiConfigPanel.vue'

const makeForm = () => ({
  base_url: '', api_key: '', model: 'compatible-model', temperature: 0.2, max_tokens: 1200, enabled: true,
})

const mountPanel = (hasApiKey: boolean, extra = {}) => mount(AdminAiConfigPanel, {
  props: { form: makeForm(), hasApiKey, ...extra },
})

afterEach(() => vi.restoreAllMocks())

describe('AdminAiConfigPanel API Key controls', () => {
  it('removes provider presets and uses a generic OpenAI Compatible placeholder', () => {
    const wrapper = mountPanel(true)
    expect(wrapper.text()).not.toContain('填入 xxfly 中转站')
    expect(wrapper.text()).not.toContain('填入 OpenAI 官方')
    expect(wrapper.html()).not.toContain('api.internal.invalid')
    expect(wrapper.html()).not.toContain('api.openai.com')
    expect(wrapper.find('input[placeholder="https://example.com"]').exists()).toBe(true)
    expect(wrapper.text()).toContain('OpenAI Compatible')
  })

  it('shows the danger action only when a Key exists', () => {
    expect(mountPanel(true).find('button.danger').text()).toBe('删除当前 Key')
    const withoutKey = mountPanel(false)
    expect(withoutKey.find('button.danger').exists()).toBe(false)
    expect(withoutKey.text()).toContain('当前未保存模型Key')
  })

  it('does not emit deletion when confirmation is cancelled', async () => {
    vi.spyOn(window, 'confirm').mockReturnValue(false)
    const wrapper = mountPanel(true)
    await wrapper.find('button.danger').trigger('click')
    expect(window.confirm).toHaveBeenCalledWith(expect.stringContaining('仅删除 Key'))
    expect(wrapper.emitted('deleteKey')).toBeUndefined()
  })

  it('emits deletion after explicit confirmation and reflects deleting state', async () => {
    vi.spyOn(window, 'confirm').mockReturnValue(true)
    const wrapper = mountPanel(true, { deleting: true })
    expect(wrapper.find('button.danger').attributes('disabled')).toBeDefined()
    expect(wrapper.find('button.danger').text()).toBe('删除中')
    await wrapper.setProps({ deleting: false })
    await wrapper.find('button.danger').trigger('click')
    expect(wrapper.emitted('deleteKey')).toHaveLength(1)
  })
})
