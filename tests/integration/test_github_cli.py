"""Integration tests for GitHub CLI commands wired into the CLI."""

from __future__ import annotations

import io

from agentharness.cli import main


class TestGitHubProtectionPlanCLI:
    def test_protection_plan_returns_success(self) -> None:
        buf = io.StringIO()
        rc = main(["github", "protection", "plan", "--repo", "owner/repo"], output=buf)
        assert rc == 0
        assert "owner/repo" in buf.getvalue()

    def test_protection_plan_json_output(self) -> None:
        import json as _json

        buf = io.StringIO()
        rc = main(
            ["github", "protection", "plan", "--repo", "owner/repo", "--json"],
            output=buf,
        )
        assert rc == 0
        data = _json.loads(buf.getvalue())
        assert "repo" in data["details"]

    def test_protection_apply_no_token_returns_error(
        self, monkeypatch
    ) -> None:
        monkeypatch.delenv("GITHUB_TOKEN", raising=False)
        monkeypatch.delenv("NO_SUCH_TOKEN", raising=False)
        buf = io.StringIO()
        rc = main(
            [
                "github",
                "protection",
                "apply",
                "--repo",
                "owner/repo",
                "--token-env",
                "NO_SUCH_TOKEN",
            ],
            output=buf,
        )
        assert rc != 0
        assert "NO_SUCH_TOKEN" in buf.getvalue() or "token" in buf.getvalue().lower()
