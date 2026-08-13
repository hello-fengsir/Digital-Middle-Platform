import { chromium } from 'playwright'

const modelBase = {
  brand_code: 'mock', brand_name: 'MockBrand', product_type: '服务器', series: 'MockSeries',
  generation: '', platform_vendor: '', title: 'Mock Server', source_ref: 'mock', lifecycle_status: 'active', business_tags: [], badges: [],
}
const gpu = (id, name) => ({ id, display_name: name, model_name: name, title: name, brand_code: 'accessory', product_type: '显卡', series: 'GPU' })
const spec = (field_key, value, group_name = 'GPU', label = '显卡') => ({ field_key, value, group_name, label, group_code: group_name.toLowerCase(), raw_label: label, source_ref: '', confidence: '' })
const details = {
  1: { ...modelBase, id: 1, model_name: 'BOUND-SERVER', specifications: [spec('gpu_support', '历史静态型号')], compatible_gpus: [gpu(101, 'NVIDIA L20'), gpu(102, 'NVIDIA L40S')] },
  2: { ...modelBase, id: 2, model_name: 'STATIC-SERVER', specifications: [spec('gpu_support', '历史静态型号')], compatible_gpus: [] },
  3: { ...modelBase, id: 3, model_name: 'NO-GPU-GROUP', specifications: [spec('memory', '1TB', '内存', '内存')], compatible_gpus: [gpu(101, 'NVIDIA L20')] },
  101: { ...modelBase, id: 101, brand_code: 'accessory', brand_name: 'Accessory', product_type: '显卡', model_name: 'NVIDIA L20', title: 'NVIDIA L20', specifications: [], compatible_gpus: [] },
  102: { ...modelBase, id: 102, brand_code: 'accessory', brand_name: 'Accessory', product_type: '显卡', model_name: 'NVIDIA L40S', title: 'NVIDIA L40S', specifications: [], compatible_gpus: [] },
}
const summaries = Object.values(details).map(({ specifications, compatible_gpus, source_ref, ...item }) => item)

async function run(viewport, label) {
  const browser = await chromium.launch({ headless: true })
  const page = await browser.newPage({ viewportSize: viewport })
  const errors = [], failed = [], badResponses = []
  page.on('console', (msg) => { if (msg.type() === 'error') errors.push(msg.text()) })
  page.on('pageerror', (err) => errors.push(err.message))
  page.on('requestfailed', (req) => failed.push(`${req.method()} ${req.url()} ${req.failure()?.errorText}`))
  page.on('response', (res) => { if (res.status() >= 400) badResponses.push(`${res.status()} ${res.url()}`) })
  await page.route('**/api/v1/**', async (route) => {
    const url = new URL(route.request().url())
    let body
    if (url.pathname === '/api/v1/brands') body = [{ code: 'mock', name: 'MockBrand', model_count: 3 }, { code: 'accessory', name: 'Accessory', model_count: 2 }]
    else if (url.pathname === '/api/v1/series') body = []
    else if (url.pathname === '/api/v1/models') body = summaries.filter((item) => !url.searchParams.get('brand_code') || item.brand_code === url.searchParams.get('brand_code'))
    else {
      const match = url.pathname.match(/^\/api\/v1\/models\/(\d+)$/)
      if (!match || !details[match[1]]) return route.fulfill({ status: 404, json: { detail: 'missing mock' } })
      body = details[match[1]]
    }
    await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(body) })
  })
  await page.goto('http://127.0.0.1:4179', { waitUntil: 'networkidle' })
  await page.getByText('BOUND-SERVER', { exact: true }).last().click()
  await page.waitForSelector('.compatible-gpu-link')
  const text = await page.locator('.product-body').innerText()
  if (!text.includes('显卡') || text.includes('兼容显卡型号') || text.includes('历史静态型号')) throw new Error(`${label}: bound rendering incorrect: ${text}`)
  if (await page.locator('.compatible-gpu-link').allTextContents().then((v) => v.join('|')) !== 'NVIDIA L20|NVIDIA L40S') throw new Error(`${label}: multi GPU incorrect`)
  await page.getByText('STATIC-SERVER', { exact: true }).last().click()
  await page.waitForFunction(() => document.body.innerText.includes('历史静态型号'))
  await page.getByRole('button', { name: '加入对比' }).click()
  await page.getByText('BOUND-SERVER', { exact: true }).last().click()
  await page.getByRole('button', { name: '加入对比' }).click()
  await page.getByRole('button', { name: '开始对比' }).click()
  await page.waitForSelector('.compare-modal')
  const compare = await page.locator('.compare-table').innerText()
  if (!compare.includes('NVIDIA L20；NVIDIA L40S') && !compare.includes('NVIDIA L20; NVIDIA L40S')) throw new Error(`${label}: bound compare projection incorrect: ${compare}`)
  if (!compare.includes('历史静态型号')) throw new Error(`${label}: static compare fallback incorrect: ${compare}`)
  await page.getByRole('button', { name: '关闭' }).click()

  await page.getByText('NO-GPU-GROUP', { exact: true }).last().click()
  await page.waitForFunction(() => document.body.innerText.includes('NVIDIA L20'))
  const generatedGroup = await page.locator('.spec-group').filter({ has: page.getByText('NVIDIA L20', { exact: true }) }).first().innerText()
  if (!generatedGroup.includes('GPU') || !generatedGroup.includes('显卡')) throw new Error(`${label}: generated GPU group missing`)
  await page.getByRole('button', { name: 'NVIDIA L20' }).click()
  await page.waitForFunction(() => document.body.innerText.includes('NVIDIA L20'))

  if (errors.length || failed.length || badResponses.length) throw new Error(`${label}: browser errors=${JSON.stringify({ errors, failed, badResponses })}`)
  await page.screenshot({ path: `self-review/browser-${label}.png`, fullPage: true })
  console.log(`PASS ${label} viewport=${viewport.width}x${viewport.height} consoleErrors=0 requestFailed=0 httpErrors=0`)
  await browser.close()
}

await run({ width: 1440, height: 1000 }, 'desktop')
await run({ width: 390, height: 844 }, 'mobile-390')
console.log('BROWSER_QA_PASS')
