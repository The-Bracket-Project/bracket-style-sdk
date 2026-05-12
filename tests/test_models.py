from bracket_sdk import OceanResult, OceanScores, PersonalizedRewriteResult, RewriteResult


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


def test_rewrite_result_parses_output_and_meta() -> None:
    payload = {
        "output_text": "Styled output",
        "meta": {
            "request_id": "req-1",
            "profile_source": "dynamodb",
            "profile_version": "v7",
            "model_version": "style-endpoint-v1",
        },
    }

    result = RewriteResult.from_payload(payload)

    assert result.output_text == "Styled output"
    assert result.meta.request_id == "req-1"
    assert result.meta.profile_source == "dynamodb"
    assert result.meta.profile_version == "v7"
    assert result.meta.model_version == "style-endpoint-v1"
    assert result.as_dict() == payload


def test_personalized_rewrite_result_parses_rich_meta() -> None:
    payload = {
        "output_text": "Personalized output",
        "meta": {
            "request_id": "req-2",
            "profile_source": "dynamodb_user_ema",
            "profile_version": "v9",
            "model_version": "style-endpoint-v2",
            "control_header": "<k tw=52 dir=58>",
            "ocean_inferred": {
                "openness": 0.61,
                "conscientiousness": 0.52,
                "extraversion": 0.47,
                "agreeableness": 0.66,
                "neuroticism": 0.42,
            },
            "ocean_effective": {
                "openness": 0.58,
                "conscientiousness": 0.55,
                "extraversion": 0.49,
                "agreeableness": 0.64,
                "neuroticism": 0.45,
            },
            "ema_alpha": 0.35,
            "user_profile_key": "user#user-123",
        },
    }

    result = PersonalizedRewriteResult.from_payload(payload)

    assert result.output_text == "Personalized output"
    assert result.meta.request_id == "req-2"
    assert result.meta.profile_source == "dynamodb_user_ema"
    assert result.meta.control_header == "<k tw=52 dir=58>"
    assert result.meta.ocean_inferred is not None
    assert result.meta.ocean_inferred.openness == 0.61
    assert result.meta.ocean_effective is not None
    assert result.meta.ocean_effective.agreeableness == 0.64
    assert result.meta.ema_alpha == 0.35
    assert result.meta.user_profile_key == "user#user-123"
    assert result.as_dict() == payload
