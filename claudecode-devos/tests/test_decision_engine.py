"""Tests for ops/decision_engine.py — state transition logic."""
import importlib
import json
import sys
from pathlib import Path

MINIMAL_STATE = {
    "system": {"status": "idle"},
    "goal": {"title": "test", "defined": True},
    "kpi": {
        "success_rate_target": 0.9,
        "current_success_rate": 0.5,
        "status": "unmet",
    },
    "automation": {"auto_issue_generation": False, "self_evolution": True},
    "execution": {"max_duration_minutes": 300, "remaining_seconds": 18000},
    "ci": {
        "enabled": True,
        "repo_path": "/tmp/test-repo",
        "repair_attempt_count": 0,
        "repair_attempt_limit": 15,
        "last_run_status": None,
        "stable": False,
    },
    "resources": {
        "memory_free_mb": 8000,
        "swap_used_mb": 100,
        "cpu_percent": 30,
        "loadavg_1m": 1.0,
        "disk_used_percent": 50,
    },
    "decision": {},
    "risk": {},
}


def _load_module(monkeypatch, tmp_path, extra_env=None):
    state_file = tmp_path / "config" / "state.json"
    lock_dir = tmp_path / "runtime" / "tmp"
    decision_log_dir = tmp_path / "runtime" / "decisions"
    state_file.parent.mkdir(parents=True)
    lock_dir.mkdir(parents=True)
    decision_log_dir.mkdir(parents=True)

    import copy
    state_file.write_text(json.dumps(copy.deepcopy(MINIMAL_STATE)), encoding="utf-8")

    monkeypatch.setenv("DEVOS_HOME", str(tmp_path))
    monkeypatch.setenv("DEVOS_STATE_FILE", str(state_file))
    monkeypatch.setenv("DEVOS_LOCK_DIR", str(lock_dir))
    if extra_env:
        for k, v in extra_env.items():
            monkeypatch.setenv(k, v)

    if "ops.decision_engine" in sys.modules:
        del sys.modules["ops.decision_engine"]
    sys.path.insert(0, str(Path(__file__).parent.parent))
    import ops.decision_engine as de
    importlib.reload(de)
    return de, state_file


# ---------------------------------------------------------------------------
# Normal development path
# ---------------------------------------------------------------------------

class TestDecideNormalPath:
    def test_idle_resources_returns_develop(self, monkeypatch, tmp_path):
        de, _ = _load_module(monkeypatch, tmp_path)
        state = json.loads(_.read_text())
        action, reason, mode = de.decide(state)
        assert action == "develop"
        assert mode == "normal"

    def test_decision_stored_in_state(self, monkeypatch, tmp_path):
        de, _ = _load_module(monkeypatch, tmp_path)
        state = json.loads(_.read_text())
        de.decide(state)
        assert state["decision"]["next_action"] == "develop"
        assert state["decision"]["last_decision_at"] is not None


# ---------------------------------------------------------------------------
# Resource pressure → cooldown
# ---------------------------------------------------------------------------

class TestDecideMemoryPressure:
    def test_low_memory_triggers_cooldown(self, monkeypatch, tmp_path):
        de, _ = _load_module(monkeypatch, tmp_path)
        state = json.loads(_.read_text())
        state["resources"]["memory_free_mb"] = 1000  # below 3000 threshold
        action, reason, mode = de.decide(state)
        assert action == "cooldown"
        assert "resource" in reason
        assert mode == "safe"

    def test_high_swap_triggers_cooldown(self, monkeypatch, tmp_path):
        de, _ = _load_module(monkeypatch, tmp_path)
        state = json.loads(_.read_text())
        state["resources"]["swap_used_mb"] = 2000  # above 1000 threshold
        action, _, mode = de.decide(state)
        assert action == "cooldown"

    def test_high_cpu_triggers_cooldown(self, monkeypatch, tmp_path):
        de, _ = _load_module(monkeypatch, tmp_path)
        state = json.loads(_.read_text())
        state["resources"]["cpu_percent"] = 90  # above 85 threshold
        action, _, _ = de.decide(state)
        assert action == "cooldown"


# ---------------------------------------------------------------------------
# Disk pressure → suspend
# ---------------------------------------------------------------------------

class TestDecideDiskPressure:
    def test_disk_full_triggers_suspend(self, monkeypatch, tmp_path):
        de, _ = _load_module(monkeypatch, tmp_path)
        state = json.loads(_.read_text())
        state["resources"]["disk_used_percent"] = 95  # above 90 threshold
        action, reason, _ = de.decide(state)
        assert action == "suspend"
        assert "disk" in reason


# ---------------------------------------------------------------------------
# CI failure → repair_ci
# ---------------------------------------------------------------------------

class TestDecideCIFailure:
    def test_ci_failure_triggers_repair(self, monkeypatch, tmp_path):
        de, _ = _load_module(monkeypatch, tmp_path)
        state = json.loads(_.read_text())
        state["ci"]["last_run_status"] = "failure"
        state["ci"]["repair_attempt_count"] = 0
        action, reason, _ = de.decide(state)
        assert action == "repair_ci"
        assert state["risk"]["ci_unstable"] is True

    def test_repair_limit_exceeded_suspends(self, monkeypatch, tmp_path):
        de, _ = _load_module(monkeypatch, tmp_path)
        state = json.loads(_.read_text())
        state["ci"]["last_run_status"] = "failure"
        state["ci"]["repair_attempt_count"] = 15
        state["ci"]["repair_attempt_limit"] = 15
        action, reason, _ = de.decide(state)
        assert action == "suspend"
        assert "exceeded" in reason


# ---------------------------------------------------------------------------
# ensure_sections defaults
# ---------------------------------------------------------------------------

class TestEnsureSections:
    def test_missing_keys_get_defaults(self, monkeypatch, tmp_path):
        de, _ = _load_module(monkeypatch, tmp_path)
        state = {}
        de.ensure_sections(state)
        assert "goal" in state
        assert "kpi" in state
        assert "decision" in state
        assert state["decision"]["next_action"] == "idle"


# ---------------------------------------------------------------------------
# KPI-driven auto_issue_generation
# ---------------------------------------------------------------------------

class TestAutoIssueGeneration:
    def test_kpi_unmet_enables_issue_generation(self, monkeypatch, tmp_path):
        de, _ = _load_module(monkeypatch, tmp_path)
        state = json.loads(_.read_text())
        state["kpi"]["current_success_rate"] = 0.4
        state["kpi"]["success_rate_target"] = 0.9
        state["automation"]["auto_issue_generation"] = False
        state["automation"]["issue_factory_last_run_at"] = None
        de.decide(state)
        assert state["automation"]["auto_issue_generation"] is True

    def test_kpi_met_disables_issue_generation(self, monkeypatch, tmp_path):
        de, _ = _load_module(monkeypatch, tmp_path)
        state = json.loads(_.read_text())
        state["kpi"]["current_success_rate"] = 0.95
        state["kpi"]["success_rate_target"] = 0.9
        state["automation"]["auto_issue_generation"] = True
        de.decide(state)
        assert state["automation"]["auto_issue_generation"] is False

    def test_recent_run_respects_interval(self, monkeypatch, tmp_path):
        """Should not re-enable if factory ran within ISSUE_FACTORY_INTERVAL."""
        de, _ = _load_module(monkeypatch, tmp_path, extra_env={"ISSUE_FACTORY_INTERVAL_SECONDS": "3600"})
        state = json.loads(_.read_text())
        state["kpi"]["current_success_rate"] = 0.4
        state["automation"]["auto_issue_generation"] = False
        # Simulate a very recent run (1 minute ago)
        from datetime import datetime, timedelta
        recent = datetime.now() - timedelta(minutes=1)
        state["automation"]["issue_factory_last_run_at"] = recent.strftime("%Y-%m-%d %H:%M:%S")
        de.decide(state)
        # Should remain False because interval has not elapsed
        assert state["automation"]["auto_issue_generation"] is False


# ---------------------------------------------------------------------------
# Worktree path resolution
# ---------------------------------------------------------------------------

class TestWorktreePathResolution:
    def test_placeholder_is_resolved(self, monkeypatch, tmp_path):
        de, _ = _load_module(monkeypatch, tmp_path)
        monkeypatch.setenv("DEVOS_HOME", str(tmp_path))
        state = json.loads(_.read_text())
        state["worktree"] = {"base_dir": "${DEVOS_HOME}/runtime/worktrees"}
        de.decide(state)
        assert "${DEVOS_HOME}" not in state["worktree"]["base_dir"]
        assert str(tmp_path) in state["worktree"]["base_dir"]

    def test_no_placeholder_unchanged(self, monkeypatch, tmp_path):
        de, _ = _load_module(monkeypatch, tmp_path)
        state = json.loads(_.read_text())
        state["worktree"] = {"base_dir": "/absolute/path/worktrees"}
        de.decide(state)
        assert state["worktree"]["base_dir"] == "/absolute/path/worktrees"
