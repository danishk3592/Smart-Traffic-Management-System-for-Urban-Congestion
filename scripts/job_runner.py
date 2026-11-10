"""Launch, track and resume long-running project commands without a shell."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
import uuid
from collections.abc import Sequence
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from scripts.keep_awake import keep_awake

ROOT = Path(__file__).resolve().parents[1]


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def _write_record(path: Path, record: dict[str, Any]) -> None:
    """Atomically write a job record so readers never observe partial JSON."""
    temporary = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    temporary.write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8")
    os.replace(temporary, path)


def _monitor(record_path: Path) -> int:
    """Run a detached child, update its record, and hold the OS awake."""
    record = json.loads(record_path.read_text(encoding="utf-8"))
    log_path = Path(record["log_path"])
    log_path.parent.mkdir(parents=True, exist_ok=True)
    record.update(state="starting", monitor_pid=os.getpid(), updated_utc=_utc_now())
    _write_record(record_path, record)
    try:
        with keep_awake(f"STMS job {record['job_id']}"), log_path.open(
            "a", encoding="utf-8", buffering=1
        ) as log:
            flags = 0
            if os.name == "nt":
                flags = subprocess.CREATE_NO_WINDOW | subprocess.CREATE_NEW_PROCESS_GROUP
            process = subprocess.Popen(
                record["command"],
                cwd=ROOT,
                stdin=subprocess.DEVNULL,
                stdout=log,
                stderr=subprocess.STDOUT,
                creationflags=flags,
                start_new_session=os.name != "nt",
            )
            record.update(
                state="running",
                pid=process.pid,
                started_utc=record.get("started_utc", _utc_now()),
                updated_utc=_utc_now(),
            )
            _write_record(record_path, record)
            while process.poll() is None:
                time.sleep(30)
                record["updated_utc"] = _utc_now()
                _write_record(record_path, record)
            record["return_code"] = process.returncode
            record["state"] = "finished" if process.returncode == 0 else "failed"
    except (OSError, RuntimeError, ValueError, KeyError, TypeError, subprocess.SubprocessError) as exc:
        record.update(state="failed", error=f"{type(exc).__name__}: {exc}")
        return_code = 1
    else:
        return_code = int(record["return_code"] != 0)
    record["updated_utc"] = _utc_now()
    _write_record(record_path, record)
    return return_code


def _launch(options: argparse.Namespace, command: Sequence[str]) -> int:
    """Create a job record and start its detached monitor process."""
    if not command:
        raise ValueError("a command is required after --")
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    job_id = f"{timestamp}_{uuid.uuid4().hex[:8]}"
    job_dir = ROOT / "results" / "jobs"
    job_dir.mkdir(parents=True, exist_ok=True)
    record_path = job_dir / f"{job_id}.json"
    out_dir = Path(options.out_dir)
    log_path = Path(options.log)
    if not out_dir.is_absolute():
        out_dir = ROOT / out_dir
    if not log_path.is_absolute():
        log_path = ROOT / log_path
    log_path.parent.mkdir(parents=True, exist_ok=True)
    record: dict[str, Any] = {
        "job_id": job_id,
        "command": list(command),
        "resume_command": options.resume_command,
        "pid": None,
        "started_utc": _utc_now(),
        "updated_utc": _utc_now(),
        "log_path": str(log_path.resolve()),
        "out_dir": str(out_dir.resolve()),
        "state": "starting",
    }
    _write_record(record_path, record)
    monitor_command = [sys.executable, "-m", "scripts.job_runner", "--monitor", str(record_path)]
    flags = 0
    if os.name == "nt":
        flags = subprocess.CREATE_NO_WINDOW | subprocess.CREATE_NEW_PROCESS_GROUP | subprocess.DETACHED_PROCESS
    monitor = subprocess.Popen(
        monitor_command,
        cwd=ROOT,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        creationflags=flags,
        start_new_session=os.name != "nt",
    )
    print(json.dumps({"job_id": job_id, "pid": monitor.pid, "record": str(record_path)}))
    return 0


def main(argv: Sequence[str] | None = None) -> int:
    """Parse launcher or monitor mode and return the real child status."""
    arguments = list(sys.argv[1:] if argv is None else argv)
    if arguments and arguments[0] == "--monitor":
        if len(arguments) != 2:
            raise SystemExit("--monitor requires exactly one job record path")
        return _monitor(Path(arguments[1]))

    if "--" not in arguments:
        raise SystemExit(
            "usage: python -m scripts.job_runner --out-dir DIR --log FILE "
            "--resume-command COMMAND -- <command> [args ...]"
        )
    separator = arguments.index("--")
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", required=True)
    parser.add_argument("--log", required=True)
    parser.add_argument("--resume-command", required=True)
    options = parser.parse_args(arguments[:separator])
    return _launch(options, arguments[separator + 1 :])


if __name__ == "__main__":
    raise SystemExit(main())
