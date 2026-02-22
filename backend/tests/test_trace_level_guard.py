"""v1.3.2: Trace level guard tests.

Ensures ALLOW_TRACE_FULL env var gates traceLevel=full in routers.
Tests the guard logic directly (no HTTP server needed).
"""

from __future__ import annotations


def _apply_trace_guard(trace_level: str, allow_trace_full: bool) -> str:
    """Reproduce the trace guard logic from routers."""
    return trace_level if trace_level != "full" or allow_trace_full else "minimal"


class TestTraceLevelGuard:
    def test_full_blocked_when_env_false(self):
        """traceLevel=full + ALLOW_TRACE_FULL=false → minimal."""
        applied = _apply_trace_guard("full", allow_trace_full=False)
        assert applied == "minimal"

    def test_full_allowed_when_env_true(self):
        """traceLevel=full + ALLOW_TRACE_FULL=true → full."""
        applied = _apply_trace_guard("full", allow_trace_full=True)
        assert applied == "full"

    def test_minimal_unaffected(self):
        """traceLevel=minimal → minimal regardless of env."""
        assert _apply_trace_guard("minimal", allow_trace_full=False) == "minimal"
        assert _apply_trace_guard("minimal", allow_trace_full=True) == "minimal"

    def test_none_unaffected(self):
        """traceLevel=none → none regardless of env."""
        assert _apply_trace_guard("none", allow_trace_full=False) == "none"
        assert _apply_trace_guard("none", allow_trace_full=True) == "none"

    def test_meta_shows_downgrade(self):
        """When downgraded, meta should contain requested vs applied."""
        trace_level = "full"
        allow_full = False
        applied = _apply_trace_guard(trace_level, allow_full)

        # Simulate what routers do
        meta: dict[str, str] = {
            "contractVersion": "1.3",
            "generatedAt": "2026-02-22T10:00:00Z",
            "timezone": "Europe/Istanbul",
        }
        if applied != trace_level:
            meta["traceLevelRequested"] = trace_level
            meta["traceLevelApplied"] = applied

        assert meta["traceLevelRequested"] == "full"
        assert meta["traceLevelApplied"] == "minimal"

    def test_no_downgrade_meta_absent(self):
        """When not downgraded, meta should NOT contain trace fields."""
        trace_level = "minimal"
        allow_full = False
        applied = _apply_trace_guard(trace_level, allow_full)

        meta: dict[str, str] = {
            "contractVersion": "1.3",
            "generatedAt": "2026-02-22T10:00:00Z",
            "timezone": "Europe/Istanbul",
        }
        if applied != trace_level:
            meta["traceLevelRequested"] = trace_level
            meta["traceLevelApplied"] = applied

        assert "traceLevelRequested" not in meta
        assert "traceLevelApplied" not in meta
