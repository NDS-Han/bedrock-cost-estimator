<script setup lang="ts">
import { computed, onMounted, reactive, ref, watch } from 'vue'
import { estimate, getModels, getPresets, syncPrices } from './api/client'
import type { EstimateResult, ModelPrice, Presets, Ratios } from './types/api'

const presets = ref<Presets>()
const models = ref<ModelPrice[]>([])
const result = ref<EstimateResult>()
const error = ref('')
const busy = ref(false)
const currency = ref<'USD' | 'KRW'>('USD')
const stored = sessionStorage.getItem('bedrock-estimator')
const state = reactive(stored ? JSON.parse(stored) : {
  workload: 'codingAgent', intensity: 'general', dailyTotalTokens: 4500000,
  activeDaysPerMonth: 20, userCount: 30, exchangeRate: 1400,
  ratios: { input: 10, output: 5, cacheRead: 75, cacheWrite: 10 } as Ratios,
  sonnetPercentage: 80, opusPercentage: 20, sonnetId: '', opusId: '',
})

const sonnetModels = computed(() => models.value.filter((model) => model.family === 'SONNET'))
const opusModels = computed(() => models.value.filter((model) => model.family === 'OPUS'))
const tokenTotal = computed(() => Object.values(state.ratios as Ratios).reduce((a, b) => a + Number(b), 0))
const modelTotal = computed(() => Number(state.sonnetPercentage) + Number(state.opusPercentage))
const valid = computed(() => tokenTotal.value === 100 && modelTotal.value === 100 && state.dailyTotalTokens > 0 && state.userCount > 0)
const reference = computed(() => presets.value?.references.claudeCode)

function applyPreset() {
  if (state.intensity === 'custom' || !presets.value) return
  const preset = presets.value.workloads[state.workload].levels[state.intensity]
  state.dailyTotalTokens = preset.dailyTotalTokens
  state.ratios = { ...preset.tokenRatios }
  state.sonnetPercentage = preset.modelRatios.sonnet
  state.opusPercentage = preset.modelRatios.opus
}

function markCustom() { state.intensity = 'custom' }
function money(value: string) {
  const amount = Number(value) * (currency.value === 'KRW' ? Number(state.exchangeRate) : 1)
  return new Intl.NumberFormat('ko-KR', { style: 'currency', currency: currency.value, maximumFractionDigits: currency.value === 'KRW' ? 0 : 2 }).format(amount)
}
function tokens(value: string) { return new Intl.NumberFormat('ko-KR', { maximumFractionDigits: 0 }).format(Number(value)) }

async function calculate() {
  if (!valid.value || !state.sonnetId || !state.opusId) return
  busy.value = true
  error.value = ''
  try {
    result.value = await estimate({
      dailyTotalTokens: Number(state.dailyTotalTokens), activeDaysPerMonth: Number(state.activeDaysPerMonth),
      userCount: Number(state.userCount), tokenRatios: state.ratios,
      models: [
        { modelId: state.sonnetId, family: 'SONNET', percentage: Number(state.sonnetPercentage) },
        { modelId: state.opusId, family: 'OPUS', percentage: Number(state.opusPercentage) },
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
          <div class="model-row"><label>기준 모델 · Sonnet<select v-model="state.sonnetId"><option v-for="model in sonnetModels" :key="model.modelId" :value="model.modelId">{{ model.displayName }}</option></select></label><label>비중 %<input v-model.number="state.sonnetPercentage" type="number" min="0" max="100" @input="markCustom"></label></div>
          <div class="model-row"><label>고지능 모델 · Opus<select v-model="state.opusId"><option v-for="model in opusModels" :key="model.modelId" :value="model.modelId">{{ model.displayName }}</option></select></label><label>비중 %<input v-model.number="state.opusPercentage" type="number" min="0" max="100" @input="markCustom"></label></div>
          <p v-if="!models.length" class="hint">가격 데이터가 없습니다. 관리자 가격 동기화를 먼저 실행하세요.</p>
        </section>
        <button class="primary" type="submit" :disabled="!valid || busy || !models.length">{{ busy ? '처리 중…' : '견적 계산하기' }}</button>
      </form>

      <aside class="results" aria-live="polite">
        <section class="result-hero"><p>연간 예상 비용</p><strong>{{ result ? money(result.totalAnnualUsd) : '—' }}</strong><small>{{ state.userCount }}명 · 월 {{ state.activeDaysPerMonth }}일 기준</small></section>
        <section class="panel metrics"><div><span>1인 / 활성일</span><b>{{ result ? money(result.perUserDailyUsd) : '—' }}</b></div><div><span>1인 / 월</span><b>{{ result ? money(result.perUserMonthlyUsd) : '—' }}</b></div><div><span>전체 / 월</span><b>{{ result ? money(result.totalMonthlyUsd) : '—' }}</b></div></section>
        <section v-if="state.workload === 'codingAgent' && reference" class="reference"><span>ANTHROPIC REFERENCE</span><p>Enterprise 평균 <b>${{ reference.averageDailyUsd }}/활성일</b>, 월 <b>${{ reference.monthlyMinUsd }}–${{ reference.monthlyMaxUsd }}</b></p><small>비교용 지표이며 계산에는 사용하지 않습니다.</small></section>
        <section v-if="result" class="panel breakdown"><h3>비용 상세</h3><table><thead><tr><th>모델</th><th>구분</th><th>토큰</th><th>일 비용</th></tr></thead><tbody><tr v-for="item in result.breakdown" :key="`${item.modelId}-${item.category}`"><td>{{ item.family }}</td><td>{{ item.category }}</td><td>{{ tokens(item.tokens) }}</td><td>{{ money(item.costUsd) }}</td></tr></tbody></table></section>
        <p class="notice">{{ presets?.metadata.notice ?? '프리셋은 초기 예산 산정을 위한 가정값입니다.' }}</p>
      </aside>
    </div>
  </main>
</template>
