from typing import Any, Optional

import httpx

from bracket_sdk.client import _resolve_sdk_config
from bracket_sdk.config import SDKConfig
from bracket_sdk.http import AsyncHttpClient


class AsyncBracketClient:
    def __init__(
        self,
        api_key: Optional[str] = None,
        config: Optional[SDKConfig] = None,
        base_url: Optional[str] = None,
        timeout: Optional[float] = None,
        retries: Optional[int] = None,
        client_id: Optional[str] = None,
        user_agent: Optional[str] = None,
        transport: Optional[httpx.AsyncBaseTransport] = None,
    ) -> None:
        resolved_config = _resolve_sdk_config(
            api_key=api_key,
            config=config,
            base_url=base_url,
            timeout=timeout,
            retries=retries,
            client_id=client_id,
            user_agent=user_agent,
        )
        self._config = resolved_config
        self._http = AsyncHttpClient(resolved_config, transport=transport)

    async def close(self) -> None:
        await self._http.close()

    async def request_raw(self, method: str, path: str, **kwargs: Any) -> httpx.Response:
        return await self._http.request(method, path, **kwargs)

    async def request(self, method: str, path: str, **kwargs: Any) -> Any:
        response = await self._http.request(method, path, **kwargs)
        return self._parse_response(response)

    async def get(self, path: str, params: Optional[dict] = None, **kwargs: Any) -> Any:
        return await self.request("GET", path, params=params, **kwargs)

    async def post(self, path: str, json: Optional[dict] = None, **kwargs: Any) -> Any:
        return await self.request("POST", path, json=json, **kwargs)

    async def put(self, path: str, json: Optional[dict] = None, **kwargs: Any) -> Any:
        return await self.request("PUT", path, json=json, **kwargs)

    async def delete(self, path: str, **kwargs: Any) -> Any:
        return await self.request("DELETE", path, **kwargs)

    async def health(self) -> Any:
        return await self.get("/v1/health")

    def _parse_response(self, response: httpx.Response) -> Any:
        content_type = response.headers.get("content-type", "")
        if "application/json" in content_type:
            return response.json()
        if response.text:
            return response.text
        return None

    async def __aenter__(self) -> "AsyncBracketClient":
        return self

    async def __aexit__(self, exc_type, exc, tb) -> None:
        await self.close()
