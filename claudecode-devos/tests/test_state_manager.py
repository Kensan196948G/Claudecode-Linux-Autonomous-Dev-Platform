"""Tests for ops/state_manager.py — atomic state read/write logic."""
import importlib
import json
import sys
from pathlib import Path

import pytest

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

MINIMAL_STATE = {
    "system": {"status": "idle"},
    "goal": {"title": "test"},
    "kpi": {"success_rate_target": 0.9, "current_success_rate": 0.0},
    "automation": {"auto_issue_generation": False},
    "ci": {"repair_attempt_count": 0, "enabled": True},
    "resources": {},
    "decision": {},
    "risk": {},
}


def _load_module(monkeypatch, tmp_path):
    """Load state_manager with env vars pointing to tmp_path."""
    state_file = tmp_path / "config" / "state.json"
    lock_dir = tmp_path / "runtime" / "tmp"
    state_file.parent.mkdir(parents=True)
    lock_dir.mkdir(parents=True)
    state_file.write_text(json.dumps(MINIMAL_STATE), encoding="utf-8")

    monkeypatch.setenv("DEVOS_HOME", str(tmp_path))
    monkeypatch.setenv("DEVOS_STATE_FILE", str(state_file))
    monkeypatch.setenv("DEVOS_LOCK_DIR", str(lock_dir))

    # Reload module so module-level constants pick up the new env vars
    if "ops.state_manager" in sys.modules:
        del sys.modules["ops.state_manager"]
    sys.path.insert(0, str(Path(__file__).parent.parent))
    import ops.state_manager as sm
    importlib.reload(sm)
    return sm, state_file


# ---------------------------------------------------------------------------
# coerce_value
# ---------------------------------------------------------------------------

class TestCoerceValue:
    def test_true(self, monkeypatch, tmp_path):
        sm, _ = _load_module(monkeypatch, tmp_path)
        assert sm.coerce_value("true") is True

    def test_false(self, monkeypatch, tmp_path):
        sm, _ = _load_module(monkeypatch, tmp_path)
        assert sm.coerce_value("false") is False

    def test_null(self, monkeypatch, tmp_path):
        sm, _ = _load_module(monkeypatch, tmp_path)
        assert sm.coerce_value("null") is None

    def test_int(self, monkeypatch, tmp_path):
        sm, _ = _load_module(monkeypatch, tmp_path)
        assert sm.coerce_value("42") == 42

    def test_float(self, monkeypatch, tmp_path):
        sm, _ = _load_module(monkeypatch, tmp_path)
        assert sm.coerce_value("3.14") == pytest.approx(3.14)

    def test_string(self, monkeypatch, tmp_path):
        sm, _ = _load_module(monkeypatch, tmp_path)
        assert sm.coerce_value("hello") == "hello"


# ---------------------------------------------------------------------------
# load_state / save_state
# ---------------------------------------------------------------------------

class TestLoadSaveState:
    def test_load_minimal_state(self, monkeypatch, tmp_path):
        sm, state_file = _load_module(monkeypatch, tmp_path)
        state = sm.load_state()
        assert state["system"]["status"] == "idle"

    def test_save_and_reload(self, monkeypatch, tmp_path):
        sm, state_file = _load_module(monkeypatch, tmp_path)
        state = sm.load_state()
        state["system"]["status"] = "running"
        sm.save_state(state)
        reloaded = sm.load_state()
        assert reloaded["system"]["status"] == "running"

    def test_save_uses_atomic_replace(self, monkeypatch, tmp_path):
        """save_state must write via NamedTemporaryFile then os.replace."""
        sm, state_file = _load_module(monkeypatch, tmp_path)
        state = sm.load_state()
        sm.save_state(state)
        # No temp files should remain in the directory
        tmp_files = list(state_file.parent.glob("tmp*"))
        assert tmp_files == [], f"Leftover temp files: {tmp_files}"

    def test_file_not_found_raises(self, monkeypatch, tmp_path):
        sm, state_file = _load_module(monkeypatch, tmp_path)
        state_file.unlink()
        with pytest.raises(FileNotFoundError):
            sm.load_state()


# ---------------------------------------------------------------------------
# update_path / get_path
# ---------------------------------------------------------------------------

class TestPathOperations:
    def setup_method(self):
        self.state = {"a": {"b": {"c": 1}}}

    def test_get_nested(self, monkeypatch, tmp_path):
        sm, _ = _load_module(monkeypatch, tmp_path)
        assert sm.get_path(self.state, "a.b.c") == 1

    def test_update_nested(self, monkeypatch, tmp_path):
        sm, _ = _load_module(monkeypatch, tmp_path)
        sm.update_path(self.state, "a.b.c", 99)
        assert self.state["a"]["b"]["c"] == 99

    def test_update_creates_missing_keys(self, monkeypatch, tmp_path):
        sm, _ = _load_module(monkeypatch, tmp_path)
        sm.update_path(self.state, "x.y.z", "new")
        assert self.state["x"]["y"]["z"] == "new"


# ---------------------------------------------------------------------------
# with_lock (integration)
# ---------------------------------------------------------------------------

class TestWithLock:
    def test_with_lock_reads_and_saves(self, monkeypatch, tmp_path):
        sm, _ = _load_module(monkeypatch, tmp_path)

        def mutate(state):
            state["system"]["status"] = "active"

        sm.with_lock(mutate)
        assert sm.load_state()["system"]["status"] == "active"

    def test_with_lock_returns_callback_result(self, monkeypatch, tmp_path):
        sm, _ = _load_module(monkeypatch, tmp_path)

        result = sm.with_lock(lambda state: "ok")
        assert result == "ok"
