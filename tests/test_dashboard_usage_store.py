import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Optional

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

pytest.importorskip("pydantic")

from services.dashboard.services.usage_store import UsageEvent, UsageStore, summarize_events


def _event(
    *,
    client_id: str,
    org_id: Optional[str],
    status_code: int,
    minutes_ago: int = 0,
) -> UsageEvent:
    return UsageEvent(
        client_id=client_id,
        org_id=org_id,
        endpoint="/v1/modules/text/inference",
        method="POST",
        status_code=status_code,
        timestamp=datetime.now(timezone.utc) - timedelta(minutes=minutes_ago),
    )


def test_summarize_events_includes_org_rollups() -> None:
    events = [
        _event(client_id="key-a1", org_id="org-a", status_code=200, minutes_ago=10),
        _event(client_id="key-a2", org_id="org-a", status_code=500, minutes_ago=20),
        _event(client_id="key-b1", org_id="org-b", status_code=201, minutes_ago=30),
    ]

    summary = summarize_events(events, window_hours=24, top_n=5)

    assert summary["total_calls"] == 3
    assert summary["unique_orgs"] == 2
    assert summary["active_orgs_24h"] == 2
    assert summary["top_orgs"][0]["org_id"] == "org-a"
    assert summary["top_orgs"][0]["calls"] == 2
    assert summary["top_orgs"][0]["unique_clients"] == 2


def test_usage_store_filters_by_org_including_unknown() -> None:
    store = UsageStore()
    store.add_event(_event(client_id="key-1", org_id="org-1", status_code=200))
    store.add_event(_event(client_id="key-2", org_id=None, status_code=200))

    org_events = store.list_events(org_id="org-1")
    unknown_events = store.list_events(org_id="unknown")
    unknown_summary = store.summary(org_id="unknown")

    assert len(org_events) == 1
    assert org_events[0].client_id == "key-1"
    assert len(unknown_events) == 1
    assert unknown_events[0].client_id == "key-2"
    assert unknown_summary["total_calls"] == 1
    assert unknown_summary["unique_orgs"] == 1
    assert unknown_summary["top_orgs"][0]["org_id"] == "unknown"
