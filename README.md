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

## Demo API (v1)

Run the demo API locally to validate the SDK health check and usage tracking pipeline.

```bash
python -m pip install -e .[demo,dashboard]
export BRACKET_API_KEY="dev-key"
export DASHBOARD_URL="http://localhost:8001"
uvicorn demo_api.app:app --reload --port 8000
```

Then point the SDK at `http://localhost:8000` and call `/health`.
