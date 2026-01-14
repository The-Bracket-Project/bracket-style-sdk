# Welcome To Bracket Style SDK v1.0

## Python SDK

The SDK is a thin REST wrapper that authenticates with an API key and exposes a simple client interface.

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
response = client.get("/health")
print(response)
```

`client_id` is optional and is sent as `x-client-id` to help with internal usage tracking.

You can also call `client.health()` as a convenience method.

## Internal Dashboard

The internal usage dashboard lives in `dashboard/` and is intended for monitoring SDK calls and client IDs.

```bash
python -m pip install -e .[dashboard]
uvicorn dashboard.app:app --reload --port 8001
```

Container:

```bash
docker build -f Dockerfile.dashboard -t bracket-dashboard .
docker run --env-file .env -p 8001:8001 bracket-dashboard
```

## Demo API (v1)

Run the demo API locally to validate the SDK health check and usage tracking pipeline.

```bash
python -m pip install -e .[demo,dashboard]
export BRACKET_API_KEY="dev-key"
export DASHBOARD_URL="http://localhost:8001"
uvicorn demo_api.app:app --reload --port 8000
```

Then point the SDK at `http://localhost:8000` and call `/health`.

## Smoke Test Scripts

If your API Gateway requires a stage, pass `--stage` (or set `BRACKET_STAGE`).
If your base URL already includes the stage, omit it.

```bash
python scripts/smoke_test.py \\
  --base-url "https://{api_id}.execute-api.{region}.amazonaws.com" \\
  --stage "prod" \\
  --api-key "YOUR_KEY" \\
  --client-id "acme-inc" \\
  --path "/v1/health"
```

```bash
python scripts/smoke_generate.py \\
  --base-url "https://{api_id}.execute-api.{region}.amazonaws.com" \\
  --stage "prod" \\
  --api-key "YOUR_KEY" \\
  --client-id "acme-inc" \\
  --body '{"inputs":"Say hello in one sentence.","parameters":{"max_new_tokens":64,"temperature":0.2}}'
```
