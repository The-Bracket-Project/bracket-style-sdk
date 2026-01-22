# Bracket Style SDK

Python SDK + internal dashboard + demo API for usage tracking.

## Repo layout
- `src/` SDK
- `dashboard/` internal dashboard (FastAPI)
- `demo_api/` demo API (FastAPI)
- `scripts/` smoke tests

## Hosting (dev)
- Cloudflare: `thebracket.ai` zone, Zero Trust on `*.dev.thebracket.ai`
- Dashboard: ECS Fargate (us-west-1) behind ALB
- URL: `https://sdk-dashboard.dev.thebracket.ai`
- Image: ECR `sdk-internal-dashboard` (us-west-1)
- Data: CloudWatch Logs `/aws/apigateway/bracket-sdk-prod-access`

## Local quickstart

SDK:
```bash
python -m pip install -e .
```

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

## Internal Dashboard

The internal usage dashboard lives in `dashboard/` and is intended for monitoring SDK calls and client IDs.

Dashboard (local):
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

Demo API (local):
```bash
python -m pip install -e .[demo,dashboard]
export BRACKET_API_KEY="dev-key"
export DASHBOARD_URL="http://localhost:8001"
uvicorn demo_api.app:app --reload --port 8000
```

Then point the SDK at `http://localhost:8000` and call `/v1/health`.

## Smoke Test Scripts

If your API Gateway requires a stage, pass `--stage` (or set `BRACKET_STAGE`).
If your base URL already includes the stage, omit it.

Container (optional):
```bash
docker build -f Dockerfile.dashboard -t bracket-dashboard .
docker run --env-file .env -p 8001:8001 bracket-dashboard
```

## Future work
- [ ] CI/CD: build image, push to ECR, update ECS service
- [ ] Automate Cloudflare IP allowlist on ALB SG/WAF
- [ ] Add alerts for dashboard errors and empty CloudWatch reads
