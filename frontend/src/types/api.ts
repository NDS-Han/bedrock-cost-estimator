export type Family = 'HAIKU' | 'SONNET' | 'OPUS' | 'OTHER'
export type Category = 'input' | 'output' | 'cacheRead' | 'cacheWrite'

export interface ModelPrice {
  modelId: string
  displayName: string
  family: Family
  inputCostPerToken: string
  outputCostPerToken: string
  cacheReadCostPerToken: string
  cacheWriteCostPerToken: string
}

export interface Ratios {
  input: number
  output: number
  cacheRead: number
  cacheWrite: number
}

export interface PresetLevel {
  label: string
  description: string
  dailyTotalTokens: number
  tokenRatios: Ratios
  modelRatios: { haiku: number; sonnet: number; opus: number }
}

export interface Presets {
  references: { claudeCode: Record<string, number | string> }
  workloads: Record<string, { label: string; levels: Record<string, PresetLevel> }>
  metadata: { notice: string }
}

export interface ExchangeRate {
  rate: string
  effectiveDate: string
  source: string
}

export interface SyncStatus {
  status: 'never' | 'success' | 'failure'
  completedAt?: string
  fetchedCount?: number
  storedCount?: number
}

export interface EstimateResult {
  breakdown: Array<{
    modelId: string
    family: Family
    category: Category
    tokens: string
    pricePerToken: string
    costUsd: string
  }>
  perUserDailyUsd: string
  perUserMonthlyUsd: string
  totalMonthlyUsd: string
  totalAnnualUsd: string
}
