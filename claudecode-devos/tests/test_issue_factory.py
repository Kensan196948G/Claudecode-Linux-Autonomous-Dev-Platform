"""Tests for ai/issue_factory.py — candidate generation and deduplication logic."""
import importlib
import json
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

REPO_ROOT = Path(__file__).parent.parent


def _load_module(monkeypatch, tmp_path, extra_env=None):
    state_file = tmp_path / "config" / "state.json"
    issues_dir = tmp_path / "runtime" / "issues"
    state_file.parent.mkdir(parents=True)
    issues_dir.mkdir(parents=True)

    state_file.write_text(json.dumps({
        "goal": {"title": "test", "defined": True},
        "kpi": {"success_rate_target": 0.9, "current_success_rate": 0.5, "status": "unmet"},
        "ci": {"last_run_status": None, "repo_path": str(tmp_path), "stable": False, "stable_blockers": [], "last_failure_summary": None},
        "automation": {"auto_issue_generation": False},
    }), encoding="utf-8")

    monkeypatch.setenv("DEVOS_HOME", str(tmp_path))
    monkeypatch.setenv("DEVOS_STATE_FILE", str(state_file))
    monkeypatch.setenv("GITHUB_AUTO_ISSUE_GENERATION", "false")
    if extra_env:
        for k, v in extra_env.items():
            monkeypatch.setenv(k, v)

    if "ai.issue_factory" in sys.modules:
        del sys.modules["ai.issue_factory"]
    sys.path.insert(0, str(REPO_ROOT))
    import ai.issue_factory as factory
    importlib.reload(factory)
    return factory, state_file


# ---------------------------------------------------------------------------
# state_candidates — pure function tests (no subprocess)
# ---------------------------------------------------------------------------

class TestStateCandidates:
    def test_goal_undefined_generates_p1(self, monkeypatch, tmp_path):
        factory, _ = _load_module(monkeypatch, tmp_path)
        state = {"goal": {"defined": False}, "kpi": {}, "ci": {}}
        candidates = factory.state_candidates(state)
        titles = [c["title"] for c in candidates]
        assert any("Goal" in t for t in titles)
        assert any("P1" in c["labels"] for c in candidates if "Goal" in c["title"])

    def test_kpi_unmet_generates_p2(self, monkeypatch, tmp_path):
        factory, _ = _load_module(monkeypatch, tmp_path)
        state = {
            "goal": {"defined": True},
            "kpi": {"status": "unmet", "current_success_rate": 0.4, "success_rate_target": 0.9},
            "ci": {},
        }
        candidates = factory.state_candidates(state)
        assert any("KPI" in c["title"] for c in candidates)
        kpi_c = next(c for c in candidates if "KPI" in c["title"])
        assert "P2" in kpi_c["labels"]

    def test_ci_failure_generates_p1(self, monkeypatch, tmp_path):
        factory, _ = _load_module(monkeypatch, tmp_path)
        state = {
            "goal": {"defined": True},
            "kpi": {},
            "ci": {"last_run_status": "failure", "last_failure_summary": "build failed", "stable": True, "stable_blockers": []},
        }
        candidates = factory.state_candidates(state)
        assert any("CI" in c["title"] for c in candidates)

    def test_stable_blockers_generates_p2(self, monkeypatch, tmp_path):
        factory, _ = _load_module(monkeypatch, tmp_path)
        state = {
            "goal": {"defined": True},
            "kpi": {},
            "ci": {"last_run_status": None, "stable": False, "stable_blockers": ["lint failed"]},
        }
        candidates = factory.state_candidates(state)
        assert any("STABLE" in c["title"] for c in candidates)

    def test_all_ok_no_candidates(self, monkeypatch, tmp_path):
        factory, _ = _load_module(monkeypatch, tmp_path)
        state = {
            "goal": {"defined": True},
            "kpi": {"status": "met"},
            "ci": {"last_run_status": "success", "stable": True, "stable_blockers": []},
        }
        candidates = factory.state_candidates(state)
        assert candidates == []


# ---------------------------------------------------------------------------
# suppress_low_priority — pure function tests
# ---------------------------------------------------------------------------

class TestSuppressLowPriority:
    def test_p1_present_drops_p3(self, monkeypatch, tmp_path):
        factory, _ = _load_module(monkeypatch, tmp_path)
        candidates = [
            {"title": "high", "labels": ["P1"]},
            {"title": "low", "labels": ["P3"]},
            {"title": "medium", "labels": ["P2"]},
        ]
        result = factory.suppress_low_priority(candidates)
        titles = [c["title"] for c in result]
        assert "high" in titles
        assert "medium" in titles
        assert "low" not in titles

    def test_no_p1_keeps_all(self, monkeypatch, tmp_path):
        factory, _ = _load_module(monkeypatch, tmp_path)
        candidates = [
            {"title": "medium", "labels": ["P2"]},
            {"title": "low", "labels": ["P3"]},
        ]
        result = factory.suppress_low_priority(candidates)
        assert len(result) == 2


# ---------------------------------------------------------------------------
# existing_titles — mocked gh CLI
# ---------------------------------------------------------------------------

class TestExistingTitles:
    def test_returns_titles_from_gh(self, monkeypatch, tmp_path):
        factory, _ = _load_module(monkeypatch, tmp_path)
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = json.dumps([{"title": "Issue A"}, {"title": "Issue B"}])

        with patch.object(factory, "run", return_value=mock_result):
            titles = factory.existing_titles(str(tmp_path))
        assert titles == {"Issue A", "Issue B"}

    def test_gh_failure_returns_empty_set(self, monkeypatch, tmp_path):
        factory, _ = _load_module(monkeypatch, tmp_path)
        mock_result = MagicMock()
        mock_result.returncode = 1
        mock_result.stdout = ""

        with patch.object(factory, "run", return_value=mock_result):
            titles = factory.existing_titles(str(tmp_path))
        assert titles == set()

    def test_invalid_json_returns_empty_set(self, monkeypatch, tmp_path):
        factory, _ = _load_module(monkeypatch, tmp_path)
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = "not-json"

        with patch.object(factory, "run", return_value=mock_result):
            titles = factory.existing_titles(str(tmp_path))
        assert titles == set()


# ---------------------------------------------------------------------------
# create_issues — mocked gh CLI, deduplication check
# ---------------------------------------------------------------------------

class TestCreateIssues:
    def test_skips_existing_titles(self, monkeypatch, tmp_path):
        factory, _ = _load_module(monkeypatch, tmp_path)
        existing_mock = MagicMock(returncode=0, stdout=json.dumps([{"title": "Already Exists"}]))
        create_mock = MagicMock(returncode=0, stdout="https://github.com/x/y/issues/1")

        def side_effect(cmd, cwd):
            if "list" in cmd:
                return existing_mock
            return create_mock

        with patch.object(factory, "run", side_effect=side_effect):
            created = factory.create_issues(str(tmp_path), [
                {"title": "Already Exists", "body": "...", "labels": []},
                {"title": "New Issue", "body": "...", "labels": ["P2"]},
            ])
        assert len(created) == 1
        assert "https://github.com" in created[0]

    def test_respects_create_limit(self, monkeypatch, tmp_path):
        factory, _ = _load_module(monkeypatch, tmp_path, extra_env={"ISSUE_FACTORY_CREATE_LIMIT": "1"})
        importlib.reload(factory)
        list_mock = MagicMock(returncode=0, stdout="[]")
        create_mock = MagicMock(returncode=0, stdout="https://github.com/x/y/issues/1")

        def side_effect(cmd, cwd):
            if "list" in cmd:
                return list_mock
            return create_mock

        with patch.object(factory, "run", side_effect=side_effect):
            created = factory.create_issues(str(tmp_path), [
                {"title": "Issue 1", "body": "", "labels": []},
                {"title": "Issue 2", "body": "", "labels": []},
                {"title": "Issue 3", "body": "", "labels": []},
            ])
        assert len(created) == 1
