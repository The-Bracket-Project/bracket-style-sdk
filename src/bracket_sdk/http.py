import time
from typing import Any, Optional

import httpx

from bracket_sdk.auth import apply_auth_headers
from bracket_sdk.config import SDKConfig
from bracket_sdk.errors import (
    ApiError,
    AuthenticationError,
    NetworkError,
    NotFoundError,
    RateLimitError,
)


class HttpClient:
    def __init__(self, config: SDKConfig, transport: Optional[httpx.BaseTransport] = None) -> None:
        self._config = config
        self._client = httpx.Client(
            base_url=config.base_url,
            timeout=config.timeout,
            headers={
                "Accept": "application/json",
                "User-Agent": config.user_agent_value(),
            },
            transport=transport,
        )

    def close(self) -> None:
        self._client.close()

    def request(self, method: str, path: str, **kwargs: Any) -> httpx.Response:
        retries = max(0, self._config.retries)
        last_exc: Optional[Exception] = None

        for attempt in range(retries + 1):
            if attempt:
                time.sleep(0.2 * (2 ** (attempt - 1)))
            try:
                headers = kwargs.pop("headers", None)
                headers = apply_auth_headers(headers, self._config.api_key, self._config.client_id)
                response = self._client.request(method, path, headers=headers, **kwargs)
            except httpx.RequestError as exc:
                last_exc = exc
                if attempt >= retries:
                    raise NetworkError(str(exc)) from exc
                continue

            if response.status_code >= 500 and attempt < retries:
                continue

            self._raise_for_status(response)
            return response

        raise NetworkError("Request failed after retries.") from last_exc

    def _raise_for_status(self, response: httpx.Response) -> None:
        if response.status_code < 400:
            return

        message = self._extract_error_message(response)
        status_code = response.status_code

        if status_code in (401, 403):
            raise AuthenticationError(message, status_code=status_code, payload=self._payload(response))
        if status_code == 404:
            raise NotFoundError(message, status_code=status_code, payload=self._payload(response))
        if status_code == 429:
            raise RateLimitError(message, status_code=status_code, payload=self._payload(response))

        raise ApiError(message, status_code=status_code, payload=self._payload(response))

    def _payload(self, response: httpx.Response) -> Any:
        try:
            return response.json()
        except ValueError:
            return response.text

    def _extract_error_message(self, response: httpx.Response) -> str:
        payload = self._payload(response)
        if isinstance(payload, dict):
            for key in ("message", "error", "detail"):
                value = payload.get(key)
                if isinstance(value, str) and value:
                    return value
        if isinstance(payload, str) and payload:
            return payload
        return f"HTTP {response.status_code}"
