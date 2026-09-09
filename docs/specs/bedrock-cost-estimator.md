# Spec: Bedrock Cost Estimator

## Objective

Create a responsive internal estimator for Amazon Bedrock token spending. Users select workload presets or enter custom usage, mix one Sonnet-family and one Opus-family model, and receive transparent per-day, monthly, and annual estimates from synchronized LiteLLM prices.

## Assumptions

1. This project implements its own price synchronization API using the verified reference implementation at `/Users/han/Documents/Github/workspace/litellm-price-api/model_list_api.py`.
2. The upstream is the unauthenticated LiteLLM Model Catalog endpoint `https://api.litellm.ai/model_catalog`. Synchronization requests `provider=bedrock_converse`, follows `page`/`page_size` pagination until `has_more` is false, and applies a 30-second request timeout.
3. The synchronization adapter maps `id`, `provider`, `mode`, `input_cost_per_token`, `output_cost_per_token`, `cache_read_input_token_cost`, and `cache_creation_input_token_cost` into the application's canonical price schema. Long-context and one-hour cache rates are retained when present for later display and calculation support.
4. Only Amazon Bedrock Anthropic Sonnet and Opus text models are selectable in the first release.
5. Estimates use decimal arithmetic on the backend; display rounding never affects calculation.
6. The estimator is deployed behind an organization-controlled network boundary. With no application authentication, the price-sync endpoint must not be exposed publicly.
7. Initial preset numbers are explicitly labeled low-confidence planning assumptions and will later be calibrated from Bedrock or LiteLLM usage logs.
8. Exact dependency versions will be pinned from stable releases at project initialization; releases younger than seven days will not be selected.

## User flow

1. The page loads available models, current pricing status, and preset configuration.
2. The user selects Coding Agent or Internal Chatbot.
3. The user selects Lite, General, or Heavy; preset token and model-mix values populate the form.
4. The user may change total daily tokens, token percentages, model selections, model percentages, active days, users, or exchange rate.
5. Changing a usage preset value changes intensity to Custom.
6. The application validates both percentage groups as exactly 100% and rejects negative or non-finite values.
7. Valid input is sent to the estimation API. Results update with a debounced request or explicit calculate action.
8. Results show token and cost breakdowns plus daily, monthly, and annual totals.
9. Coding Agent results show Anthropic cost references as non-calculating comparison data.
10. The user can switch displayed results between USD and KRW using the manually entered exchange rate.
11. Form state survives reloads in the same tab through `sessionStorage` and disappears when the tab closes.

## Calculation contract

For each model `m` and category `c`:

```text
daily_category_tokens = daily_total_tokens × category_ratio[c]
daily_model_category_tokens = daily_category_tokens × model_ratio[m]
daily_model_category_cost = daily_model_category_tokens × price[m][c]
```

Totals:

```text
per_user_daily_usd = Σ daily_model_category_cost
per_user_monthly_usd = per_user_daily_usd × active_days_per_month
total_monthly_usd = per_user_monthly_usd × user_count
total_annual_usd = total_monthly_usd × 12
krw_amount = usd_amount × usd_to_krw_rate
```

Ratios arrive as percentages but are normalized to decimal values for calculation. Calculations retain decimal precision; UI monetary formatting is separate.

## API contract

All endpoints use `/api/v1`. JSON fields use camelCase. Validation errors use FastAPI's standard 422 response for the first release.

### `GET /api/v1/health`

Returns application and database readiness.

### `GET /api/v1/models`

Returns active Bedrock Anthropic models with:

- modelId
- displayName
- family (`SONNET` or `OPUS`)
- provider
- inputCostPerToken
- outputCostPerToken
- cacheReadCostPerToken
- cacheWriteCostPerToken
- sourceUpdatedAt

No pagination is required because the endpoint is deliberately restricted to the small supported model set.

### `GET /api/v1/presets`

Returns versioned workload presets and Claude Code cost-reference metadata loaded from backend config.

### `POST /api/v1/estimates`

Accepts:

- dailyTotalTokens: positive integer
- activeDaysPerMonth: integer from 1 through 31
- userCount: positive integer
- tokenRatios: four non-negative decimal percentages totaling 100
- models: exactly one Sonnet and one Opus selection, each with a non-negative percentage; percentages total 100

Returns the normalized request, per-model/per-category tokens and USD costs, and all aggregate USD totals. It also returns the exact price snapshot used in the calculation so results are auditable without persisting the estimate.

### `POST /api/v1/prices/sync`

Pages through `https://api.litellm.ai/model_catalog` using `provider=bedrock_converse`, validates the untrusted `data` and `has_more` response fields, filters Anthropic Sonnet and Opus chat models, normalizes LiteLLM pricing fields, and atomically upserts prices. It returns fetched/stored counts and sync timestamp. If fetching, parsing, validation, pagination, or completeness checks fail, existing prices remain unchanged.

This endpoint assumes network-level administrative protection in the first release. Public exposure is prohibited without adding authentication.

### `GET /api/v1/prices/sync-status`

Returns the most recent successful synchronization metadata and any safe, non-secret failure summary.

## Database

### `model_prices`

- model_id: primary key
- display_name
- family
- provider
- input_cost_per_token: numeric
- output_cost_per_token: numeric
- cache_read_cost_per_token: numeric
- cache_write_cost_per_token: numeric
- source_updated_at
- synced_at
- is_active

### `price_sync_runs`

- id: generated primary key
- status: success or failure
- started_at
- completed_at
- fetched_count
- stored_count
- error_summary: nullable and sanitized

No estimate, user, browser-session, or exchange-rate tables are created.

## Preset configuration

A backend YAML file is validated at startup. It contains:

- schema version
- Coding Agent and Internal Chatbot presets
- Lite, General, and Heavy daily token assumptions
- token-category percentages
- default Sonnet/Opus percentages
- human-readable assumptions
- source classification and confidence
- Claude Code cost-reference values and official source URL

Invalid configuration prevents startup rather than silently producing estimates.

## Frontend structure

- App shell and pricing freshness banner
- Exchange-rate control in the page header
- Workload and intensity selectors
- Usage assumptions form
- Always-visible token composition inputs
- Sonnet/Opus model and percentage inputs
- Validation summary adjacent to affected controls
- Cost summary with daily, per-user monthly, organization monthly, and annual values
- Model/category breakdown table
- Claude Code reference comparison for Coding Agent only
- Assumption and methodology disclosure
- Manual price-sync control clearly marked as administrative

The layout is mobile-first, keyboard accessible, and usable at 320, 768, 1024, and 1440 pixel widths. Color is not the only means of communicating validation or comparison status.

## Tech stack

- Backend: Python, FastAPI, Pydantic, SQLAlchemy, Alembic, PostgreSQL
- Backend tests: pytest and FastAPI TestClient/httpx
- Frontend: Vue 3, TypeScript, Vite
- Frontend tests: Vitest and Vue Test Utils
- Browser test: Playwright or configured browser tooling for the critical estimator flow
- Deployment: Dockerfiles, Nginx serving the Vue build and proxying `/api`, Docker Compose, PostgreSQL health checks

## Commands

The scaffold must expose these stable commands:

```text
Backend dev:  conda run -n base uvicorn app.main:app --reload
Backend test: conda run -n base python -m pytest
Backend lint: conda run -n base ruff check .
Backend fmt:  conda run -n base ruff format --check .
Frontend dev: npm run dev
Frontend test: npm run test:unit
Frontend lint: npm run lint
Frontend type: npm run typecheck
Frontend build: npm run build
Full stack:   docker compose up --build
```

## Project structure

```text
backend/
  app/api/          HTTP route modules
  app/core/         settings and preset loading
  app/db/           database session and models
  app/schemas/      API boundary schemas
  app/services/     pricing sync and estimation logic
  config/           versioned usage presets
  migrations/       Alembic migrations
  tests/            unit and API tests
frontend/
  src/api/          typed API client
  src/components/   focused presentation components
  src/composables/  estimator and session state
  src/types/        API and UI contracts
  src/views/        estimator page
  src/**/*.test.ts  colocated component and logic tests
docs/intent/        confirmed product intent
docs/specs/         product and technical specifications
tasks/              implementation plan and checklist
```

## Code style

Python uses typed functions and `Decimal` for prices and costs:

```python
def category_cost(tokens: int, price_per_token: Decimal) -> Decimal:
    return Decimal(tokens) * price_per_token
```

Vue uses Composition API with `<script setup lang="ts">`, semantic HTML, explicit labels, and derived state rather than duplicated mutable totals.

## Testing strategy

- Unit tests prove ratio validation, category/model allocation, decimal cost calculation, aggregate totals, KRW display conversion, and preset transitions.
- API tests prove response contracts, unsupported models, stale/missing prices, and atomic sync failure behavior.
- Component tests prove visible cache fields, accessible labels, validation output, Custom transition, and currency switching.
- One browser flow covers preset selection through annual KRW output.
- External LiteLLM requests are replaced by deterministic fixtures in tests.

## Boundaries

### Always

- Validate browser input and third-party LiteLLM data at their boundaries.
- Preserve separate prices and totals for all four token categories.
- Show pricing freshness and assumptions.
- Run relevant tests, lint, type checks, and builds before declaring a slice complete.
- Keep secrets in environment variables and provide only a `.env.example`.

### Ask first

- Adding application authentication
- Persisting estimates
- Changing the four-category token model
- Adding providers or model families beyond Bedrock Anthropic Sonnet/Opus
- Adding automatic currency-rate retrieval

### Never

- Commit credentials or real API keys
- Treat cost references or preset assumptions as measured user usage
- Replace missing cache prices with base input prices silently
- Partially overwrite valid price data after a failed synchronization
- Expose raw upstream errors or secrets to clients

## Success criteria

- All formulas above are covered by deterministic tests.
- Both percentage groups must total 100% before estimation.
- A preset populates visible values and manual edits switch to Custom.
- Model and token-category breakdown sums exactly to displayed aggregate totals before display rounding.
- A failed synchronization leaves the previous active prices intact.
- Coding Agent reference values are displayed but do not alter calculations.
- Session state survives reload in the same tab and is not written to the backend.
- USD/KRW switching changes presentation without changing stored USD calculation results.
- Docker Compose starts healthy frontend, backend, and PostgreSQL services.
- The critical estimator flow works without browser console errors at required responsive widths.

## Open questions

1. Initial numerical token presets need explicit planning-assumption values. They can be seeded conservatively and labeled low confidence, then revised after pilot telemetry is available.

The LiteLLM price synchronization API is in scope for this project. Its upstream contract and extraction fields are based on the supplied `litellm-price-api/model_list_api.py` reference.
