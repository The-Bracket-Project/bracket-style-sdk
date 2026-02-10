# Bracket Style SDK

Python SDK for Bracket Style APIs.

## Install

```bash
python -m pip install bracket-style-sdk
```

## Quickstart

```python
from bracket_sdk import BracketClient

client = BracketClient(
    api_key="YOUR_API_KEY",
    client_id="acme-inc",
)
response = client.get("/v1/health")
print(response)
```

`client_id` is optional and is sent as `x-client-id`. The SDK uses the default Bracket API base URL automatically.

Environment-based setup (optional):
```bash
export BRACKET_API_KEY="YOUR_API_KEY"
```
```python
client = BracketClient()
```

## Configuration

You can also pass a full `SDKConfig` for defaults such as timeout, retries, and user agent.

```python
from bracket_sdk import BracketClient, SDKConfig

config = SDKConfig(
    api_key="YOUR_API_KEY",
    timeout=10.0,
    retries=3,
)
client = BracketClient(config=config)
```

## Errors

The SDK raises specific exceptions for common HTTP failures:
- `AuthenticationError` (401/403)
- `NotFoundError` (404)
- `RateLimitError` (429)
- `ApiError` (other 4xx/5xx)
- `NetworkError` (transport failures)

## Health

```python
client.health()
```

## Requirements

- Python 3.9+
