// @vitest-environment happy-dom
import { describe, expect, it } from 'vitest'
import { mount } from '@vue/test-utils'
import AdminCompatibleGpuPanel from './AdminCompatibleGpuPanel.vue'

const options = [
  { id: 7, model_name: 'RTX 6000', title: 'RTX 6000', brand_code: 'accessory', product_type: '显卡', series: 'GPU', display_name: 'RTX 6000 48GB' },
  { id: 9, model_name: 'L40S', title: 'L40S', brand_code: 'accessory', product_type: '显卡', series: 'GPU', display_name: 'L40S 48GB' },
]

describe('AdminCompatibleGpuPanel', () => {
  it('shows an independent save button, emits selection and save', async () => {
    const wrapper = mount(AdminCompatibleGpuPanel, { props: { gpuOptions: options, selectedIds: [7], disabled: false, saving: false, dirty: true } })
    expect(wrapper.get('[data-testid="save-compatible-gpus"]').text()).toBe('保存兼容显卡')
    expect(wrapper.text()).toContain('选择已变化，尚未保存')

    await wrapper.findAll('input[type="checkbox"]')[1].setValue(true)
    expect(wrapper.emitted('update:selectedIds')?.[0]).toEqual([[7, 9]])
    await wrapper.get('[data-testid="save-compatible-gpus"]').trigger('click')
    expect(wrapper.emitted('save')).toHaveLength(1)
  })

  it('locks selection and shows saving state while request is active', () => {
    const wrapper = mount(AdminCompatibleGpuPanel, { props: { gpuOptions: options, selectedIds: [7], disabled: false, saving: true, dirty: true } })
    expect(wrapper.get('[data-testid="save-compatible-gpus"]').text()).toBe('保存中…')
    expect(wrapper.get('[data-testid="save-compatible-gpus"]').attributes('disabled')).toBeDefined()
    expect(wrapper.findAll('input[type="checkbox"]').every((item) => item.attributes('disabled') !== undefined)).toBe(true)
  })
})
