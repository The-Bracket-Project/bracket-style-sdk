import httpx
import pytest

from bracket_sdk import AsyncBracketClient


@pytest.mark.asyncio
async def test_async_client_get_and_health() -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        assert request.headers.get("x-api-key") == "test-key"
        if request.url.path == "/v1/health":
            return httpx.Response(200, json={"status": "ok"}, request=request)
        return httpx.Response(200, json={"ok": True}, request=request)

    transport = httpx.MockTransport(handler)
    client = AsyncBracketClient(api_key="test-key", transport=transport)

    assert await client.get("/ping") == {"ok": True}
    assert await client.health() == {"status": "ok"}
    await client.close()


@pytest.mark.asyncio
async def test_async_client_retries_429_with_retry_after(monkeypatch: pytest.MonkeyPatch) -> None:
    attempts = 0
    sleep_calls = []

    async def fake_sleep(value: float) -> None:
        sleep_calls.append(value)

    monkeypatch.setattr("bracket_sdk.http.asyncio.sleep", fake_sleep)

    async def handler(request: httpx.Request) -> httpx.Response:
        nonlocal attempts
        attempts += 1
        if attempts == 1:
            return httpx.Response(
                429,
                json={"message": "slow down"},
                headers={"Retry-After": "1"},
                request=request,
            )
        return httpx.Response(200, json={"ok": True}, request=request)

    transport = httpx.MockTransport(handler)
    client = AsyncBracketClient(api_key="test-key", retries=1, transport=transport)

    assert await client.get("/limited") == {"ok": True}
    assert attempts == 2
    assert sleep_calls == [1.0]
    await client.close()


@pytest.mark.asyncio
async def test_async_client_supports_async_context_manager() -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"ok": True}, request=request)

    transport = httpx.MockTransport(handler)
    async with AsyncBracketClient(api_key="test-key", transport=transport) as client:
        assert await client.get("/ping") == {"ok": True}
