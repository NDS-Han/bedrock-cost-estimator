<script setup lang="ts">
import { computed, nextTick, onMounted, reactive, ref, watch } from 'vue'
import { cohortEstimate, estimate, getExchangeRate, getModels, getPresets, getSyncStatus, syncPrices } from './api/client'
import { language, setLanguage, t, tm } from './i18n'
import type { CohortEstimateResult, EstimateResult, ModelPrice, Presets, Ratios, SyncStatus } from './types/api'

const presets = ref<Presets>()
const models = ref<ModelPrice[]>([])
const result = ref<EstimateResult>()
const cohortResult = ref<CohortEstimateResult>()
const isEstimateStale = ref(false)
const priceSyncStatus = ref<SyncStatus>()
const error = ref('')
const busy = ref(false)
const currency = ref<'USD' | 'KRW'>('USD')
const modalModel = ref<ModelPrice>()
const modalClose = ref<HTMLButtonElement>()
interface EstimatorState {
  workload: string
  estimateMode: 'single' | 'cohort'
  intensity: string
  cohortRatios: { lite: number; general: number; heavy: number }
  cohortTokens: { lite: number; general: number; heavy: number }
  dailyTotalTokens: number
  activeDaysPerMonth: number
  userCount: number
  exchangeRate: number
  exchangeRateMode: 'auto' | 'manual'
  exchangeRateDate: string
  ratios: Ratios
  haikuPercentage: number
  sonnetPercentage: number
  opusPercentage: number
  haikuId: string
  sonnetId: string
  opusId: string
  additionalModels: Array<{ modelId: string; percentage: number }>
}

const stored = sessionStorage.getItem('bedrock-estimator')
const defaults: EstimatorState = {
  workload: 'codingAgent', estimateMode: 'single', intensity: 'general',
  cohortRatios: { lite: 70, general: 0, heavy: 30 },
  cohortTokens: { lite: 1500000, general: 4500000, heavy: 9000000 }, dailyTotalTokens: 4500000,
  activeDaysPerMonth: 20, userCount: 30, exchangeRate: 1400,
  exchangeRateMode: 'auto', exchangeRateDate: '',
  ratios: { input: 10, output: 5, cacheRead: 75, cacheWrite: 10 } as Ratios,
  haikuPercentage: 10, sonnetPercentage: 75, opusPercentage: 15,
  haikuId: '', sonnetId: '', opusId: '',
  additionalModels: [] as Array<{ modelId: string; percentage: number }>,
}
const restored = stored ? JSON.parse(stored) as Partial<EstimatorState> : {}
const state = reactive<EstimatorState>({ ...defaults, ...restored })
const intensities = ['lite', 'general', 'heavy'] as const

const haikuModels = computed(() => models.value.filter((model) => model.family === 'HAIKU'))
const sonnetModels = computed(() => models.value.filter((model) => model.family === 'SONNET'))
const opusModels = computed(() => models.value.filter((model) => model.family === 'OPUS'))
const tokenTotal = computed(() => Object.values(state.ratios as Ratios).reduce((a, b) => a + Number(b), 0))
const modelTotal = computed(() => Number(state.haikuPercentage) + Number(state.sonnetPercentage) + Number(state.opusPercentage) + state.additionalModels.reduce((sum, model) => sum + Number(model.percentage), 0))
const selectedModelIds = computed(() => [state.haikuId, state.sonnetId, state.opusId, ...state.additionalModels.map((model) => model.modelId)].filter(Boolean))
const hasUniqueModels = computed(() => new Set(selectedModelIds.value).size === selectedModelIds.value.length)
const cohortTotal = computed(() => Object.values(state.cohortRatios).reduce((sum, value) => sum + Number(value), 0))
const cohortTokensValid = computed(() => intensities.every((intensity) => state.cohortRatios[intensity] <= 0 || Number(state.cohortTokens[intensity]) > 0))
const valid = computed(() => state.estimateMode === 'cohort'
  ? cohortTotal.value === 100 && cohortTokensValid.value && tokenTotal.value === 100 && modelTotal.value === 100 && hasUniqueModels.value && state.userCount > 0 && state.activeDaysPerMonth > 0 && Boolean(state.haikuId && state.sonnetId && state.opusId)
  : tokenTotal.value === 100 && modelTotal.value === 100 && hasUniqueModels.value && state.dailyTotalTokens > 0 && state.userCount > 0)
const estimateSignature = computed(() => JSON.stringify({
  workload: state.workload,
  estimateMode: state.estimateMode,
  cohortRatios: state.cohortRatios,
  cohortTokens: state.cohortTokens,
  dailyTotalTokens: state.dailyTotalTokens,
  activeDaysPerMonth: state.activeDaysPerMonth,
  userCount: state.userCount,
  ratios: state.ratios,
  models: [
    state.haikuId, state.haikuPercentage,
    state.sonnetId, state.sonnetPercentage,
    state.opusId, state.opusPercentage,
    state.additionalModels,
  ],
}))
const reference = computed(() => presets.value?.references.claudeCode)
const rateSource = computed(() => state.exchangeRateMode === 'manual'
  ? t('manualRate')
  : state.exchangeRateDate ? `Frankfurter · ${state.exchangeRateDate}` : t('fetchingRate'))
const notice = computed(() => language.value === 'ko'
  ? (presets.value?.metadata.notice ?? t('defaultNotice'))
  : t('defaultNotice'))
const totalMonthlyUsd = computed(() => state.estimateMode === 'cohort' ? cohortResult.value?.totalMonthlyUsd : result.value?.totalMonthlyUsd)
const totalAnnualUsd = computed(() => state.estimateMode === 'cohort' ? cohortResult.value?.totalAnnualUsd : result.value?.totalAnnualUsd)
const perUserMonthlyUsd = computed(() => {
  if (state.estimateMode === 'single') return result.value?.perUserMonthlyUsd
  return cohortResult.value ? String(Number(cohortResult.value.totalMonthlyUsd) / state.userCount) : undefined
})
const perUserDailyUsd = computed(() => perUserMonthlyUsd.value
  ? String(Number(perUserMonthlyUsd.value) / state.activeDaysPerMonth)
  : undefined)
function groupBreakdown(items: EstimateResult['breakdown']) {
  const groups = new Map<string, EstimateResult['breakdown']>()
  for (const item of items) {
    groups.set(item.modelId, [...(groups.get(item.modelId) ?? []), item])
  }
  return [...groups.entries()].map(([modelId, modelItems]) => ({
    modelId,
    displayName: selectedModel(modelId)?.displayName ?? modelId,
    family: modelItems[0].family,
    items: modelItems,
    totalUsd: String(modelItems.reduce((sum, item) => sum + Number(item.costUsd), 0)),
  }))
}
const groupedBreakdown = computed(() => groupBreakdown(result.value?.breakdown ?? []))

function applyPreset() {
  if (state.intensity === 'custom' || !presets.value) return
  const levels = presets.value.workloads[state.workload].levels
  const preset = levels[state.intensity]
  state.dailyTotalTokens = preset.dailyTotalTokens
  for (const intensity of intensities) {
    state.cohortTokens[intensity] = levels[intensity].dailyTotalTokens
  }
  state.ratios = { ...preset.tokenRatios }
  state.haikuPercentage = preset.modelRatios.haiku
  state.sonnetPercentage = preset.modelRatios.sonnet
  state.opusPercentage = preset.modelRatios.opus
  state.additionalModels = []
}

function addModel() {
  const candidate = models.value.find((model) => !selectedModelIds.value.includes(model.modelId))
  if (candidate) state.additionalModels.push({ modelId: candidate.modelId, percentage: 0 })
  markCustom()
}
function removeModel(index: number) {
  state.additionalModels.splice(index, 1)
  markCustom()
}
function selectedModel(modelId: string) {
  return models.value.find((model) => model.modelId === modelId)
}
function modelFamily(modelId: string) {
  return selectedModel(modelId)?.family ?? 'OTHER'
}
function workloadLabel(key: string, fallback: string) {
  return tm(`workload.${key}`) ?? fallback
}
async function openPrice(modelId: string) {
  modalModel.value = selectedModel(modelId)
  await nextTick()
  modalClose.value?.focus()
}
function closePrice() { modalModel.value = undefined }
function perMillion(value: string) {
  return new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD', currencyDisplay: 'narrowSymbol' }).format(Number(value) * 1_000_000)
}

async function loadExchangeRate(force = false) {
  try {
    const latest = await getExchangeRate()
    if (force || state.exchangeRateMode === 'auto') {
      state.exchangeRate = Number(latest.rate)
      state.exchangeRateMode = 'auto'
      state.exchangeRateDate = latest.effectiveDate
    }
  } catch {
    state.exchangeRateMode = 'manual'
  }
}
function markRateManual() { state.exchangeRateMode = 'manual' }
function markCustom() { state.intensity = 'custom' }
function money(value: string) {
  const amount = Number(value) * (currency.value === 'KRW' ? Number(state.exchangeRate) : 1)
  return new Intl.NumberFormat(currency.value === 'USD' ? 'en-US' : 'ko-KR', { style: 'currency', currency: currency.value, currencyDisplay: 'narrowSymbol', maximumFractionDigits: currency.value === 'KRW' ? 0 : 2 }).format(amount)
}
function tokens(value: string) { return new Intl.NumberFormat(language.value === 'ko' ? 'ko-KR' : 'en-US', { maximumFractionDigits: 0 }).format(Number(value)) }
function syncDate(value: string) {
  const date = new Date(value)
  return [date.getFullYear(), date.getMonth() + 1, date.getDate()]
    .map((part, index) => index === 0 ? String(part) : String(part).padStart(2, '0'))
    .join('.')
}
function categoryLabel(category: string) {
  return { input: 'Input', output: 'Output', cacheRead: 'Cache read', cacheWrite: 'Cache write' }[category] ?? category
}
function modelAllocations() {
  return [
    { modelId: state.haikuId, family: 'HAIKU', percentage: Number(state.haikuPercentage) },
    { modelId: state.sonnetId, family: 'SONNET', percentage: Number(state.sonnetPercentage) },
    { modelId: state.opusId, family: 'OPUS', percentage: Number(state.opusPercentage) },
    ...state.additionalModels.map((model) => ({
      modelId: model.modelId,
      family: modelFamily(model.modelId),
      percentage: Number(model.percentage),
    })),
  ]
}

async function calculate() {
  if (!valid.value || !state.haikuId || !state.sonnetId || !state.opusId) return
  busy.value = true
  error.value = ''
  try {
    if (state.estimateMode === 'cohort' && presets.value) {
      cohortResult.value = await cohortEstimate({
        activeDaysPerMonth: Number(state.activeDaysPerMonth),
        userCount: Number(state.userCount),
        cohorts: (['lite', 'general', 'heavy'] as const)
          .filter((intensity) => state.cohortRatios[intensity] > 0)
          .map((intensity) => ({
            intensity,
            percentage: state.cohortRatios[intensity],
            dailyTotalTokens: Number(state.cohortTokens[intensity]),
            tokenRatios: state.ratios,
            models: modelAllocations(),
          })),
      })
    } else {
      result.value = await estimate({
        dailyTotalTokens: Number(state.dailyTotalTokens), activeDaysPerMonth: Number(state.activeDaysPerMonth),
        userCount: Number(state.userCount), tokenRatios: state.ratios,
        models: modelAllocations(),
      })
    }
    isEstimateStale.value = false
  } catch (reason) { error.value = reason instanceof Error ? reason.message : t('errorCalculate') }
  finally { busy.value = false }
}

async function synchronize() {
  busy.value = true
  error.value = ''
  try { await syncPrices(); await loadModels(); priceSyncStatus.value = await getSyncStatus() }
  catch (reason) { error.value = reason instanceof Error ? reason.message : t('errorSync') }
  finally { busy.value = false }
}
async function loadModels() {
  models.value = await getModels()
  state.haikuId ||= haikuModels.value[haikuModels.value.length - 1]?.modelId ?? ''
  state.sonnetId ||= sonnetModels.value[sonnetModels.value.length - 1]?.modelId ?? ''
  state.opusId ||= opusModels.value[opusModels.value.length - 1]?.modelId ?? ''
}

watch(state, () => sessionStorage.setItem('bedrock-estimator', JSON.stringify(state)), { deep: true })
watch(estimateSignature, () => { if (result.value || cohortResult.value) isEstimateStale.value = true })
watch(() => [state.workload, state.intensity], applyPreset)
watch(language, (lang) => {
  document.documentElement.lang = lang
  document.title = t('documentTitle')
}, { immediate: true })
onMounted(async () => {
  try { presets.value = await getPresets(); applyPreset(); await loadModels(); priceSyncStatus.value = await getSyncStatus(); await loadExchangeRate() }
  catch (reason) { error.value = reason instanceof Error ? reason.message : t('errorLoad') }
})
</script>

<template>
  <header class="topbar">
    <div><span class="eyebrow">AWS BEDROCK</span><h1>{{ t('appTitle') }}</h1></div>
    <div class="currency-control">
      <div class="lang-toggle" role="group" :aria-label="t('languageGroup')">
        <button type="button" :class="{ active: language === 'ko' }" :aria-pressed="language === 'ko'" @click="setLanguage('ko')">KO</button>
        <button type="button" :class="{ active: language === 'en' }" :aria-pressed="language === 'en'" @click="setLanguage('en')">EN</button>
      </div>
      <label for="exchange">{{ t('exchangeRateLabel') }}<input id="exchange" v-model.number="state.exchangeRate" type="number" min="1" step="0.01" inputmode="decimal" @input="markRateManual"><small class="rate-source">{{ rateSource }}</small></label>
      <button class="rate-refresh" type="button" :aria-label="t('refreshRate')" @click="loadExchangeRate(true)">↻</button>
      <button type="button" :disabled="state.exchangeRate <= 0" @click="currency = currency === 'USD' ? 'KRW' : 'USD'">
        {{ currency === 'USD' ? t('toKrw') : t('toUsd') }}
      </button>
    </div>
  </header>

  <main>
    <section class="intro">
      <div><p class="kicker">Planning workspace</p><h2>Calculate Bedrock Price</h2></div>
      <div class="sync-control">
        <button class="secondary sync-button" type="button" :disabled="busy" @click="synchronize">
          <span class="sync-icon" :class="{ spinning: busy }" aria-hidden="true"><svg viewBox="0 0 24 24"><path d="M20 7v5h-5"/><path d="M4 17v-5h5"/><path d="M6.1 9a7 7 0 0 1 11.6-2L20 12"/><path d="m4 12 2.3 5a7 7 0 0 0 11.6-2"/></svg></span>
          <span><strong>{{ busy ? 'Syncing…' : 'Prices Sync' }}</strong><small>LiteLLM catalog</small></span>
        </button>
        <span v-if="models.length && priceSyncStatus?.status === 'success' && priceSyncStatus.completedAt" class="sync-tag">Last Sync: {{ syncDate(priceSyncStatus.completedAt) }}</span>
      </div>
    </section>

    <p v-if="error" class="alert" role="alert">{{ error }}</p>
    <div class="layout">
      <form class="panel form-panel" @submit.prevent="calculate">
        <section>
          <div class="section-heading"><span>01</span><h3>{{ t('scenario') }}</h3></div>
          <label>{{ t('workloadType') }}<select v-model="state.workload"><option v-for="(item, key) in presets?.workloads" :key="key" :value="key">{{ workloadLabel(String(key), item.label) }}</option></select></label>
          <div class="mode-tabs" role="tablist" :aria-label="t('estimateMode')">
            <button type="button" role="tab" :aria-selected="state.estimateMode === 'single'" :class="{ active: state.estimateMode === 'single' }" @click="state.estimateMode = 'single'">{{ t('singleMode') }}</button>
            <button type="button" role="tab" :aria-selected="state.estimateMode === 'cohort'" :class="{ active: state.estimateMode === 'cohort' }" @click="state.estimateMode = 'cohort'">{{ t('cohortMode') }}</button>
          </div>
          <label v-if="state.estimateMode === 'single'">{{ t('intensity') }}<select v-model="state.intensity"><option v-for="(item, key) in presets?.workloads[state.workload]?.levels" :key="key" :value="key">{{ item.label }}</option><option value="custom">{{ t('custom') }}</option></select></label>
        </section>

        <section>
          <div class="section-heading"><span>02</span><h3>{{ t('usageSection') }}</h3></div>
          <div :class="state.estimateMode === 'single' ? 'three-col' : 'two-col'">
            <label v-if="state.estimateMode === 'single'">{{ t('dailyTokensPerUser') }}<input v-model.number="state.dailyTotalTokens" type="number" min="1" @input="markCustom"></label>
            <label>{{ t('activeDaysPerMonth') }}<input v-model.number="state.activeDaysPerMonth" type="number" min="1" max="31"></label>
            <label>{{ t('totalUsers') }}<input v-model.number="state.userCount" type="number" min="1"></label>
          </div>
        </section>

        <section v-if="state.estimateMode === 'cohort'" role="tabpanel">
          <div class="section-heading"><span>03</span><h3>{{ t('intensityMix') }}</h3><strong :class="{ invalid: cohortTotal !== 100 }">{{ t('totalPct', { n: cohortTotal }) }}</strong></div>
          <div class="cohort-editor">
            <div v-for="intensity in intensities" :key="intensity" class="cohort-row">
              <div><strong>{{ presets?.workloads[state.workload]?.levels[intensity].label }}</strong><small>{{ t('approxUsers', { n: (state.userCount * state.cohortRatios[intensity] / 100).toFixed(1) }) }}</small></div>
              <label class="cohort-tokens">{{ t('dailyTokens') }}<input v-model.number="state.cohortTokens[intensity]" type="number" min="1" @input="markCustom"></label>
              <label><span class="sr-only">{{ t('intensityShare', { intensity }) }}</span><span class="percentage-input"><input v-model.number="state.cohortRatios[intensity]" type="number" min="0" max="100"><b>%</b></span></label>
            </div>
          </div>
        </section>

        <section>
          <div class="section-heading"><span>{{ state.estimateMode === 'single' ? '03' : '04' }}</span><h3>{{ t('tokenMix') }}</h3><strong :class="{ invalid: tokenTotal !== 100 }">{{ t('totalPct', { n: tokenTotal }) }}</strong></div>
          <div class="four-col">
            <label>Input %<input v-model.number="state.ratios.input" type="number" min="0" max="100" @input="markCustom"></label>
            <label>Output %<input v-model.number="state.ratios.output" type="number" min="0" max="100" @input="markCustom"></label>
            <label>Cache read %<input v-model.number="state.ratios.cacheRead" type="number" min="0" max="100" @input="markCustom"></label>
            <label>Cache write %<input v-model.number="state.ratios.cacheWrite" type="number" min="0" max="100" @input="markCustom"></label>
          </div>
        </section>

        <section>
          <div class="section-heading"><span>{{ state.estimateMode === 'single' ? '04' : '05' }}</span><h3>{{ t('modelMix') }}</h3><strong :class="{ invalid: modelTotal !== 100 }">{{ t('totalPct', { n: modelTotal }) }}</strong></div>
          <p v-if="state.estimateMode === 'cohort'" class="hint">{{ t('cohortMixHint') }}</p>
          <div class="model-row"><label>{{ t('lightModel') }}<span class="model-select-control"><select v-model="state.haikuId"><option v-for="model in haikuModels" :key="model.modelId" :value="model.modelId">{{ model.displayName }}</option></select><button type="button" :aria-label="t('viewHaikuPrice')" @click="openPrice(state.haikuId)"><svg aria-hidden="true" viewBox="0 0 24 24"><circle cx="11" cy="11" r="7"/><path d="m16 16 5 5"/></svg></button></span></label><label>{{ t('sharePct') }}<input v-model.number="state.haikuPercentage" type="number" min="0" max="100" @input="markCustom"></label></div>
          <div class="model-row"><label>{{ t('standardModel') }}<span class="model-select-control"><select v-model="state.sonnetId"><option v-for="model in sonnetModels" :key="model.modelId" :value="model.modelId">{{ model.displayName }}</option></select><button type="button" :aria-label="t('viewSonnetPrice')" @click="openPrice(state.sonnetId)"><svg aria-hidden="true" viewBox="0 0 24 24"><circle cx="11" cy="11" r="7"/><path d="m16 16 5 5"/></svg></button></span></label><label>{{ t('sharePct') }}<input v-model.number="state.sonnetPercentage" type="number" min="0" max="100" @input="markCustom"></label></div>
          <div class="model-row"><label>{{ t('advancedModel') }}<span class="model-select-control"><select v-model="state.opusId"><option v-for="model in opusModels" :key="model.modelId" :value="model.modelId">{{ model.displayName }}</option></select><button type="button" :aria-label="t('viewOpusPrice')" @click="openPrice(state.opusId)"><svg aria-hidden="true" viewBox="0 0 24 24"><circle cx="11" cy="11" r="7"/><path d="m16 16 5 5"/></svg></button></span></label><label>{{ t('sharePct') }}<input v-model.number="state.opusPercentage" type="number" min="0" max="100" @input="markCustom"></label></div>
          <div v-for="(extra, index) in state.additionalModels" :key="index" class="model-row extra-model">
            <label>{{ t('additionalModel') }}<span class="model-select-control"><select v-model="extra.modelId" @change="markCustom"><option v-for="model in models" :key="model.modelId" :value="model.modelId">{{ model.displayName }}</option></select><button type="button" :aria-label="t('viewAdditionalPrice')" @click="openPrice(extra.modelId)"><svg aria-hidden="true" viewBox="0 0 24 24"><circle cx="11" cy="11" r="7"/><path d="m16 16 5 5"/></svg></button></span></label>
            <label>{{ t('sharePct') }}<span class="percentage-action"><input v-model.number="extra.percentage" type="number" min="0" max="100" @input="markCustom"><button type="button" :aria-label="t('removeModelAria')" @click="removeModel(index)">{{ t('remove') }}</button></span></label>
          </div>
          <button class="add-model" type="button" :disabled="selectedModelIds.length >= models.length" @click="addModel">{{ t('addModel') }}</button>
          <p v-if="!hasUniqueModels" class="validation" role="alert">{{ t('duplicateModel') }}</p>
          <p v-if="!models.length" class="hint">{{ t('noPrices') }}</p>
        </section>
        <button class="primary" type="submit" :disabled="!valid || busy || !models.length">{{ busy ? t('processing') : isEstimateStale ? t('recalculate') : t('calculate') }}</button>
      </form>

      <aside class="results" aria-live="polite">
        <section class="result-hero" :class="{ stale: isEstimateStale }"><div class="result-label"><p>{{ t('annualCost') }}</p><span v-if="isEstimateStale" class="stale-flag">{{ t('staleFlag') }}</span></div><strong>{{ totalAnnualUsd ? money(totalAnnualUsd) : '—' }}</strong><small>{{ t('usersDaysBasis', { users: state.userCount, days: state.activeDaysPerMonth }) }}</small></section>
        <section class="panel metrics"><div><span>{{ t('perUserActiveDay') }}</span><b>{{ perUserDailyUsd ? money(perUserDailyUsd) : '—' }}</b></div><div><span>{{ t('perUserMonth') }}</span><b>{{ perUserMonthlyUsd ? money(perUserMonthlyUsd) : '—' }}</b></div><div><span>{{ t('totalMonth') }}</span><b>{{ totalMonthlyUsd ? money(totalMonthlyUsd) : '—' }}</b></div></section>
        <section v-if="state.workload === 'codingAgent' && reference" class="reference"><span>ANTHROPIC REFERENCE</span><p v-html="t('referenceLine', { daily: reference.averageDailyUsd, min: reference.monthlyMinUsd, max: reference.monthlyMaxUsd })"></p><small>{{ t('referenceNote') }}</small></section>
        <section v-if="state.estimateMode === 'cohort' && cohortResult" class="panel breakdown cohort-results">
          <div class="breakdown-heading"><div><span>COHORT BREAKDOWN</span><h3>{{ t('cohortCostTitle') }}</h3></div><small>{{ t('allUsersBasis') }}</small></div>
          <article v-for="cohort in cohortResult.cohorts" :key="cohort.intensity" class="cohort-cost-card">
            <header><div><strong>{{ presets?.workloads[state.workload]?.levels[cohort.intensity].label }}</strong><small>{{ t('cohortShare', { p: cohort.percentage, u: Number(cohort.effectiveUsers).toFixed(1) }) }}</small></div><b>{{ money(cohort.totalAnnualUsd) }}<small>{{ t('perYear') }}</small></b></header>
            <div class="cohort-cost-meta"><div><span>{{ t('perUserActiveDayBasis') }}</span><strong>{{ money(cohort.perUserDailyUsd) }}</strong></div><div><span>{{ t('cohortMonthTotal') }}</span><strong>{{ money(cohort.totalMonthlyUsd) }}</strong></div></div>
            <details class="cohort-details">
              <summary>{{ t('perModelDetails') }}</summary>
              <div class="cohort-model-breakdown">
                <article v-for="group in groupBreakdown(cohort.breakdown)" :key="group.modelId" class="model-cost-group">
                  <header><div><strong>{{ group.displayName }}</strong><small>{{ group.family }}</small></div><b>{{ money(group.totalUsd) }}</b></header>
                  <table><thead><tr><th>{{ t('tokenType') }}</th><th>{{ t('usageAmount') }}</th><th>{{ t('dailyCostPerUser') }}</th></tr></thead><tbody><tr v-for="item in group.items" :key="item.category"><td>{{ categoryLabel(item.category) }}</td><td>{{ tokens(item.tokens) }}</td><td>{{ money(item.costUsd) }}</td></tr></tbody></table>
                </article>
              </div>
            </details>
          </article>
        </section>
        <section v-if="state.estimateMode === 'single' && result" class="panel breakdown">
          <div class="breakdown-heading"><div><span>COST BREAKDOWN</span><h3>{{ t('modelCostTitle') }}</h3></div><small>{{ t('singleBasis') }}</small></div>
          <article v-for="group in groupedBreakdown" :key="group.modelId" class="model-cost-group" data-testid="model-cost-group">
            <header><div><strong>{{ group.displayName }}</strong><small>{{ group.family }}</small></div><b>{{ money(group.totalUsd) }}</b></header>
            <table><thead><tr><th>{{ t('tokenType') }}</th><th>{{ t('usageAmount') }}</th><th>{{ t('dailyCost') }}</th></tr></thead><tbody><tr v-for="item in group.items" :key="item.category"><td>{{ categoryLabel(item.category) }}</td><td>{{ tokens(item.tokens) }}</td><td>{{ money(item.costUsd) }}</td></tr></tbody></table>
          </article>
        </section>
        <p class="notice">{{ notice }}</p>
      </aside>
    </div>
  </main>
  <Teleport to="body">
    <div v-if="modalModel" class="modal-backdrop" role="presentation" @click="closePrice">
      <section class="price-modal" role="dialog" aria-modal="true" aria-labelledby="price-modal-title" @click.stop @keydown.esc="closePrice">
        <header><div><span>MODEL PRICE</span><h2 id="price-modal-title">{{ t('pricePerMillion') }}</h2></div><button ref="modalClose" type="button" :aria-label="t('closePriceModal')" @click="closePrice">×</button></header>
        <p class="model-id">{{ modalModel.displayName }}</p>
        <dl>
          <div><dt>Input</dt><dd>{{ perMillion(modalModel.inputCostPerToken) }}</dd></div>
          <div><dt>Output</dt><dd>{{ perMillion(modalModel.outputCostPerToken) }}</dd></div>
          <div><dt>Cache read</dt><dd>{{ perMillion(modalModel.cacheReadCostPerToken) }}</dd></div>
          <div><dt>Cache write</dt><dd>{{ perMillion(modalModel.cacheWriteCostPerToken) }}</dd></div>
        </dl>
        <p class="modal-note">{{ t('modalNote') }}</p>
      </section>
    </div>
  </Teleport>
</template>
