from typing import Any, Optional

import httpx

from bracket_sdk.config import DEFAULT_BASE_URL, DEFAULT_RETRIES, DEFAULT_TIMEOUT, SDKConfig
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
        transport: Optional[httpx.BaseTransport] = None,
    ) -> None:
        if config is None:
            if not api_key:
                raise ValueError("api_key is required when config is not provided")
            config = SDKConfig(
                api_key=api_key,
                base_url=base_url or DEFAULT_BASE_URL,
                timeout=timeout if timeout is not None else DEFAULT_TIMEOUT,
                retries=retries if retries is not None else DEFAULT_RETRIES,
                client_id=client_id,
            )
        self._config = config
        self._http = HttpClient(config, transport=transport)

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
