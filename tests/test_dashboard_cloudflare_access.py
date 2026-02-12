import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from services.dashboard.services import cloudflare_access


@pytest.fixture(autouse=True)
def reset_cloudflare_access_state(monkeypatch: pytest.MonkeyPatch):
    for key in (
        "DASHBOARD_REQUIRE_CF_ACCESS",
        "CF_ACCESS_CLIENT_ID",
        "CF_ACCESS_CLIENT_SECRET",
        "CF_ACCESS_AUD",
        "CF_ACCESS_TEAM_DOMAIN",
        "DASHBOARD_CF_ACCESS_SKIP_PATHS",
    ):
        monkeypatch.delenv(key, raising=False)
    cloudflare_access._verifier = cloudflare_access._UNINITIALIZED


def test_cloudflare_access_verifier_disabled_by_default() -> None:
    assert cloudflare_access.get_cloudflare_access_verifier() is None


def test_cloudflare_access_verifier_raises_when_enabled_but_unconfigured(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("DASHBOARD_REQUIRE_CF_ACCESS", "true")

    with pytest.raises(RuntimeError, match="Cloudflare Access is enabled"):
        cloudflare_access.get_cloudflare_access_verifier()


def test_cloudflare_access_verifier_initializes_with_service_token_config(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("DASHBOARD_REQUIRE_CF_ACCESS", "true")
    monkeypatch.setenv("CF_ACCESS_CLIENT_ID", "client-id")
    monkeypatch.setenv("CF_ACCESS_CLIENT_SECRET", "client-secret")

    verifier = cloudflare_access.get_cloudflare_access_verifier()

    assert verifier is not None
    assert verifier.authorize(
        {
            "cf-access-client-id": "client-id",
            "cf-access-client-secret": "client-secret",
        }
    )
    assert cloudflare_access.get_cloudflare_access_verifier() is verifier
