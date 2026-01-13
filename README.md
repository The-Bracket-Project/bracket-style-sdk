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

## Internal Dashboard

The internal usage dashboard lives in `dashboard/` and is intended for monitoring SDK calls and client IDs.

```bash
python -m pip install -e .[dashboard]
uvicorn dashboard.app:app --reload
```
