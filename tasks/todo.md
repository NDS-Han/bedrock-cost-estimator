# Bedrock Cost Estimator Tasks

## Task 1: Initialize project toolchains

**Acceptance criteria**
- [ ] FastAPI and Vue TypeScript applications start locally.
- [ ] Backend and frontend test, lint, and build commands exist.
- [ ] Dependencies and lockfiles are pinned; secrets and build outputs are ignored.

**Verification**
- [ ] `uv run pytest`
- [ ] `npm run test:unit`
- [ ] `npm run typecheck`

**Dependencies:** None

## Task 2: Load validated usage presets

**Acceptance criteria**
- [ ] YAML defines both workloads and Lite, General, Heavy levels.
- [ ] Every token and model ratio group totals 100%.
- [ ] Invalid config prevents backend startup with a clear error.

**Verification**
- [ ] Preset loader unit tests pass.
- [ ] `GET /api/v1/presets` contract test passes.

**Dependencies:** Task 1

## Task 3: Implement deterministic estimation

**Acceptance criteria**
- [ ] Tests cover four token categories across Sonnet and Opus mixes.
- [ ] Decimal breakdowns reconcile exactly with aggregate totals.
- [ ] Invalid ratios, counts, model families, or missing prices return validation errors.

**Verification**
- [ ] Calculation unit tests pass.
- [ ] `POST /api/v1/estimates` API tests pass.

**Dependencies:** Tasks 1–2

## Checkpoint: Core calculation

- [ ] Backend tests and lint pass.
- [ ] OpenAPI contract matches the specification.

## Task 4: Persist model prices and sync history

**Acceptance criteria**
- [ ] Alembic migration creates only model-price and sync-run tables.
- [ ] Price values retain sufficient decimal precision.
- [ ] Model listing returns only active supported models.

**Verification**
- [ ] Migration applies to an empty PostgreSQL database.
- [ ] Repository integration tests pass.

**Dependencies:** Task 1

## Task 5: Synchronize LiteLLM prices atomically

**Acceptance criteria**
- [ ] A typed adapter validates the Model Catalog `data`/`has_more` contract and paginates with `provider=bedrock_converse`.
- [ ] Successful sync extracts the supplied pricing fields, upserts the complete supported Sonnet/Opus set, and records metadata.
- [ ] Failed or incomplete sync preserves prior active prices.

**Verification**
- [ ] Sync service tests pass with success, malformed, and network-failure fixtures.
- [ ] Sync and status API tests pass.

**Dependencies:** Task 4

## Checkpoint: Backend

- [ ] Backend tests, lint, and formatting checks pass.
- [ ] Estimate responses include the exact price snapshot used.

## Task 6: Build estimator input flow

**Acceptance criteria**
- [ ] Users can select workload/intensity and see all preset values.
- [ ] Input, output, cache-read, and cache-write percentages are always visible and editable.
- [ ] Manual preset-field edits switch intensity to Custom and validation is accessible.

**Verification**
- [ ] Vue component tests pass.
- [ ] Keyboard interaction works at 320px and desktop widths.

**Dependencies:** Tasks 2–3

## Task 7: Display transparent estimates and references

**Acceptance criteria**
- [ ] Daily, per-user monthly, total monthly, and annual costs render from API results.
- [ ] Model/category breakdown reconciles with totals.
- [ ] Coding Agent shows official cost references as comparison-only content.

**Verification**
- [ ] Result and reference component tests pass.
- [ ] No estimate changes when reference metadata changes.

**Dependencies:** Tasks 3 and 6

## Task 8: Add session and currency presentation

**Acceptance criteria**
- [ ] Form state and exchange rate survive reload in the same tab.
- [ ] USD/KRW switching changes display only, using the entered rate.
- [ ] Invalid exchange rates do not enable KRW conversion.

**Verification**
- [ ] Session composable and currency formatting tests pass.

**Dependencies:** Tasks 6–7

## Task 9: Surface pricing synchronization

**Acceptance criteria**
- [ ] Pricing freshness and missing-price states are clear.
- [ ] Manual sync has loading, success, and sanitized error states.
- [ ] The UI labels synchronization as an administrative action.

**Verification**
- [ ] API-client and component tests pass.

**Dependencies:** Task 5

## Checkpoint: Application

- [ ] Frontend tests, lint, type checks, and production build pass.
- [ ] Responsive and accessibility checks pass at required widths.

## Task 10: Package and verify EC2 deployment

**Acceptance criteria**
- [ ] Production frontend, backend, and PostgreSQL services run under Docker Compose.
- [ ] Health checks and startup ordering work without manual intervention.
- [ ] Environment documentation contains names and examples but no secrets.

**Verification**
- [ ] `docker compose config`
- [ ] `docker compose up --build`
- [ ] API health and critical browser estimator flow pass without console errors.

**Dependencies:** Tasks 1–9

## Final checkpoint

- [ ] All specification success criteria pass.
- [ ] Security and calculation review is complete.
- [ ] Intent, spec, and operational commands match the delivered application.
