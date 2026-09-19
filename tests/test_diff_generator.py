"""
Tests for Cross-Repository Diff & Unified Patch Generator
"""

import pytest
from agent_orchestrator.diff_generator import CrossRepoDiffGenerator


def test_unified_diff_generation():
    generator = CrossRepoDiffGenerator()
    old_code = "def hello():\n    return 'old'\n"
    new_code = "def hello():\n    return 'new'\n"

    diff = generator.generate_unified_diff("src/test.py", old_code, new_code)
    assert "--- a/src/test.py" in diff
    assert "+++ b/src/test.py" in diff
    assert "-    return 'old'" in diff
    assert "+    return 'new'" in diff


def test_cross_repo_diff_synthesis():
    generator = CrossRepoDiffGenerator()
    res = generator.synthesize_cross_repo_patches("Deprecate /v1/auth/verify and migrate to /v2/auth/token")

    assert res["status"] == "success"
    assert res["total_repositories"] == 3
    assert res["total_files_affected"] == 3
    assert res["total_additions"] > 0
    assert res["total_deletions"] > 0

    repos = [pr["repo"] for pr in res["pull_requests"]]
    assert "repo_auth_core" in repos
    assert "repo_frontend_portal" in repos
    assert "repo_shared_sdk" in repos

    # Verify cross-linked PR references
    auth_pr = next(pr for pr in res["pull_requests"] if pr["repo"] == "repo_auth_core")
    assert len(auth_pr["cross_linked_prs"]) >= 2
    assert "repo_frontend_portal#48" in auth_pr["cross_linked_prs"]
