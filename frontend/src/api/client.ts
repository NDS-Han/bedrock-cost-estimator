import type { ExchangeRate, EstimateResult, ModelPrice, Presets, Ratios, SyncStatus } from '../types/api'

const API = '/api/v1'

async function json<T>(path: string, options?: RequestInit): Promise<T> {
  const response = await fetch(`${API}${path}`, options)
  if (!response.ok) throw new Error(`요청에 실패했습니다 (${response.status})`)
  return response.json() as Promise<T>
}

export const getPresets = () => json<Presets>('/presets')
export const getExchangeRate = () => json<ExchangeRate>('/exchange-rate')
export const getModels = () => json<ModelPrice[]>('/models')
export const getSyncStatus = () => json<SyncStatus>('/prices/sync-status')
export const syncPrices = () => json<{ storedCount: number }>('/prices/sync', { method: 'POST' })

export function estimate(payload: {
  dailyTotalTokens: number
  activeDaysPerMonth: number
  userCount: number
  tokenRatios: Ratios
  models: Array<{ modelId: string; family: string; percentage: number }>
}) {
  return json<EstimateResult>('/estimates', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  })
}
