from dataclasses import dataclass
from typing import Any, Mapping, Optional


@dataclass(frozen=True)
class RewriteMeta:
    request_id: Optional[str] = None
    profile_source: Optional[str] = None
    profile_version: Optional[str] = None
    model_version: Optional[str] = None

    @classmethod
    def from_mapping(cls, payload: Mapping[str, Any]) -> "RewriteMeta":
        return cls(
            request_id=_as_optional_str(payload.get("request_id")),
            profile_source=_as_optional_str(payload.get("profile_source")),
            profile_version=_as_optional_str(payload.get("profile_version")),
            model_version=_as_optional_str(payload.get("model_version")),
        )


@dataclass(frozen=True)
class RewriteResult:
    output_text: str
    meta: RewriteMeta
    raw: dict

    @classmethod
    def from_payload(cls, payload: Mapping[str, Any]) -> "RewriteResult":
        if not isinstance(payload, Mapping):
            raise TypeError("RewriteResult.from_payload expects a mapping payload.")

        output_text = payload.get("output_text")
        if not isinstance(output_text, str):
            output_text = ""

        meta_payload = payload.get("meta")
        if isinstance(meta_payload, Mapping):
            meta = RewriteMeta.from_mapping(meta_payload)
        else:
            meta = RewriteMeta()

        return cls(
            output_text=output_text,
            meta=meta,
            raw=dict(payload),
        )

    def as_dict(self) -> dict:
        return dict(self.raw)


def _as_optional_str(value: Any) -> Optional[str]:
    if isinstance(value, str) and value:
        return value
    return None
