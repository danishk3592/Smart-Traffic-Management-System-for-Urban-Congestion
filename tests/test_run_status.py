"""Status publication is atomic and records terminal outcomes."""

import json
from pathlib import Path

from Ai.common import run_episode


def test_explicit_run_folder_is_the_artifact_run_id(tmp_path) -> None:
    destination = tmp_path / "20261106-150000_rule_net_medium_s8000"
    assert run_episode._output_run_id("generated-id", destination) == destination.name


def test_status_updates_atomically_with_failure_details(tmp_path) -> None:
    status_path = tmp_path / "status.json"
    run_episode._STATUS_PATH.set(status_path)
    try:
        run_episode._write_status(status_path, {
            "schema_version": 1,
            "run_id": "fixture",
            "state": "running",
            "family": "single",
            "controller": "fixed",
            "scenario": "medium",
            "seed": 8000,
            "sim_time": 0,
            "max_sim_s": 10,
            "n_tls_controlled": 1,
            "started_utc": "2026-11-02T00:00:00+00:00",
            "updated_utc": "",
            "error": None,
        })
        run_episode._set_status("failed", sim_time=5, error="RuntimeError: fixture failure")
        payload = json.loads(status_path.read_text(encoding="utf-8"))
        assert payload["state"] == "failed"
        assert payload["sim_time"] == 5
        assert payload["error"] == "RuntimeError: fixture failure"
        assert payload["updated_utc"].endswith("+00:00")
        assert not status_path.with_suffix(".json.tmp").exists()
    finally:
        run_episode._STATUS_PATH.set(None)


def test_status_writer_retries_transient_replace_denial(monkeypatch, tmp_path) -> None:
    status_path = tmp_path / "status.json"
    original_replace = Path.replace
    attempts = 0

    def fail_twice_then_replace(path: Path, target: Path) -> Path:
        nonlocal attempts
        attempts += 1
        if attempts < 3:
            raise PermissionError("transient Windows sharing violation")
        return original_replace(path, target)

    monkeypatch.setattr(Path, "replace", fail_twice_then_replace)
    run_episode._write_status(status_path, _payload())
    assert attempts == 3
    assert json.loads(status_path.read_text(encoding="utf-8"))["run_id"] == "fixture"
    assert not status_path.with_suffix(".json.tmp").exists()


def _payload() -> dict[str, object]:
    return {
        "schema_version": 1,
        "run_id": "fixture",
        "state": "running",
        "family": "single",
        "controller": "fixed",
        "scenario": "medium",
        "seed": 8000,
        "sim_time": 0,
        "max_sim_s": 10,
        "n_tls_controlled": 1,
        "started_utc": "2026-11-02T00:00:00+00:00",
        "updated_utc": "",
        "error": None,
    }


def test_runner_wrapper_marks_normal_completion(monkeypatch, tmp_path) -> None:
    status_path = tmp_path / "status.json"

    def runner(*args, **kwargs):
        run_episode._STATUS_PATH.set(status_path)
        run_episode._write_status(status_path, _payload())
        return {"sim_end_time": 10}

    monkeypatch.setattr(run_episode, "_run_episode", runner)
    result = run_episode.run_episode(object(), "medium", 8000)
    payload = json.loads(status_path.read_text(encoding="utf-8"))
    assert result["sim_end_time"] == 10
    assert payload["state"] == "finished"
    assert payload["sim_time"] == 10


def test_runner_wrapper_marks_exceptions_failed(monkeypatch, tmp_path) -> None:
    status_path = tmp_path / "status.json"

    def runner(*args, **kwargs):
        run_episode._STATUS_PATH.set(status_path)
        run_episode._write_status(status_path, _payload())
        raise RuntimeError("episode failed")

    monkeypatch.setattr(run_episode, "_run_episode", runner)
    try:
        run_episode.run_episode(object(), "medium", 8000)
    except RuntimeError as exc:
        assert str(exc) == "episode failed"
    else:
        raise AssertionError("runner exception was not propagated")
    payload = json.loads(status_path.read_text(encoding="utf-8"))
    assert payload["state"] == "failed"
    assert payload["error"] == "RuntimeError: episode failed"
