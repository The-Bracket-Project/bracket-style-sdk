from bracket_sdk import OceanResult, OceanScores


def test_ocean_result_parses_nested_scores_payload() -> None:
    payload = {
        "id": "resp-1",
        "scores": {
            "openness": 0.91,
            "conscientiousness": 0.82,
            "extraversion": 0.73,
            "agreeableness": 0.64,
            "neuroticism": 0.55,
        },
    }

    result = OceanResult.from_payload(payload)

    assert result.scores == OceanScores(
        openness=0.91,
        conscientiousness=0.82,
        extraversion=0.73,
        agreeableness=0.64,
        neuroticism=0.55,
    )
    assert result.as_dict() == payload


def test_ocean_result_supports_top_level_scores_for_compatibility() -> None:
    payload = {
        "openness": 0.31,
        "conscientiousness": 0.42,
        "extraversion": 0.53,
        "agreeableness": 0.64,
        "neuroticism": 0.75,
        "note": "legacy shape",
    }

    result = OceanResult.from_payload(payload)

    assert result.scores.as_dict() == {
        "openness": 0.31,
        "conscientiousness": 0.42,
        "extraversion": 0.53,
        "agreeableness": 0.64,
        "neuroticism": 0.75,
    }
    assert result.raw["note"] == "legacy shape"
