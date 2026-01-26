# Bracket Style SDK

Python SDK for Bracket Style APIs. Internal dashboard and demo API are for Bracket team use only.

## Repo layout
- `src/` SDK
- `dashboard/` internal dashboard (Internal Use)
- `demo_api/` demo API (Internal Use)
- `scripts/` smoke tests (Internal Use)

## SDK Quickstart

Install (editable):
```bash
python -m pip install -e .
```

Usage:
```python
from bracket_sdk import BracketClient

client = BracketClient(
    api_key="YOUR_API_KEY",
    base_url="https://api.bracketstyle.com",
    client_id="acme-inc",
)
response = client.get("/v1/health")
print(response)
```

`client_id` is optional and is sent as `x-client-id` to help with internal usage tracking.

You can also call `client.health()` as a convenience method (defaults to `/v1/health`).

## SDK Readiness Checklist (external use)

Implemented in this repo:
- [x] Packaging metadata in `pyproject.toml` with src layout and optional extras
- [x] API key auth + optional `client_id` header injection
- [x] Configurable base URL, timeout, retries, and user agent
- [x] HTTP client with retry/backoff on network errors and 5xx responses
- [x] Error mapping for auth, not found, rate limit, and generic API errors
- [x] Convenience HTTP verbs, raw request access, and `health()` helper
- [x] Context manager support and explicit `close()`
- [x] Basic unit tests for auth headers and rate limit behavior
- [x] Smoke test scripts for health and generate endpoints
- [x] README quickstart usage example

Not implemented yet:
- [ ] Typed request/response models (`src/bracket_sdk/models/` is empty)
- [ ] API-specific methods beyond generic HTTP + `health()`
- [ ] Async client variant
- [ ] Pagination helpers/iterators
- [ ] Retry handling for 429 with `Retry-After` and configurable backoff/jitter
- [ ] Structured logging or debug hooks for requests/responses
- [ ] Environment-based config defaults for API key/base URL
- [ ] Broader unit test coverage (retry paths, error payload parsing, timeouts)
- [ ] CI running tests/linting (PR checks are placeholder)
- [ ] Release/publish automation and changelog

## SDK Roadmap
- [ ] CI: run pytest (and add lint/type checks) in PR checks
- [ ] SDK: add typed models + endpoint-specific methods
- [ ] SDK: add async client + pagination helpers
- [ ] Release: changelog + publish workflow

## Dashboard (Internal Use)

The internal usage dashboard and demo API are intended for monitoring SDK calls and client IDs.
External users can ignore this section.

### Hosting (dev)
- Cloudflare: `thebracket.ai` zone, Zero Trust on `*.dev.thebracket.ai`
- Dashboard: ECS Fargate (us-west-1) behind ALB
- URL: `https://sdk-dashboard.dev.thebracket.ai`
- Image: ECR `sdk-internal-dashboard` (us-west-1)
- Data: CloudWatch Logs `/aws/apigateway/bracket-sdk-prod-access`

### Dashboard (local)
```bash
cp .env.example .env
python -m pip install -e .[dashboard]
uvicorn dashboard.app:app --reload --port 8001
```

Minimum env vars for CloudWatch data:
- `DASHBOARD_DATA_SOURCE=cloudwatch`
- `DASHBOARD_CLOUDWATCH_LOG_GROUP=/aws/apigateway/bracket-sdk-prod-access`
- `AWS_REGION=us-west-1`

If you do not have AWS creds, set `DASHBOARD_DATA_SOURCE=memory`.

### Demo API (local)
```bash
python -m pip install -e .[demo,dashboard]
export BRACKET_API_KEY="dev-key"
export DASHBOARD_URL="http://localhost:8001"
uvicorn demo_api.app:app --reload --port 8000
```

Then point the SDK at `http://localhost:8000` and call `/v1/health`.

### Smoke Test Scripts

If your API Gateway requires a stage, pass `--stage` (or set `BRACKET_STAGE`).
If your base URL already includes the stage, omit it.

### Container (optional)
```bash
docker build -f Dockerfile.dashboard -t bracket-dashboard .
docker run --env-file .env -p 8001:8001 bracket-dashboard
```

### Dashboard Roadmap
- [ ] Automate Cloudflare IP allowlist on ALB SG/WAF
- [ ] Add alerts for dashboard errors and empty CloudWatch reads
