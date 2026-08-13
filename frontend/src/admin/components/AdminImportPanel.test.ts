// @vitest-environment happy-dom
import { mount } from '@vue/test-utils'
import { describe, expect, it } from 'vitest'
// @ts-ignore Node types are not installed in this frontend package.
import { readFileSync } from 'node:fs'
import AdminImportPanel from './AdminImportPanel.vue'

const props = { importFile: null, importBusy: false, importPreview: null, markdownText: '' }

describe('AdminImportPanel Markdown editor sizing', () => {
  it('uses a dedicated class only on the Markdown import textarea', () => {
    const wrapper = mount(AdminImportPanel, { props })
    const textarea = wrapper.get('textarea')
    expect(textarea.classes()).toContain('markdown-import-textarea')
    expect(wrapper.findAll('textarea')).toHaveLength(1)
  })

  it('scopes desktop and mobile height rules without changing generic or AI editors', () => {
    const css = readFileSync('src/admin/admin.css', 'utf8')
    expect(css).toMatch(/\.admin-shell \.markdown-import-textarea \{[^}]*width: 100%;[^}]*min-height: 360px;[^}]*max-height: 70vh;[^}]*resize: vertical;/s)
    expect(css).toMatch(/@media \(max-width: 560px\) \{ \.admin-shell \.markdown-import-textarea \{ min-height: 260px; max-height: 65vh; \} \}/)
    expect(css).not.toMatch(/\.admin-shell textarea \{[^}]*min-height: 360px/s)
    expect(css).toMatch(/\.ai-agent-rule-editor \{ min-height:52vh !important;/)
  })
})
