from typing import Any, Mapping, Optional

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

    async def rewrite_text(
        self,
        payload: Optional[Any] = None,
        *,
        text: Optional[str] = None,
        **kwargs: Any,
    ) -> Any:
        body: Any
        if payload is not None and text is not None:
            raise ValueError("Provide either payload or text, not both.")

        if payload is None:
            normalized_text = (text or "").strip()
            if not normalized_text:
                raise ValueError("text is required and must be a non-empty string.")
            body = {"text": normalized_text}
        else:
            body = payload
            if isinstance(body, dict):
                if "text" not in body and "prompt" in body and isinstance(body["prompt"], str):
                    body = {**body, "text": body["prompt"]}
                    body.pop("prompt", None)

                value = body.get("text")
                if not isinstance(value, str) or not value.strip():
                    raise ValueError("text is required and must be a non-empty string.")

        return await self.post("/v1/modules/text-to-style/inference", json=body, **kwargs)

    async def personalized_rewrite(
        self,
        payload: Optional[Any] = None,
        *,
        user_id: Optional[str] = None,
        user_prompt: Optional[str] = None,
        llm_output: Optional[str] = None,
        context: Optional[Mapping[str, Any]] = None,
        **kwargs: Any,
    ) -> Any:
        body: Any
        explicit_fields_provided = any(
            value is not None for value in (user_id, user_prompt, llm_output, context)
        )
        if payload is not None and explicit_fields_provided:
            raise ValueError("Provide either payload or explicit fields, not both.")

        if payload is None:
            normalized_user_id = (user_id or "").strip()
            normalized_user_prompt = (user_prompt or "").strip()
            normalized_llm_output = (llm_output or "").strip()

            if not normalized_user_id:
                raise ValueError("user_id is required and must be a non-empty string.")
            if not normalized_user_prompt:
                raise ValueError("user_prompt is required and must be a non-empty string.")
            if not normalized_llm_output:
                raise ValueError("llm_output is required and must be a non-empty string.")

            body = {
                "user_id": normalized_user_id,
                "user_prompt": normalized_user_prompt,
                "llm_output": normalized_llm_output,
            }
            if context is not None:
                if not isinstance(context, Mapping):
                    raise ValueError("context must be a mapping/object when provided.")
                body["context"] = dict(context)
        else:
            body = payload
            if isinstance(body, dict):
                for key in ("user_id", "user_prompt", "llm_output"):
                    value = body.get(key)
                    if not isinstance(value, str) or not value.strip():
                        raise ValueError(f"{key} is required and must be a non-empty string.")

                context_payload = body.get("context")
                if context_payload is not None and not isinstance(context_payload, Mapping):
                    raise ValueError("context must be a mapping/object when provided.")

        return await self.post("/v1/modules/personalized-rewrite/inference", json=body, **kwargs)

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
