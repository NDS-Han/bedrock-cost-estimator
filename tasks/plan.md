# Implementation Plan: Bedrock Cost Estimator

## Overview

Build the estimator in contract-first vertical slices. Establish deterministic calculation behavior first, then add persisted pricing and synchronization, connect a tested Vue interface, and finally package the verified stack for EC2 Docker Compose deployment.

## Architecture decisions

- FastAPI owns authoritative validation and cost calculation; Vue provides immediate form feedback but does not independently define pricing rules.
- PostgreSQL stores only model prices and sync history. Browser `sessionStorage` owns transient estimate state.
- A validated YAML file owns initial presets and published comparison metadata.
- Prices and calculations use decimal arithmetic; JSON serializes decimal monetary values as strings to prevent floating-point drift.
- The project implements a LiteLLM pricing-source adapter based on the supplied reference: call `https://api.litellm.ai/model_catalog`, filter `provider=bedrock_converse`, follow `page`/`page_size` pagination, and normalize the result behind an internal interface.
- Price synchronization validates a complete candidate set before committing an atomic upsert.
- The first release relies on network-level protection for the administrative sync endpoint; it must not be publicly exposed.

## Dependency graph

```text
Project scaffold
  ├─ preset schema and loader
  ├─ estimate request/response contract
  │    └─ calculation service
  │         └─ estimate API
  │              └─ Vue estimator flow
  └─ database schema
       └─ pricing repository
            └─ LiteLLM source adapter
                 └─ sync API and UI status

Vue estimator flow + sync flow
  └─ Docker images and Compose
       └─ browser and deployment verification
```

## Phases

### Phase 1: Foundation and contracts

- Scaffold pinned backend and frontend toolchains.
- Define and test preset configuration parsing.
- Define API schemas and calculation tests before implementation.

### Checkpoint

- Backend and frontend test runners execute.
- Invalid preset config fails deterministically.
- Calculation tests demonstrate the intended RED state, then pass after implementation.

### Phase 2: Pricing and estimation API

- Add PostgreSQL models and migration for prices and sync runs.
- Implement model listing and deterministic estimate endpoint.
- Implement and test the pricing-source boundary and atomic synchronization.

### Checkpoint

- API contract tests pass against a test database.
- Sync failure cannot replace existing prices.
- OpenAPI exposes the agreed endpoints and schemas.

### Phase 3: Estimator interface

- Build the responsive estimator form and visible ratio controls.
- Add session-state persistence and Custom preset transitions.
- Add breakdown, reference comparison, and USD/KRW presentation.
- Add pricing freshness and administrative sync states.

### Checkpoint

- Unit and component tests pass.
- Keyboard and responsive checks pass.
- Frontend production build succeeds.

### Phase 4: Deployment and end-to-end verification

- Add production Dockerfiles, Nginx routing, Compose services, health checks, and environment example.
- Run the full stack and verify the critical estimator flow.
- Review security, calculations, source attribution, and operational documentation.

### Checkpoint

- `docker compose up --build` reaches healthy state.
- Critical browser flow has no console errors.
- All tests, lint, type checks, and builds pass.

## Risks and mitigations

| Risk | Impact | Mitigation |
|---|---|---|
| LiteLLM changes its Model Catalog schema or pagination | High | Validate `data` and `has_more` behind a typed adapter, cover the supplied contract with fixtures, cap pagination defensively, and preserve existing DB prices on incompatibility. |
| Initial token presets imply false precision | High | Label as low-confidence planning assumptions and show descriptions/source metadata. |
| Provider fields count cached input differently | High | Normalize once in the source adapter and test fixtures against the four canonical categories. |
| Missing cache rates underestimates spend | High | Reject unsupported/incomplete model pricing instead of silently substituting. |
| Unauthenticated sync endpoint is exposed | High | Bind exposure to trusted network/proxy configuration and document that public deployment requires auth. |
| Decimal rounding causes mismatched totals | Medium | Calculate with Decimal, return exact strings, and round only for display. |
| Browser and backend contracts drift | Medium | Generate or manually maintain typed contracts with API fixture tests. |

## Open questions

- Initial numerical token presets will start as explicitly labeled, low-confidence planning assumptions and should be revised after pilot telemetry is available.

The live pricing adapter is part of the implementation and does not depend on a pre-existing project.
