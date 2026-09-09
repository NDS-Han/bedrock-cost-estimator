<script setup lang="ts">
import { computed, nextTick, onMounted, reactive, ref, watch } from 'vue'
import { estimate, getModels, getPresets, syncPrices } from './api/client'
import type { EstimateResult, ModelPrice, Presets, Ratios } from './types/api'

const presets = ref<Presets>()
const models = ref<ModelPrice[]>([])
const result = ref<EstimateResult>()
const error = ref('')
const busy = ref(false)
const currency = ref<'USD' | 'KRW'>('USD')
const modalModel = ref<ModelPrice>()
const modalClose = ref<HTMLButtonElement>()
interface EstimatorState {
  workload: string
  intensity: string
  dailyTotalTokens: number
  activeDaysPerMonth: number
  userCount: number
  exchangeRate: number
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
  workload: 'codingAgent', intensity: 'general', dailyTotalTokens: 4500000,
  activeDaysPerMonth: 20, userCount: 30, exchangeRate: 1400,
  ratios: { input: 10, output: 5, cacheRead: 75, cacheWrite: 10 } as Ratios,
  haikuPercentage: 10, sonnetPercentage: 75, opusPercentage: 15,
  haikuId: '', sonnetId: '', opusId: '',
  additionalModels: [] as Array<{ modelId: string; percentage: number }>,
}
const restored = stored ? JSON.parse(stored) as Partial<EstimatorState> : {}
const state = reactive<EstimatorState>({ ...defaults, ...restored })

const haikuModels = computed(() => models.value.filter((model) => model.family === 'HAIKU'))
const sonnetModels = computed(() => models.value.filter((model) => model.family === 'SONNET'))
const opusModels = computed(() => models.value.filter((model) => model.family === 'OPUS'))
const tokenTotal = computed(() => Object.values(state.ratios as Ratios).reduce((a, b) => a + Number(b), 0))
const modelTotal = computed(() => Number(state.haikuPercentage) + Number(state.sonnetPercentage) + Number(state.opusPercentage) + state.additionalModels.reduce((sum, model) => sum + Number(model.percentage), 0))
const selectedModelIds = computed(() => [state.haikuId, state.sonnetId, state.opusId, ...state.additionalModels.map((model) => model.modelId)].filter(Boolean))
const hasUniqueModels = computed(() => new Set(selectedModelIds.value).size === selectedModelIds.value.length)
const valid = computed(() => tokenTotal.value === 100 && modelTotal.value === 100 && hasUniqueModels.value && state.dailyTotalTokens > 0 && state.userCount > 0)
const reference = computed(() => presets.value?.references.claudeCode)
const groupedBreakdown = computed(() => {
  const groups = new Map<string, NonNullable<typeof result.value>['breakdown']>()
  for (const item of result.value?.breakdown ?? []) {
    groups.set(item.modelId, [...(groups.get(item.modelId) ?? []), item])
  }
  return [...groups.entries()].map(([modelId, items]) => ({
    modelId,
    displayName: selectedModel(modelId)?.displayName ?? modelId,
    family: items[0].family,
    items,
    totalUsd: String(items.reduce((sum, item) => sum + Number(item.costUsd), 0)),
  }))
})

function applyPreset() {
  if (state.intensity === 'custom' || !presets.value) return
  const preset = presets.value.workloads[state.workload].levels[state.intensity]
  state.dailyTotalTokens = preset.dailyTotalTokens
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
async function openPrice(modelId: string) {
  modalModel.value = selectedModel(modelId)
  await nextTick()
  modalClose.value?.focus()
}
function closePrice() { modalModel.value = undefined }
function perMillion(value: string) {
  return new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD' }).format(Number(value) * 1_000_000)
}

function markCustom() { state.intensity = 'custom' }
function money(value: string) {
  const amount = Number(value) * (currency.value === 'KRW' ? Number(state.exchangeRate) : 1)
  return new Intl.NumberFormat('ko-KR', { style: 'currency', currency: currency.value, maximumFractionDigits: currency.value === 'KRW' ? 0 : 2 }).format(amount)
}
function tokens(value: string) { return new Intl.NumberFormat('ko-KR', { maximumFractionDigits: 0 }).format(Number(value)) }
function categoryLabel(category: string) {
  return { input: 'Input', output: 'Output', cacheRead: 'Cache read', cacheWrite: 'Cache write' }[category] ?? category
}

async function calculate() {
  if (!valid.value || !state.haikuId || !state.sonnetId || !state.opusId) return
  busy.value = true
  error.value = ''
  try {
    result.value = await estimate({
      dailyTotalTokens: Number(state.dailyTotalTokens), activeDaysPerMonth: Number(state.activeDaysPerMonth),
      userCount: Number(state.userCount), tokenRatios: state.ratios,
      models: [
        { modelId: state.haikuId, family: 'HAIKU', percentage: Number(state.haikuPercentage) },
        { modelId: state.sonnetId, family: 'SONNET', percentage: Number(state.sonnetPercentage) },
        { modelId: state.opusId, family: 'OPUS', percentage: Number(state.opusPercentage) },
        ...state.additionalModels.map((model) => ({
          modelId: model.modelId,
          family: modelFamily(model.modelId),
          percentage: Number(model.percentage),
        })),
      ],
    })
  } catch (reason) { error.value = reason instanceof Error ? reason.message : '계산할 수 없습니다.' }
  finally { busy.value = false }
}

async function synchronize() {
  busy.value = true
  error.value = ''
  try { await syncPrices(); await loadModels() }
  catch (reason) { error.value = reason instanceof Error ? reason.message : '가격을 동기화할 수 없습니다.' }
  finally { busy.value = false }
}
async function loadModels() {
  models.value = await getModels()
  state.haikuId ||= haikuModels.value[haikuModels.value.length - 1]?.modelId ?? ''
  state.sonnetId ||= sonnetModels.value[sonnetModels.value.length - 1]?.modelId ?? ''
  state.opusId ||= opusModels.value[opusModels.value.length - 1]?.modelId ?? ''
}

watch(state, () => sessionStorage.setItem('bedrock-estimator', JSON.stringify(state)), { deep: true })
watch(() => [state.workload, state.intensity], applyPreset)
onMounted(async () => {
  try { presets.value = await getPresets(); applyPreset(); await loadModels() }
  catch (reason) { error.value = reason instanceof Error ? reason.message : '초기 데이터를 불러올 수 없습니다.' }
})
</script>

<template>
  <header class="topbar">
    <div><span class="eyebrow">AWS BEDROCK</span><h1>사용량 비용 계산기</h1></div>
    <div class="currency-control">
      <label for="exchange">USD → KRW 환율</label>
      <input id="exchange" v-model.number="state.exchangeRate" type="number" min="1" inputmode="decimal">
      <button type="button" :disabled="state.exchangeRate <= 0" @click="currency = currency === 'USD' ? 'KRW' : 'USD'">
        {{ currency === 'USD' ? '원화로 변환' : '달러로 보기' }}
      </button>
    </div>
  </header>

  <main>
    <section class="intro">
      <div><p class="kicker">Planning workspace</p><h2>토큰 사용량으로 연간 예산을 가늠하세요.</h2><p>LiteLLM 단가를 Sync합니다.</p></div>
      <button class="secondary" type="button" :disabled="busy" @click="synchronize">관리자 가격 동기화</button>
    </section>

    <p v-if="error" class="alert" role="alert">{{ error }}</p>
    <div class="layout">
      <form class="panel form-panel" @submit.prevent="calculate">
        <section>
          <div class="section-heading"><span>01</span><h3>사용 시나리오</h3></div>
          <div class="two-col">
            <label>업무 유형<select v-model="state.workload"><option v-for="(item, key) in presets?.workloads" :key="key" :value="key">{{ item.label }}</option></select></label>
            <label>사용 강도<select v-model="state.intensity"><option v-for="(item, key) in presets?.workloads[state.workload]?.levels" :key="key" :value="key">{{ item.label }}</option><option value="custom">직접 입력</option></select></label>
          </div>
        </section>

        <section>
          <div class="section-heading"><span>02</span><h3>사용량</h3></div>
          <div class="three-col">
            <label>1인당 일일 토큰<input v-model.number="state.dailyTotalTokens" type="number" min="1" @input="markCustom"></label>
            <label>월 사용 일수<input v-model.number="state.activeDaysPerMonth" type="number" min="1" max="31"></label>
            <label>사용 인원<input v-model.number="state.userCount" type="number" min="1"></label>
          </div>
        </section>

        <section>
          <div class="section-heading"><span>03</span><h3>토큰 구성</h3><strong :class="{ invalid: tokenTotal !== 100 }">합계 {{ tokenTotal }}%</strong></div>
          <div class="four-col">
            <label>Input %<input v-model.number="state.ratios.input" type="number" min="0" max="100" @input="markCustom"></label>
            <label>Output %<input v-model.number="state.ratios.output" type="number" min="0" max="100" @input="markCustom"></label>
            <label>Cache read %<input v-model.number="state.ratios.cacheRead" type="number" min="0" max="100" @input="markCustom"></label>
            <label>Cache write %<input v-model.number="state.ratios.cacheWrite" type="number" min="0" max="100" @input="markCustom"></label>
          </div>
        </section>

        <section>
          <div class="section-heading"><span>04</span><h3>모델 혼합</h3><strong :class="{ invalid: modelTotal !== 100 }">합계 {{ modelTotal }}%</strong></div>
          <div class="model-row"><label>경량 모델 · Haiku<span class="model-select-control"><select v-model="state.haikuId"><option v-for="model in haikuModels" :key="model.modelId" :value="model.modelId">{{ model.displayName }}</option></select><button type="button" aria-label="Haiku 모델 단가 보기" @click="openPrice(state.haikuId)"><svg aria-hidden="true" viewBox="0 0 24 24"><circle cx="11" cy="11" r="7"/><path d="m16 16 5 5"/></svg></button></span></label><label>비중 %<input v-model.number="state.haikuPercentage" type="number" min="0" max="100" @input="markCustom"></label></div>
          <div class="model-row"><label>기준 모델 · Sonnet<span class="model-select-control"><select v-model="state.sonnetId"><option v-for="model in sonnetModels" :key="model.modelId" :value="model.modelId">{{ model.displayName }}</option></select><button type="button" aria-label="Sonnet 모델 단가 보기" @click="openPrice(state.sonnetId)"><svg aria-hidden="true" viewBox="0 0 24 24"><circle cx="11" cy="11" r="7"/><path d="m16 16 5 5"/></svg></button></span></label><label>비중 %<input v-model.number="state.sonnetPercentage" type="number" min="0" max="100" @input="markCustom"></label></div>
          <div class="model-row"><label>고지능 모델 · Opus<span class="model-select-control"><select v-model="state.opusId"><option v-for="model in opusModels" :key="model.modelId" :value="model.modelId">{{ model.displayName }}</option></select><button type="button" aria-label="Opus 모델 단가 보기" @click="openPrice(state.opusId)"><svg aria-hidden="true" viewBox="0 0 24 24"><circle cx="11" cy="11" r="7"/><path d="m16 16 5 5"/></svg></button></span></label><label>비중 %<input v-model.number="state.opusPercentage" type="number" min="0" max="100" @input="markCustom"></label></div>
          <div v-for="(extra, index) in state.additionalModels" :key="index" class="model-row extra-model">
            <label>추가 모델<span class="model-select-control"><select v-model="extra.modelId" @change="markCustom"><option v-for="model in models" :key="model.modelId" :value="model.modelId">{{ model.displayName }}</option></select><button type="button" aria-label="추가 모델 단가 보기" @click="openPrice(extra.modelId)"><svg aria-hidden="true" viewBox="0 0 24 24"><circle cx="11" cy="11" r="7"/><path d="m16 16 5 5"/></svg></button></span></label>
            <label>비중 %<span class="percentage-action"><input v-model.number="extra.percentage" type="number" min="0" max="100" @input="markCustom"><button type="button" aria-label="추가 모델 삭제" @click="removeModel(index)">삭제</button></span></label>
          </div>
          <button class="add-model" type="button" :disabled="selectedModelIds.length >= models.length" @click="addModel">+ 모델 추가</button>
          <p v-if="!hasUniqueModels" class="validation" role="alert">같은 모델을 중복해서 선택할 수 없습니다.</p>
          <p v-if="!models.length" class="hint">가격 데이터가 없습니다. 관리자 가격 동기화를 먼저 실행하세요.</p>
        </section>
        <button class="primary" type="submit" :disabled="!valid || busy || !models.length">{{ busy ? '처리 중…' : '견적 계산하기' }}</button>
      </form>

      <aside class="results" aria-live="polite">
        <section class="result-hero"><p>연간 예상 비용</p><strong>{{ result ? money(result.totalAnnualUsd) : '—' }}</strong><small>{{ state.userCount }}명 · 월 {{ state.activeDaysPerMonth }}일 기준</small></section>
        <section class="panel metrics"><div><span>1인 / 활성일</span><b>{{ result ? money(result.perUserDailyUsd) : '—' }}</b></div><div><span>1인 / 월</span><b>{{ result ? money(result.perUserMonthlyUsd) : '—' }}</b></div><div><span>전체 / 월</span><b>{{ result ? money(result.totalMonthlyUsd) : '—' }}</b></div></section>
        <section v-if="state.workload === 'codingAgent' && reference" class="reference"><span>ANTHROPIC REFERENCE</span><p>Enterprise 평균 <b>${{ reference.averageDailyUsd }}/활성일</b>, 월 <b>${{ reference.monthlyMinUsd }}–${{ reference.monthlyMaxUsd }}</b></p><small>비교용 지표이며 계산에는 사용하지 않습니다.</small></section>
        <section v-if="result" class="panel breakdown">
          <div class="breakdown-heading"><div><span>COST BREAKDOWN</span><h3>모델별 비용 상세</h3></div><small>1인 · 활성일 기준</small></div>
          <article v-for="group in groupedBreakdown" :key="group.modelId" class="model-cost-group" data-testid="model-cost-group">
            <header><div><strong>{{ group.displayName }}</strong><small>{{ group.family }}</small></div><b>{{ money(group.totalUsd) }}</b></header>
            <table><thead><tr><th>토큰 유형</th><th>사용량</th><th>일 비용</th></tr></thead><tbody><tr v-for="item in group.items" :key="item.category"><td>{{ categoryLabel(item.category) }}</td><td>{{ tokens(item.tokens) }}</td><td>{{ money(item.costUsd) }}</td></tr></tbody></table>
          </article>
        </section>
        <p class="notice">{{ presets?.metadata.notice ?? '프리셋은 초기 예산 산정을 위한 가정값입니다.' }}</p>
      </aside>
    </div>
  </main>
  <Teleport to="body">
    <div v-if="modalModel" class="modal-backdrop" role="presentation" @click="closePrice">
      <section class="price-modal" role="dialog" aria-modal="true" aria-labelledby="price-modal-title" @click.stop @keydown.esc="closePrice">
        <header><div><span>MODEL PRICE</span><h2 id="price-modal-title">1M 토큰 기준 단가</h2></div><button ref="modalClose" type="button" aria-label="단가 모달 닫기" @click="closePrice">×</button></header>
        <p class="model-id">{{ modalModel.displayName }}</p>
        <dl>
          <div><dt>Input</dt><dd>{{ perMillion(modalModel.inputCostPerToken) }}</dd></div>
          <div><dt>Output</dt><dd>{{ perMillion(modalModel.outputCostPerToken) }}</dd></div>
          <div><dt>Cache read</dt><dd>{{ perMillion(modalModel.cacheReadCostPerToken) }}</dd></div>
          <div><dt>Cache write</dt><dd>{{ perMillion(modalModel.cacheWriteCostPerToken) }}</dd></div>
        </dl>
        <p class="modal-note">LiteLLM에서 마지막으로 동기화한 USD 토큰 단가입니다.</p>
      </section>
    </div>
  </Teleport>
</template>
