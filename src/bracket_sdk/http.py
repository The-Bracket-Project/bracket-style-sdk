import asyncio
import random
import time
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
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
    _IDEMPOTENT_METHODS = frozenset({"GET", "HEAD", "OPTIONS", "TRACE", "PUT", "DELETE"})
    _SENSITIVE_HEADER_NAMES = frozenset({"authorization", "proxy-authorization", "x-api-key"})

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
        request_headers = kwargs.pop("headers", None)
        headers = apply_auth_headers(request_headers, self._config.api_key, self._config.client_id)
        normalized_method = method.upper()
        next_delay = 0.0

        for attempt in range(retries + 1):
            if attempt and next_delay > 0:
                time.sleep(next_delay)
            next_delay = 0.0
            self._emit_on_request(
                method=normalized_method,
                path=path,
                attempt=attempt,
                retries=retries,
                headers=headers,
            )
            try:
                response = self._client.request(method, path, headers=headers, **kwargs)
            except httpx.RequestError as exc:
                last_exc = exc
                if attempt >= retries:
                    raise NetworkError(str(exc)) from exc
                next_delay = self._compute_backoff_delay(attempt + 1)
                self._emit_on_retry(
                    method=normalized_method,
                    path=path,
                    attempt=attempt,
                    retries=retries,
                    delay_seconds=next_delay,
                    reason="network_error",
                    status_code=None,
                )
                continue

            self._emit_on_response(
                method=normalized_method,
                path=path,
                attempt=attempt,
                retries=retries,
                response=response,
            )
            retry_delay = self._retry_delay_for_response(
                method=normalized_method,
                response=response,
                attempt=attempt,
                retries=retries,
            )
            if retry_delay is not None:
                next_delay = retry_delay
                retry_reason = "rate_limit" if response.status_code == 429 else "http_5xx"
                self._emit_on_retry(
                    method=normalized_method,
                    path=path,
                    attempt=attempt,
                    retries=retries,
                    delay_seconds=next_delay,
                    reason=retry_reason,
                    status_code=response.status_code,
                )
                continue

            self._raise_for_status(response)
            return response

        raise NetworkError("Request failed after retries.") from last_exc

    def _retry_delay_for_response(
        self,
        method: str,
        response: httpx.Response,
        attempt: int,
        retries: int,
    ) -> Optional[float]:
        if attempt >= retries:
            return None

        if response.status_code == 429:
            if self._config.respect_retry_after:
                retry_after_seconds = self._retry_after_seconds(response)
                if retry_after_seconds is not None:
                    return retry_after_seconds
            return self._compute_backoff_delay(attempt + 1)

        if response.status_code >= 500 and self._is_retryable_method(method):
            return self._compute_backoff_delay(attempt + 1)

        return None

    def _is_retryable_method(self, method: str) -> bool:
        return method in self._IDEMPOTENT_METHODS or self._config.allow_non_idempotent_retries

    def _compute_backoff_delay(self, retry_number: int) -> float:
        delay = 0.2 * (2 ** (retry_number - 1))
        if self._config.jitter:
            return random.uniform(0, delay)
        return delay

    def _retry_after_seconds(self, response: httpx.Response) -> Optional[float]:
        raw_retry_after = response.headers.get("Retry-After")
        if not raw_retry_after:
            return None

        raw_retry_after = raw_retry_after.strip()
        if not raw_retry_after:
            return None

        delay: Optional[float] = None
        try:
            delay = float(raw_retry_after)
        except ValueError:
            try:
                retry_at = parsedate_to_datetime(raw_retry_after)
            except (TypeError, ValueError):
                return None
            if retry_at.tzinfo is None:
                retry_at = retry_at.replace(tzinfo=timezone.utc)
            delay = (retry_at - datetime.now(timezone.utc)).total_seconds()

        delay = max(0.0, delay)
        return min(delay, self._config.retry_after_max_seconds)

    def _emit_on_request(
        self,
        method: str,
        path: str,
        attempt: int,
        retries: int,
        headers: dict,
    ) -> None:
        callback = self._config.on_request
        if callback is None:
            return
        callback(
            {
                "method": method,
                "path": path,
                "attempt": attempt + 1,
                "max_attempts": retries + 1,
                "headers": self._redact_headers(headers),
            }
        )

    def _emit_on_response(
        self,
        method: str,
        path: str,
        attempt: int,
        retries: int,
        response: httpx.Response,
    ) -> None:
        callback = self._config.on_response
        if callback is None:
            return
        callback(
            {
                "method": method,
                "path": path,
                "attempt": attempt + 1,
                "max_attempts": retries + 1,
                "status_code": response.status_code,
                "headers": self._redact_headers(dict(response.headers)),
            }
        )

    def _emit_on_retry(
        self,
        method: str,
        path: str,
        attempt: int,
        retries: int,
        delay_seconds: float,
        reason: str,
        status_code: Optional[int],
    ) -> None:
        callback = self._config.on_retry
        if callback is None:
            return
        callback(
            {
                "method": method,
                "path": path,
                "attempt": attempt + 1,
                "next_attempt": attempt + 2,
                "max_attempts": retries + 1,
                "delay_seconds": delay_seconds,
                "reason": reason,
                "status_code": status_code,
            }
        )

    def _redact_headers(self, headers: dict) -> dict:
        redacted = {}
        for name, value in headers.items():
            if name.lower() in self._SENSITIVE_HEADER_NAMES:
                redacted[name] = "[REDACTED]"
                continue
            redacted[name] = value
        return redacted

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
            for key in ("message", "error", "detail", "Message", "errorMessage", "__type"):
                value = payload.get(key)
                if isinstance(value, str) and value:
                    return value

            # API Gateway AWS integrations may wrap downstream errors under Output.
            nested = payload.get("Output")
            if isinstance(nested, dict):
                for key in ("message", "error", "detail", "Message", "errorMessage", "__type"):
                    value = nested.get(key)
                    if isinstance(value, str) and value:
                        return value
            if isinstance(nested, str) and nested:
                return nested

        if isinstance(payload, str) and payload:
            return payload
        return f"HTTP {response.status_code}"


class AsyncHttpClient(HttpClient):
    def __init__(
        self,
        config: SDKConfig,
        transport: Optional[httpx.AsyncBaseTransport] = None,
    ) -> None:
        self._config = config
        self._client = httpx.AsyncClient(
            base_url=config.base_url,
            timeout=config.timeout,
            headers={
                "Accept": "application/json",
                "User-Agent": config.user_agent_value(),
            },
            transport=transport,
        )

    async def close(self) -> None:
        await self._client.aclose()

    async def request(self, method: str, path: str, **kwargs: Any) -> httpx.Response:
        retries = max(0, self._config.retries)
        last_exc: Optional[Exception] = None
        request_headers = kwargs.pop("headers", None)
        headers = apply_auth_headers(request_headers, self._config.api_key, self._config.client_id)
        normalized_method = method.upper()
        next_delay = 0.0

        for attempt in range(retries + 1):
            if attempt and next_delay > 0:
                await asyncio.sleep(next_delay)
            next_delay = 0.0
            self._emit_on_request(
                method=normalized_method,
                path=path,
                attempt=attempt,
                retries=retries,
                headers=headers,
            )
            try:
                response = await self._client.request(method, path, headers=headers, **kwargs)
            except httpx.RequestError as exc:
                last_exc = exc
                if attempt >= retries:
                    raise NetworkError(str(exc)) from exc
                next_delay = self._compute_backoff_delay(attempt + 1)
                self._emit_on_retry(
                    method=normalized_method,
                    path=path,
                    attempt=attempt,
                    retries=retries,
                    delay_seconds=next_delay,
                    reason="network_error",
                    status_code=None,
                )
                continue

            self._emit_on_response(
                method=normalized_method,
                path=path,
                attempt=attempt,
                retries=retries,
                response=response,
            )
            retry_delay = self._retry_delay_for_response(
                method=normalized_method,
                response=response,
                attempt=attempt,
                retries=retries,
            )
            if retry_delay is not None:
                next_delay = retry_delay
                retry_reason = "rate_limit" if response.status_code == 429 else "http_5xx"
                self._emit_on_retry(
                    method=normalized_method,
                    path=path,
                    attempt=attempt,
                    retries=retries,
                    delay_seconds=next_delay,
                    reason=retry_reason,
                    status_code=response.status_code,
                )
                continue

            self._raise_for_status(response)
            return response

        raise NetworkError("Request failed after retries.") from last_exc
