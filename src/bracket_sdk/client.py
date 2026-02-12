import os
from typing import Any, Callable, Iterable, Iterator, Optional

import httpx

from bracket_sdk.config import (
    DEFAULT_ALLOW_NON_IDEMPOTENT_RETRIES,
    DEFAULT_BASE_URL,
    DEFAULT_JITTER,
    DEFAULT_RESPECT_RETRY_AFTER,
    DEFAULT_RETRIES,
    DEFAULT_RETRY_AFTER_MAX_SECONDS,
    DEFAULT_TIMEOUT,
    SDKConfig,
)
from bracket_sdk.http import HttpClient


class BracketClient:
    def __init__(
        self,
        api_key: Optional[str] = None,
        config: Optional[SDKConfig] = None,
        base_url: Optional[str] = None,
        timeout: Optional[float] = None,
        retries: Optional[int] = None,
        client_id: Optional[str] = None,
        user_agent: Optional[str] = None,
        transport: Optional[httpx.BaseTransport] = None,
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
        self._http = HttpClient(resolved_config, transport=transport)

    def close(self) -> None:
        self._http.close()

    def request_raw(self, method: str, path: str, **kwargs: Any) -> httpx.Response:
        return self._http.request(method, path, **kwargs)

    def request(self, method: str, path: str, **kwargs: Any) -> Any:
        response = self._http.request(method, path, **kwargs)
        return self._parse_response(response)

    def get(self, path: str, params: Optional[dict] = None, **kwargs: Any) -> Any:
        return self.request("GET", path, params=params, **kwargs)

    def post(self, path: str, json: Optional[dict] = None, **kwargs: Any) -> Any:
        return self.request("POST", path, json=json, **kwargs)

    def put(self, path: str, json: Optional[dict] = None, **kwargs: Any) -> Any:
        return self.request("PUT", path, json=json, **kwargs)

    def delete(self, path: str, **kwargs: Any) -> Any:
        return self.request("DELETE", path, **kwargs)

    def health(self) -> Any:
        return self.get("/v1/health")

    def paginate(
        self,
        *,
        extract_items: Callable[[Any], Iterable[Any]],
        extract_next_cursor: Callable[[Any], Optional[Any]],
        request_fn: Optional[Callable[[Optional[Any]], Any]] = None,
        method: str = "GET",
        path: Optional[str] = None,
        params: Optional[dict] = None,
        json: Optional[Any] = None,
        cursor_param: str = "cursor",
        initial_cursor: Optional[Any] = None,
        **kwargs: Any,
    ) -> Iterator[Any]:
        if request_fn is not None and path is not None:
            raise ValueError("Provide either request_fn or path/method, not both.")
        if request_fn is None and path is None:
            raise ValueError("path is required when request_fn is not provided.")

        cursor: Optional[Any] = initial_cursor
        while True:
            if request_fn is not None:
                page = request_fn(cursor)
            else:
                page_params = dict(params) if params else {}
                if cursor is not None:
                    page_params[cursor_param] = cursor
                page = self.request(
                    method,
                    path,
                    params=page_params or None,
                    json=json,
                    **kwargs,
                )

            items = extract_items(page)
            if items is not None:
                for item in items:
                    yield item

            cursor = extract_next_cursor(page)
            if cursor is None:
                break

    def get_ocean(
        self,
        payload: Optional[Any] = None,
        *,
        text: Optional[str] = None,
        explain: Optional[bool] = None,
        user_id: Optional[str] = None,
        lang: Optional[str] = None,
        granularity: Optional[str] = None,
        **kwargs: Any,
    ) -> Any:
        body: Any

        explicit_fields_provided = any(
            value is not None for value in (text, explain, user_id, lang, granularity)
        )
        if payload is not None and explicit_fields_provided:
            raise ValueError("Provide either payload or explicit fields, not both.")

        if payload is None:
            normalized_text = (text or "").strip()
            if not normalized_text:
                raise ValueError("text is required and must be a non-empty string.")
            body = {"text": normalized_text}
            if explain is not None:
                body["explain"] = explain
            if user_id is not None:
                body["user_id"] = user_id
            if lang is not None:
                body["lang"] = lang
            if granularity is not None:
                body["granularity"] = granularity
        else:
            body = payload
            if isinstance(body, dict):
                # Backward-compatible alias for earlier examples.
                if "text" not in body and "prompt" in body and isinstance(body["prompt"], str):
                    body = {**body, "text": body["prompt"]}
                    body.pop("prompt", None)

                if "text" in body:
                    value = body.get("text")
                    if not isinstance(value, str) or not value.strip():
                        raise ValueError("text is required and must be a non-empty string.")

        return self.post("/v1/modules/text-to-ocean/inference", json=body, **kwargs)

    def _parse_response(self, response: httpx.Response) -> Any:
        content_type = response.headers.get("content-type", "")
        if "application/json" in content_type:
            return response.json()
        if response.text:
            return response.text
        return None

    def __enter__(self) -> "BracketClient":
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self.close()


def _coalesce(*values: Optional[Any]) -> Optional[Any]:
    for value in values:
        if value is not None:
            return value
    return None


def _env_optional_str(name: str) -> Optional[str]:
    value = os.getenv(name)
    if value is None:
        return None
    normalized = value.strip()
    return normalized or None


def _parse_env_timeout(name: str) -> Optional[float]:
    raw = _env_optional_str(name)
    if raw is None:
        return None
    try:
        timeout = float(raw)
    except ValueError as exc:
        raise ValueError(f"Invalid {name}: expected a positive number, got {raw!r}.") from exc
    if timeout <= 0:
        raise ValueError(f"Invalid {name}: expected a positive number, got {raw!r}.")
    return timeout


def _parse_env_retries(name: str) -> Optional[int]:
    raw = _env_optional_str(name)
    if raw is None:
        return None
    try:
        retries = int(raw)
    except ValueError as exc:
        raise ValueError(f"Invalid {name}: expected a non-negative integer, got {raw!r}.") from exc
    if retries < 0:
        raise ValueError(f"Invalid {name}: expected a non-negative integer, got {raw!r}.")
    return retries


def _resolve_sdk_config(
    *,
    api_key: Optional[str],
    config: Optional[SDKConfig],
    base_url: Optional[str],
    timeout: Optional[float],
    retries: Optional[int],
    client_id: Optional[str],
    user_agent: Optional[str],
) -> SDKConfig:
    env_api_key = _env_optional_str("BRACKET_API_KEY")
    env_base_url = _env_optional_str("BRACKET_BASE_URL")
    env_client_id = _env_optional_str("BRACKET_CLIENT_ID")
    env_user_agent = _env_optional_str("BRACKET_USER_AGENT")
    env_timeout = _parse_env_timeout("BRACKET_TIMEOUT")
    env_retries = _parse_env_retries("BRACKET_RETRIES")

    base_config = config
    resolved_api_key = _coalesce(api_key, base_config.api_key if base_config else None, env_api_key)
    if not resolved_api_key:
        raise ValueError(
            "api_key is required. Provide api_key/config or set BRACKET_API_KEY."
        )

    resolved_base_url = _coalesce(
        base_url,
        base_config.base_url if base_config else None,
        env_base_url,
        DEFAULT_BASE_URL,
    )
    resolved_timeout = _coalesce(
        timeout,
        base_config.timeout if base_config else None,
        env_timeout,
        DEFAULT_TIMEOUT,
    )
    resolved_retries = _coalesce(
        retries,
        base_config.retries if base_config else None,
        env_retries,
        DEFAULT_RETRIES,
    )
    resolved_client_id = _coalesce(
        client_id,
        base_config.client_id if base_config else None,
        env_client_id,
    )
    resolved_user_agent = _coalesce(
        user_agent,
        base_config.user_agent if base_config else None,
        env_user_agent,
    )
    resolved_allow_non_idempotent_retries = (
        base_config.allow_non_idempotent_retries
        if base_config
        else DEFAULT_ALLOW_NON_IDEMPOTENT_RETRIES
    )
    resolved_respect_retry_after = (
        base_config.respect_retry_after if base_config else DEFAULT_RESPECT_RETRY_AFTER
    )
    resolved_jitter = base_config.jitter if base_config else DEFAULT_JITTER
    resolved_retry_after_max_seconds = (
        base_config.retry_after_max_seconds if base_config else DEFAULT_RETRY_AFTER_MAX_SECONDS
    )
    resolved_on_request = base_config.on_request if base_config else None
    resolved_on_response = base_config.on_response if base_config else None
    resolved_on_retry = base_config.on_retry if base_config else None

    return SDKConfig(
        api_key=resolved_api_key,
        base_url=resolved_base_url,
        timeout=resolved_timeout,
        retries=resolved_retries,
        client_id=resolved_client_id,
        user_agent=resolved_user_agent,
        allow_non_idempotent_retries=resolved_allow_non_idempotent_retries,
        respect_retry_after=resolved_respect_retry_after,
        jitter=resolved_jitter,
        retry_after_max_seconds=resolved_retry_after_max_seconds,
        on_request=resolved_on_request,
        on_response=resolved_on_response,
        on_retry=resolved_on_retry,
    )
