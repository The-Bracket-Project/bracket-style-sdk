from dataclasses import dataclass
from typing import Any, Mapping, Optional

from bracket_sdk.models.ocean import OceanScores


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


def _as_optional_float(value: Any) -> Optional[float]:
    if isinstance(value, (int, float)):
        return float(value)
    return None


def _as_optional_ocean_scores(value: Any) -> Optional[OceanScores]:
    if isinstance(value, Mapping):
        return OceanScores.from_mapping(value)
    return None


@dataclass(frozen=True)
class PersonalizedRewriteMeta:
    request_id: Optional[str] = None
    profile_source: Optional[str] = None
    profile_version: Optional[str] = None
    model_version: Optional[str] = None
    control_header: Optional[str] = None
    ocean_inferred: Optional[OceanScores] = None
    ocean_effective: Optional[OceanScores] = None
    ema_alpha: Optional[float] = None
    user_profile_key: Optional[str] = None

    @classmethod
    def from_mapping(cls, payload: Mapping[str, Any]) -> "PersonalizedRewriteMeta":
        return cls(
            request_id=_as_optional_str(payload.get("request_id")),
            profile_source=_as_optional_str(payload.get("profile_source")),
            profile_version=_as_optional_str(payload.get("profile_version")),
            model_version=_as_optional_str(payload.get("model_version")),
            control_header=_as_optional_str(payload.get("control_header")),
            ocean_inferred=_as_optional_ocean_scores(payload.get("ocean_inferred")),
            ocean_effective=_as_optional_ocean_scores(payload.get("ocean_effective")),
            ema_alpha=_as_optional_float(payload.get("ema_alpha")),
            user_profile_key=_as_optional_str(payload.get("user_profile_key")),
        )


@dataclass(frozen=True)
class PersonalizedRewriteResult:
    output_text: str
    meta: PersonalizedRewriteMeta
    raw: dict

    @classmethod
    def from_payload(cls, payload: Mapping[str, Any]) -> "PersonalizedRewriteResult":
        if not isinstance(payload, Mapping):
            raise TypeError("PersonalizedRewriteResult.from_payload expects a mapping payload.")

        output_text = payload.get("output_text")
        if not isinstance(output_text, str):
            output_text = ""

        meta_payload = payload.get("meta")
        if isinstance(meta_payload, Mapping):
            meta = PersonalizedRewriteMeta.from_mapping(meta_payload)
        else:
            meta = PersonalizedRewriteMeta()

        return cls(
            output_text=output_text,
            meta=meta,
            raw=dict(payload),
        )

    def as_dict(self) -> dict:
        return dict(self.raw)
