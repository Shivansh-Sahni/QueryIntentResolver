from __future__ import annotations

from qir_v1.api import ResolveRequest


def test_request_accepts_optional_future_context() -> None:
    request = ResolveRequest(
        query_text="MIT",
        persona="high_school_student",
        page="home",
        filters={"state": "MI"},
        context=[],
        session={"session_id": "x"},
    )
    assert request.query_text == "MIT"
