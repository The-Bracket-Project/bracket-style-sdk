# Bracket Style SDK

## 1. Overview
This repository contains the Bracket Style Python SDK and the supporting systems used to operate and expose it. It combines product-facing components (SDK and client portal) with internal operational services (usage dashboard and demo API), plus infrastructure and deployment automation.

At a high level, the codebase is organized around:
- A consumable Python SDK (`bracket-style-sdk`)
- A client-facing portal for API key management
- Backend services that power portal workflows
- An internal dashboard for usage visibility
- Infrastructure, CI/CD workflows, and operational scripts

## 2. What the SDK Does
The SDK provides a consistent Python interface to Bracket Style APIs so application teams do not need to hand-roll HTTP transport, auth headers, retries, or error translation.

Primary abstractions:
- `BracketClient`: main API client for request/response calls
- `SDKConfig`: central configuration for API key, base URL, timeout, retries, and client metadata
- Typed exceptions for common failure classes (`AuthenticationError`, `RateLimitError`, `NotFoundError`, `ApiError`, `NetworkError`)

Public entrypoints are exported from `src/bracket_sdk/__init__.py`, with consumer-facing usage centered on `BracketClient`.

Conceptual usage:
```python
from bracket_sdk import BracketClient

client = BracketClient(api_key="YOUR_API_KEY")
health = client.health()
```

## 3. Repository Layout
| Group | Directories | Purpose |
|---|---|---|
| SDK core | `src/`, `tests/` | Contains the Python package (`bracket_sdk`) and unit tests for core client behavior. This is the primary product artifact. |
| Customer portal | `client_portal/`, `client_portal_server/` | React/Vite frontend plus Node/Express backend-for-frontend for API key management, auth integration, and portal APIs. |
| Internal operations | `dashboard/`, `demo_api/` | FastAPI dashboard for usage monitoring and a demo API used for local/internal validation flows. |
| Infrastructure and delivery | `infra/`, `.github/workflows/`, `scripts/` | Terraform for AWS infrastructure, GitHub Actions for CI/CD, and scripts for deployment and smoke checks. |
| Documentation and distribution assets | `docs/`, `README.public.md` | Docs index and deployment documentation, plus public-facing README material used for SDK sync/public distribution. |
| Integration scaffold | `sagemaker_endpoint/` | Minimal SageMaker inference scaffold for integration experimentation and reference. |

Tooling snapshot:
- Python SDK/tooling: Python 3.9+, `setuptools` packaging, `pytest` for SDK tests.
- JavaScript/TypeScript apps: Node.js (Node 20 in CI), `npm` per app (`package-lock.json` in each portal project).
- Frontend build system: React + TypeScript + Vite.
- Backend service testing: Node built-in test runner (`node --test`) in `client_portal_server/`.
- Infrastructure as code: Terraform (`infra/`, provider-managed AWS resources).
- Containerization: Dockerfiles for portal API, frontend image packaging, and dashboard runtime.
- Lint/format posture: no repository-wide lint/format standard is currently codified in central config files.

## 4. Components at a Glance
| Component | Role | Runtime/Platform |
|---|---|---|
| Python SDK (`src/bracket_sdk`) | Consumer library for Bracket Style API access | Python package (setuptools, Python 3.9+) |
| Client Portal (`client_portal`) | Customer UI for authentication and API key lifecycle management | React + TypeScript + Vite, deployed as static assets |
| Client Portal API (`client_portal_server`) | Backend-for-frontend for key operations and auth-protected workflows | Node.js + Express, containerized and deployed to ECS |
| Internal Dashboard (`dashboard`) | Internal usage and operational visibility | FastAPI, containerized and deployed to ECS |
| Demo API (`demo_api`) | Local/internal API harness for smoke and usage flows | FastAPI service |
| SDK Public Sync (`sdk-public-sync` workflow) | Mirrors selected SDK files to public repository | GitHub Actions source sync (non-runtime deploy) |

## 5. CI/CD at a High Level
This repository uses GitHub Actions workflows under `.github/workflows/`.

| Workflow | Trigger | High-level responsibility |
|---|---|---|
| `.github/workflows/python-pr-checks.yml` | Pull requests to `main` | Python package sanity check (currently lightweight placeholder stage). |
| `.github/workflows/client-portal-detect-changes.yml` | Pull requests to `main` | Path-based checks: frontend build and backend tests only when relevant files change. |
| `.github/workflows/client-portal-deploy.yml` | Push to `main`, manual dispatch | Deploys client portal surfaces: backend container to ECS and frontend static assets to S3/CloudFront. |
| `.github/workflows/dashboard-deploy.yml` | Push to `main` (dashboard paths) | Builds/pushes dashboard container and updates ECS service. |
| `.github/workflows/sdk-public-sync.yml` | Push to `main` (SDK paths), manual dispatch | Filters SDK-related files and syncs them to a separate public GitHub repository. |

Pipeline pattern:
- Detect relevant path changes
- Run targeted build/test checks
- Build artifacts (container images or static assets)
- Publish artifacts (ECR, S3, public repo)
- Roll out runtime updates (ECS task/service update, CloudFront invalidation)

Current trigger model is branch-based (`main`/PR), with no tag- or release-driven deployment workflow committed.

## 6. Deployment and Environments
Deployment is split by surface:
- `client_portal/`: built as static assets and served via S3 + CloudFront.
- `client_portal_server/`: packaged as a Docker image, pushed to ECR, then deployed to ECS (behind ALB).
- `dashboard/`: packaged as a Docker image, pushed to ECR, then deployed to ECS.
- SDK code: synchronized to a public repository via CI (not a runtime service deployment).

Environment and promotion model:
- Deployments are initiated from pushes to `main` (with path filters to avoid unnecessary rollouts).
- Environment-specific behavior is driven by Terraform variables and workflow/runtime environment variables.
- Configuration indicates stage-aware values (for example, API gateway stage variables), but CI currently reflects a direct `main` deployment flow rather than a codified multi-step promotion chain across dev/staging/prod.

Config and secrets (conceptual):
- Local development uses `.env` patterns from `.env.example` files.
- CI/CD uses GitHub Actions variables/secrets and AWS OIDC role assumption.
- Runtime services receive configuration via environment variables (including ECS task definitions in Terraform-managed stack).

## 7. Local Development (High Level)
Typical developer workflow:
- Install Python dependencies and SDK package in editable mode for SDK and backend Python components.
- Install Node dependencies separately in `client_portal/` and `client_portal_server/`.
- Run targeted local services:
  - SDK tests (`pytest`)
  - Client portal frontend (`npm run dev`)
  - Client portal backend (`npm run dev`/`npm start`)
  - Dashboard and demo API via `uvicorn`
- Use the relevant `.env.example` file in each component as the source of required local configuration.

For exact commands and environment setup details, use component-level READMEs and `docs/`.

## 8. Where to Put Deeper Docs (docs/)
This README is intentionally high-level. Detailed operational and implementation docs should live under `docs/`.

Recommended documentation map:
- `docs/README.md`: docs index and navigation entrypoint
- `docs/deployment/how-deployment-works.md`: deployment architecture, rollout sequence, rollback guidance
- `docs/sdk/quickstart.md`: SDK consumer onboarding and common usage patterns
- `docs/sdk/configuration.md`: SDK configuration matrix and environment conventions
- `docs/portal/architecture.md`: client portal frontend/backend interaction model
- `docs/dashboard/operations.md`: dashboard runtime, observability, and access control model
- `docs/runbooks/`: operational runbooks (incident response, rollback, recovery)

## 9. Glossary (optional)
- SDK: The Python client library used by integrators to call Bracket Style APIs.
- Client Portal: Customer-facing web interface for API key lifecycle and usage access.
- BFF (Backend-for-Frontend): Service layer that supports portal-specific API operations.
- Dashboard: Internal operational UI for monitoring usage and API activity.
- Public Sync: CI workflow that mirrors SDK files to a separate public repository.

## 10. Open Questions / Follow-ups (optional)
- Confirm where dashboard infrastructure is defined long-term; current Terraform in `infra/` models the client portal stack, while dashboard runtime deployment is workflow-driven.
- Confirm the intended environment promotion strategy (single mainline deploy vs explicit dev/staging/prod progression).
- Define final CI quality gates for Python SDK (PR workflow currently uses a lightweight placeholder stage).
- Confirm official package release strategy (for example, package registry publishing) beyond public repository sync.
- Confirm whether `sagemaker_endpoint/` is an active product path or a reference scaffold.
