import { flushPromises, mount } from '@vue/test-utils'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import App from './App.vue'

const fetchMock = vi.fn()
vi.stubGlobal('fetch', fetchMock)

const presets = {
  references: { claudeCode: { averageDailyUsd: 13, monthlyMinUsd: 150, monthlyMaxUsd: 250 } },
  metadata: { notice: '가정값입니다.' },
  workloads: {
    codingAgent: {
      label: '개발·코딩 에이전트',
      levels: {
        general: {
          label: 'General', description: '일상 사용', dailyTotalTokens: 75000000,
          tokenRatios: { input: 10, output: 5, cacheRead: 75, cacheWrite: 10 },
          modelRatios: { haiku: 10, sonnet: 75, opus: 15 },
        },
      },
    },
  },
}
const priceFields = {
  inputCostPerToken: '0.000003', outputCostPerToken: '0.000015',
  cacheReadCostPerToken: '0.0000003', cacheWriteCostPerToken: '0.00000375',
}
const models = [
  { modelId: 'haiku', displayName: 'Haiku', family: 'HAIKU', ...priceFields },
  { modelId: 'sonnet', displayName: 'Sonnet', family: 'SONNET', ...priceFields },
  { modelId: 'opus', displayName: 'Opus', family: 'OPUS', ...priceFields },
  { modelId: 'nova', displayName: 'Nova', family: 'OTHER', ...priceFields },
]

beforeEach(() => {
  sessionStorage.clear()
  fetchMock.mockReset()
  fetchMock
    .mockResolvedValueOnce({ ok: true, json: async () => presets })
    .mockResolvedValueOnce({ ok: true, json: async () => models })
    .mockResolvedValueOnce({ ok: true, json: async () => ({ status: 'success', completedAt: '2026-09-09T04:00:00Z', storedCount: 15 }) })
})

describe('App', () => {
  it('shows the latest successful price synchronization as a tag', async () => {
    const wrapper = mount(App)
    await flushPromises()

    expect(wrapper.get('.sync-tag').text()).toBe('Last Sync: 2026.09.09')
    expect(wrapper.get('.secondary').text()).toContain('Prices Sync')
  })

  it('shows all cache ratios and switches manual edits to Custom', async () => {
    const wrapper = mount(App)
    await flushPromises()

    expect(wrapper.text()).toContain('Cache read %')
    expect(wrapper.text()).toContain('Cache write %')
    const cacheRead = wrapper.find('input[min="0"]')
    await cacheRead.setValue(70)

    expect((wrapper.findAll('select')[1].element as HTMLSelectElement).value).toBe('custom')
  })

  it('opens the selected model price table in a modal', async () => {
    const wrapper = mount(App, { attachTo: document.body })
    await flushPromises()

    await wrapper.get('[aria-label="Haiku 모델 단가 보기"]').trigger('click')

    expect(document.body.textContent).toContain('1M 토큰 기준 단가')
    expect(document.body.textContent).toContain('$3.00')
    wrapper.unmount()
  })

  it('groups cost details by model with a subtotal', async () => {
    fetchMock.mockResolvedValueOnce({
      ok: true,
      json: async () => ({
        perUserDailyUsd: '10', perUserMonthlyUsd: '200', totalMonthlyUsd: '6000', totalAnnualUsd: '72000',
        breakdown: [
          { modelId: 'haiku', family: 'HAIKU', category: 'input', tokens: '100', pricePerToken: '0.01', costUsd: '1' },
          { modelId: 'haiku', family: 'HAIKU', category: 'output', tokens: '100', pricePerToken: '0.02', costUsd: '2' },
          { modelId: 'sonnet', family: 'SONNET', category: 'input', tokens: '100', pricePerToken: '0.03', costUsd: '3' },
        ],
      }),
    })
    const wrapper = mount(App)
    await flushPromises()

    await wrapper.get('form').trigger('submit')
    await flushPromises()

    const groups = wrapper.findAll('[data-testid="model-cost-group"]')
    expect(groups).toHaveLength(2)
    expect(groups[0].text()).toContain('Haiku')
    expect(groups[0].text()).toContain('$3.00')
  })

  it('adds an optional model row from the collapsed control', async () => {
    const wrapper = mount(App)
    await flushPromises()

    await wrapper.get('.add-model').trigger('click')

    expect(wrapper.findAll('.extra-model')).toHaveLength(1)
    expect(wrapper.text()).toContain('추가 모델')
  })

  it('persists estimator values in session storage', async () => {
    const wrapper = mount(App)
    await flushPromises()
    const users = wrapper.findAll('input[type="number"]')[3]
    await users.setValue(42)

    expect(JSON.parse(sessionStorage.getItem('bedrock-estimator') ?? '{}').userCount).toBe(42)
  })
})
