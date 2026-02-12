import json

import httpx
import pytest

from bracket_sdk import ApiError, BracketClient, RateLimitError, SDKConfig


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
    client = BracketClient(api_key="test-key", retries=0, transport=transport)

    with pytest.raises(RateLimitError):
        client.get("/limited")


def test_rate_limit_with_retry_after_retries_then_succeeds(monkeypatch: pytest.MonkeyPatch) -> None:
    attempts = 0
    sleep_calls = []
    monkeypatch.setattr("bracket_sdk.http.time.sleep", lambda value: sleep_calls.append(value))

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal attempts
        attempts += 1
        if attempts == 1:
            return httpx.Response(
                429,
                json={"message": "slow down"},
                headers={"Retry-After": "2"},
                request=request,
            )
        return httpx.Response(200, json={"ok": True}, request=request)

    transport = httpx.MockTransport(handler)
    client = BracketClient(api_key="test-key", retries=1, transport=transport)

    assert client.get("/limited") == {"ok": True}
    assert attempts == 2
    assert sleep_calls == [2.0]


def test_rate_limit_without_retry_after_uses_backoff(monkeypatch: pytest.MonkeyPatch) -> None:
    attempts = 0
    sleep_calls = []
    monkeypatch.setattr("bracket_sdk.http.time.sleep", lambda value: sleep_calls.append(value))

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal attempts
        attempts += 1
        if attempts < 3:
            return httpx.Response(429, json={"message": "slow down"}, request=request)
        return httpx.Response(200, json={"ok": True}, request=request)

    transport = httpx.MockTransport(handler)
    client = BracketClient(api_key="test-key", retries=2, transport=transport)

    assert client.get("/limited") == {"ok": True}
    assert attempts == 3
    assert sleep_calls == [0.2, 0.4]


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


def test_custom_headers_persist_across_retries(monkeypatch: pytest.MonkeyPatch) -> None:
    attempts = 0
    custom_header_values = []

    monkeypatch.setattr("bracket_sdk.http.time.sleep", lambda *_: None)

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal attempts
        attempts += 1
        custom_header_values.append(request.headers.get("x-custom"))
        if attempts < 3:
            return httpx.Response(500, json={"message": "temporary"}, request=request)
        return httpx.Response(200, json={"ok": True}, request=request)

    transport = httpx.MockTransport(handler)
    client = BracketClient(api_key="test-key", retries=2, transport=transport)

    assert client.get("/retry", headers={"x-custom": "present-on-all-attempts"}) == {"ok": True}
    assert custom_header_values == ["present-on-all-attempts", "present-on-all-attempts", "present-on-all-attempts"]


def test_post_on_5xx_does_not_retry_by_default(monkeypatch: pytest.MonkeyPatch) -> None:
    attempts = 0
    monkeypatch.setattr("bracket_sdk.http.time.sleep", lambda *_: None)

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal attempts
        attempts += 1
        return httpx.Response(500, json={"message": "boom"}, request=request)

    transport = httpx.MockTransport(handler)
    client = BracketClient(api_key="test-key", retries=3, transport=transport)

    with pytest.raises(ApiError, match="boom"):
        client.post("/mutate", json={"value": 1})

    assert attempts == 1


def test_post_on_5xx_retries_when_opted_in(monkeypatch: pytest.MonkeyPatch) -> None:
    attempts = 0
    sleep_calls = []
    monkeypatch.setattr("bracket_sdk.http.time.sleep", lambda value: sleep_calls.append(value))

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal attempts
        attempts += 1
        if attempts == 1:
            return httpx.Response(500, json={"message": "temporary"}, request=request)
        return httpx.Response(200, json={"ok": True}, request=request)

    transport = httpx.MockTransport(handler)
    config = SDKConfig(
        api_key="test-key",
        retries=2,
        allow_non_idempotent_retries=True,
    )
    client = BracketClient(config=config, transport=transport)

    assert client.post("/mutate", json={"value": 1}) == {"ok": True}
    assert attempts == 2
    assert sleep_calls == [0.2]


def test_hooks_receive_request_response_and_retry_with_redaction(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    attempts = 0
    request_events = []
    response_events = []
    retry_events = []
    monkeypatch.setattr("bracket_sdk.http.time.sleep", lambda *_: None)

    def on_request(ctx: dict) -> None:
        request_events.append(ctx)

    def on_response(ctx: dict) -> None:
        response_events.append(ctx)

    def on_retry(ctx: dict) -> None:
        retry_events.append(ctx)

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal attempts
        attempts += 1
        if attempts == 1:
            return httpx.Response(500, json={"message": "temporary"}, request=request)
        return httpx.Response(200, json={"ok": True}, request=request)

    transport = httpx.MockTransport(handler)
    config = SDKConfig(
        api_key="test-key",
        retries=1,
        on_request=on_request,
        on_response=on_response,
        on_retry=on_retry,
    )
    client = BracketClient(config=config, transport=transport)

    result = client.get(
        "/hooks",
        headers={"Authorization": "Bearer super-secret", "x-trace": "trace-123"},
    )

    assert result == {"ok": True}
    assert len(request_events) == 2
    assert len(response_events) == 2
    assert len(retry_events) == 1
    assert request_events[0]["headers"]["x-api-key"] == "[REDACTED]"
    assert request_events[0]["headers"]["Authorization"] == "[REDACTED]"
    assert request_events[0]["headers"]["x-trace"] == "trace-123"
    assert retry_events[0]["reason"] == "http_5xx"
    assert retry_events[0]["status_code"] == 500
    assert retry_events[0]["delay_seconds"] == 0.2
    assert "test-key" not in repr(request_events)
    assert "super-secret" not in repr(request_events)


def test_hook_exceptions_are_propagated() -> None:
    attempts = 0

    def on_request(_: dict) -> None:
        raise RuntimeError("hook exploded")

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal attempts
        attempts += 1
        return httpx.Response(200, json={"ok": True}, request=request)

    transport = httpx.MockTransport(handler)
    config = SDKConfig(api_key="test-key", on_request=on_request)
    client = BracketClient(config=config, transport=transport)

    with pytest.raises(RuntimeError, match="hook exploded"):
        client.get("/hooks-fail")

    assert attempts == 0


def test_paginate_iterates_over_all_items_with_method_and_path() -> None:
    seen_cursors = []

    def handler(request: httpx.Request) -> httpx.Response:
        cursor = request.url.params.get("cursor")
        seen_cursors.append(cursor)
        if cursor is None:
            return httpx.Response(
                200,
                json={"items": ["a", "b"], "next_cursor": "next-1"},
                request=request,
            )
        if cursor == "next-1":
            return httpx.Response(
                200,
                json={"items": ["c"], "next_cursor": None},
                request=request,
            )
        return httpx.Response(400, json={"message": "unexpected cursor"}, request=request)

    transport = httpx.MockTransport(handler)
    client = BracketClient(api_key="test-key", transport=transport)

    items = list(
        client.paginate(
            path="/items",
            extract_items=lambda page: page["items"],
            extract_next_cursor=lambda page: page.get("next_cursor"),
        )
    )

    assert items == ["a", "b", "c"]
    assert seen_cursors == [None, "next-1"]


def test_paginate_supports_custom_request_function() -> None:
    calls = []
    pages = {
        None: {"items": [1, 2], "next_cursor": "cursor-2"},
        "cursor-2": {"items": [3], "next_cursor": None},
    }

    def request_fn(cursor) -> dict:
        calls.append(cursor)
        return pages[cursor]

    client = BracketClient(
        api_key="test-key",
        transport=httpx.MockTransport(
            lambda request: httpx.Response(200, json={"ok": True}, request=request)
        ),
    )

    items = list(
        client.paginate(
            request_fn=request_fn,
            extract_items=lambda page: page["items"],
            extract_next_cursor=lambda page: page.get("next_cursor"),
        )
    )

    assert items == [1, 2, 3]
    assert calls == [None, "cursor-2"]


def test_client_can_initialize_from_bracket_api_key_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("BRACKET_API_KEY", "env-key")

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.headers.get("x-api-key") == "env-key"
        return httpx.Response(200, json={"ok": True}, request=request)

    transport = httpx.MockTransport(handler)
    client = BracketClient(transport=transport)

    assert client.get("/env-auth") == {"ok": True}


def test_env_configuration_applies_base_url_timeout_retries_and_metadata(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("BRACKET_API_KEY", "env-key")
    monkeypatch.setenv("BRACKET_BASE_URL", "https://env.example.test/sdk")
    monkeypatch.setenv("BRACKET_TIMEOUT", "3.5")
    monkeypatch.setenv("BRACKET_RETRIES", "4")
    monkeypatch.setenv("BRACKET_CLIENT_ID", "env-client")
    monkeypatch.setenv("BRACKET_USER_AGENT", "env-agent/1.0")

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/sdk/resource"
        assert request.headers.get("x-client-id") == "env-client"
        assert request.headers.get("user-agent") == "env-agent/1.0"
        return httpx.Response(200, json={"ok": True}, request=request)

    transport = httpx.MockTransport(handler)
    client = BracketClient(transport=transport)

    assert client._config.base_url == "https://env.example.test/sdk"
    assert client._config.timeout == 3.5
    assert client._config.retries == 4
    assert client.get("/resource") == {"ok": True}


@pytest.mark.parametrize(
    ("env_name", "env_value", "expected_message"),
    [
        ("BRACKET_TIMEOUT", "not-a-float", "Invalid BRACKET_TIMEOUT"),
        ("BRACKET_TIMEOUT", "0", "Invalid BRACKET_TIMEOUT"),
        ("BRACKET_RETRIES", "nope", "Invalid BRACKET_RETRIES"),
        ("BRACKET_RETRIES", "-1", "Invalid BRACKET_RETRIES"),
    ],
)
def test_invalid_env_values_raise_clear_errors(
    monkeypatch: pytest.MonkeyPatch,
    env_name: str,
    env_value: str,
    expected_message: str,
) -> None:
    monkeypatch.setenv("BRACKET_API_KEY", "env-key")
    monkeypatch.setenv(env_name, env_value)

    with pytest.raises(ValueError, match=expected_message):
        BracketClient()


def test_explicit_args_override_config_and_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("BRACKET_API_KEY", "env-key")
    monkeypatch.setenv("BRACKET_BASE_URL", "https://env.example.test/env")
    monkeypatch.setenv("BRACKET_TIMEOUT", "9.0")
    monkeypatch.setenv("BRACKET_RETRIES", "9")
    monkeypatch.setenv("BRACKET_CLIENT_ID", "env-client")
    monkeypatch.setenv("BRACKET_USER_AGENT", "env-agent/1.0")

    config = SDKConfig(
        api_key="config-key",
        base_url="https://config.example.test/config",
        timeout=8.0,
        retries=8,
        client_id="config-client",
        user_agent="config-agent/1.0",
    )

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/explicit/check"
        assert request.headers.get("x-api-key") == "explicit-key"
        assert request.headers.get("x-client-id") == "explicit-client"
        assert request.headers.get("user-agent") == "explicit-agent/1.0"
        return httpx.Response(200, json={"ok": True}, request=request)

    transport = httpx.MockTransport(handler)
    client = BracketClient(
        config=config,
        api_key="explicit-key",
        base_url="https://explicit.example.test/explicit",
        timeout=1.5,
        retries=1,
        client_id="explicit-client",
        user_agent="explicit-agent/1.0",
        transport=transport,
    )

    assert client._config.base_url == "https://explicit.example.test/explicit"
    assert client._config.timeout == 1.5
    assert client._config.retries == 1
    assert client.get("/check") == {"ok": True}
