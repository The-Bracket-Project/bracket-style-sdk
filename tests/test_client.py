import json

import httpx
import pytest

from bracket_sdk import ApiError, BracketClient, RateLimitError


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


def test_get_ocean_uses_text_to_ocean_inference_path() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.method == "POST"
        assert request.url.path == "/v1/modules/text-to-ocean/inference"
        assert json.loads(request.content.decode("utf-8")) == {
            "text": "hello ocean",
            "explain": True,
            "user_id": "user-123",
            "lang": "en",
            "granularity": "text",
        }
        return httpx.Response(200, json={"status": "ok"}, request=request)

    transport = httpx.MockTransport(handler)
    client = BracketClient(api_key="test-key", transport=transport)

    assert (
        client.get_ocean(
            text="hello ocean",
            explain=True,
            user_id="user-123",
            lang="en",
            granularity="text",
        )
        == {"status": "ok"}
    )


def test_get_ocean_supports_batch_payload_passthrough() -> None:
    batch_payload = {
        "items": [
            {"id": "1", "text": "First text", "user_id": "u1", "lang": "en"},
            {"id": "2", "text": "Second text"},
        ],
        "aggregate_by_user": False,
        "explain": False,
    }

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/v1/modules/text-to-ocean/inference"
        assert json.loads(request.content.decode("utf-8")) == batch_payload
        return httpx.Response(200, json={"ok": True}, request=request)

    transport = httpx.MockTransport(handler)
    client = BracketClient(api_key="test-key", transport=transport)

    assert client.get_ocean(batch_payload) == {"ok": True}


def test_get_ocean_maps_prompt_alias_to_text() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert json.loads(request.content.decode("utf-8")) == {"text": "hello ocean", "explain": True}
        return httpx.Response(200, json={"ok": True}, request=request)

    transport = httpx.MockTransport(handler)
    client = BracketClient(api_key="test-key", transport=transport)

    assert client.get_ocean({"prompt": "hello ocean", "explain": True}) == {"ok": True}


def test_api_error_surfaces_aws_message_variant() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            400,
            json={"Message": "Could not find endpoint text-to-ocean"},
            request=request,
        )

    transport = httpx.MockTransport(handler)
    client = BracketClient(api_key="test-key", transport=transport)

    with pytest.raises(ApiError, match="Could not find endpoint text-to-ocean"):
        client.get_ocean({"prompt": "hello ocean"})
