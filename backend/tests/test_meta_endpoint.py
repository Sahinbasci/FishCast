"""Tests for /_meta deploy guard endpoint.

Ensures /_meta returns runtime config for deploy verification.
"""

from __future__ import annotations

from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def client():
    """Create test client with mocked Firebase but real lifespan."""
    with patch("app.services.firebase.initialize_firebase"):
        from app.main import app
        with TestClient(app) as c:
            yield c


class TestMetaEndpoint:
    def test_meta_returns_offline_mode_false(self, client):
        """/_meta returns offlineMode field (default false)."""
        response = client.get("/api/v1/_meta")
        assert response.status_code == 200
        data = response.json()
        assert "offlineMode" in data
        assert data["offlineMode"] is False

    def test_meta_returns_allow_trace_full(self, client):
        """/_meta returns allowTraceFull field."""
        response = client.get("/api/v1/_meta")
        data = response.json()
        assert "allowTraceFull" in data
        assert isinstance(data["allowTraceFull"], bool)

    def test_meta_returns_rules_count(self, client):
        """/_meta returns rulesCount matching loaded rules."""
        response = client.get("/api/v1/_meta")
        data = response.json()
        assert "rulesCount" in data
        assert isinstance(data["rulesCount"], int)
        assert data["rulesCount"] > 0

    def test_meta_returns_ruleset_version(self, client):
        """/_meta returns rulesetVersion string."""
        response = client.get("/api/v1/_meta")
        data = response.json()
        assert "rulesetVersion" in data
        assert data["rulesetVersion"] == "20260222.2"

    def test_meta_returns_build_sha(self, client):
        """/_meta returns buildSha from GIT_SHA env (default 'unknown')."""
        response = client.get("/api/v1/_meta")
        data = response.json()
        assert "buildSha" in data
        assert isinstance(data["buildSha"], str)

    def test_meta_with_git_sha_env(self, client, monkeypatch):
        """/_meta returns custom GIT_SHA when env is set."""
        monkeypatch.setenv("GIT_SHA", "abc123def")
        response = client.get("/api/v1/_meta")
        data = response.json()
        assert data["buildSha"] == "abc123def"
