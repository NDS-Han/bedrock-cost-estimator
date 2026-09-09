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
          modelRatios: { sonnet: 80, opus: 20 },
        },
      },
    },
  },
}
const models = [
  { modelId: 'sonnet', displayName: 'Sonnet', family: 'SONNET' },
  { modelId: 'opus', displayName: 'Opus', family: 'OPUS' },
]

beforeEach(() => {
  sessionStorage.clear()
  fetchMock.mockReset()
  fetchMock
    .mockResolvedValueOnce({ ok: true, json: async () => presets })
    .mockResolvedValueOnce({ ok: true, json: async () => models })
})

describe('App', () => {
  it('shows all cache ratios and switches manual edits to Custom', async () => {
    const wrapper = mount(App)
    await flushPromises()

    expect(wrapper.text()).toContain('Cache read %')
    expect(wrapper.text()).toContain('Cache write %')
    const cacheRead = wrapper.find('input[min="0"]')
    await cacheRead.setValue(70)

    expect((wrapper.findAll('select')[1].element as HTMLSelectElement).value).toBe('custom')
  })

  it('persists estimator values in session storage', async () => {
    const wrapper = mount(App)
    await flushPromises()
    const users = wrapper.findAll('input[type="number"]')[3]
    await users.setValue(42)

    expect(JSON.parse(sessionStorage.getItem('bedrock-estimator') ?? '{}').userCount).toBe(42)
  })
})
