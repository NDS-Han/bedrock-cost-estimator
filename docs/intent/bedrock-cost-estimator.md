# Bedrock Cost Estimator — Confirmed Intent

## Outcome

Build an internal web application that estimates Amazon Bedrock spending from expected token usage. The estimate is based on model-specific prices synchronized from LiteLLM, not on a target budget.

## Users

Internal users planning Bedrock adoption for coding agents or an internal chatbot. The application has no login, user accounts, or project ownership.

## Why

Teams need a defensible approximation of per-user, monthly, and annual Bedrock costs before sufficient production usage data exists.

## Inputs

- Workload: coding agent or internal chatbot
- Estimation mode: Single or Cohort
- Single-mode usage intensity: Lite, General, Heavy, or Custom
- Cohort-mode user mix: Lite, General, and Heavy percentages totaling 100%
- Cohort-mode token composition: one shared input/output/cache-read/cache-write ratio applied to every cohort
- Cohort-mode model mix: the same editable Haiku/Sonnet/Opus and additional global model mix applied to every cohort
- Average total tokens per active user-day
- Average active days per month
- Number of users
- Token composition: input, output, cache read, and cache write percentages
- Model mix: a lightweight Haiku-family model, a baseline Sonnet-family model, and an advanced Opus-family model by default, with optional additional global Bedrock models
- Manually entered USD/KRW exchange rate

Token composition percentages must total 100%. Model mix percentages must total 100%. Editing a preset-derived usage value changes the usage intensity to Custom.

## Presets and references

- Initial usage and token-composition presets are planning assumptions, not official benchmarks.
- Presets are stored in a version-controlled backend configuration file and change after rebuilding and redeploying the container.
- Coding-agent results display Anthropic's published Claude Code cost references for comparison only:
  - approximately USD 13 per developer per active day
  - approximately USD 150–250 per developer per month
  - 90% of users below USD 30 per active day
- Reference costs never determine the estimate.
- The UI must state that actual usage varies with repository size, session length, tool loops, context reuse, caching, and model selection.

## Pricing

- This project provides a price synchronization API; an administrator manually triggers it to page through LiteLLM Model Catalog (`https://api.litellm.ai/model_catalog`) with the `bedrock_converse` provider filter and normalize the result.
- PostgreSQL stores synchronized model prices and synchronization metadata.
- Pricing must distinguish input, output, cache-read, and cache-write token rates.
- The estimator uses the selected model versions' stored prices.

## Results

Display:

- token allocation by model and token category
- cost breakdown by model and token category
- estimated cost per user per active day
- estimated cost per user per month
- estimated total monthly cost
- estimated total annual cost, calculated as total monthly cost multiplied by 12
- comparison with the published Claude Code cost reference for coding-agent workloads

Results default to USD. Entering an exchange rate and selecting "Convert to KRW" switches monetary results to KRW.

## State and deployment

- Estimator inputs, selections, and exchange rate are kept in browser `sessionStorage` only.
- Closing the browser tab discards the estimate.
- Estimates are not persisted on the server.
- Deploy Vue, FastAPI, and PostgreSQL to EC2 with Docker Compose.

## Success

An internal user can select a preset, adjust all usage assumptions, choose a global Haiku/Sonnet/Opus mix, and obtain a transparent monthly and annual estimate whose breakdown can be traced to synchronized per-token prices.

## Out of scope

- Authentication and authorization
- User or project ownership
- Persisted estimates or estimate history
- Automatic exchange-rate APIs
- VAT, discounts, support costs, or infrastructure costs
- Headcount growth and month-by-month workforce plans
- Official quotations or downloadable quotation documents
- Bedrock quota, TPM, or TPD capacity planning
