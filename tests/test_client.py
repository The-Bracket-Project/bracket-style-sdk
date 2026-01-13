import httpx
import pytest

from bracket_sdk import BracketClient, RateLimitError


def test_api_key_header_is_sent() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.headers.get("x-api-key") == "test-key"
        return httpx.Response(200, json={"ok": True}, request=request)

    transport = httpx.MockTransport(handler)
    client = BracketClient(api_key="test-key", transport=transport)

    assert client.get("/ping") == {"ok": True}


def test_rate_limit_maps_to_error() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(429, json={"message": "slow down"}, request=request)

    transport = httpx.MockTransport(handler)
    client = BracketClient(api_key="test-key", transport=transport)

    with pytest.raises(RateLimitError):
        client.get("/limited")
