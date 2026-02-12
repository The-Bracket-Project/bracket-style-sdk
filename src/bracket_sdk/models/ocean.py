from dataclasses import dataclass
from typing import Any, Mapping, Optional


@dataclass(frozen=True)
class OceanScores:
    openness: Optional[float] = None
    conscientiousness: Optional[float] = None
    extraversion: Optional[float] = None
    agreeableness: Optional[float] = None
    neuroticism: Optional[float] = None

    @classmethod
    def from_mapping(cls, payload: Mapping[str, Any]) -> "OceanScores":
        return cls(
            openness=_as_optional_float(payload.get("openness")),
            conscientiousness=_as_optional_float(payload.get("conscientiousness")),
            extraversion=_as_optional_float(payload.get("extraversion")),
            agreeableness=_as_optional_float(payload.get("agreeableness")),
            neuroticism=_as_optional_float(payload.get("neuroticism")),
        )

    def as_dict(self) -> dict:
        return {
            "openness": self.openness,
            "conscientiousness": self.conscientiousness,
            "extraversion": self.extraversion,
            "agreeableness": self.agreeableness,
            "neuroticism": self.neuroticism,
        }


@dataclass(frozen=True)
class OceanResult:
    scores: OceanScores
    raw: dict

    @classmethod
    def from_payload(cls, payload: Mapping[str, Any]) -> "OceanResult":
        if not isinstance(payload, Mapping):
            raise TypeError("OceanResult.from_payload expects a mapping payload.")

        raw_payload = dict(payload)
        scores_payload = payload.get("scores")
        if isinstance(scores_payload, Mapping):
            scores = OceanScores.from_mapping(scores_payload)
        else:
            scores = OceanScores.from_mapping(payload)
        return cls(scores=scores, raw=raw_payload)

    def as_dict(self) -> dict:
        return dict(self.raw)


def _as_optional_float(value: Any) -> Optional[float]:
    if isinstance(value, (int, float)):
        return float(value)
    return None
