"""Keep the host awake while a long-running project command is active."""

from __future__ import annotations

import ctypes
import os
import shutil
import subprocess
import sys
import time
from collections.abc import Iterator, Sequence
from contextlib import contextmanager


@contextmanager
def keep_awake(reason: str = "STMS long-running job") -> Iterator[None]:
    """Request that the OS not suspend the system for this context's lifetime."""
    if os.name == "nt":
        kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
        set_execution_state = kernel32.SetThreadExecutionState
        set_execution_state.argtypes = [ctypes.c_uint]
        set_execution_state.restype = ctypes.c_uint
        continuous = 0x80000000
        system_required = 0x00000001
        if not set_execution_state(continuous | system_required):
            raise ctypes.WinError(ctypes.get_last_error())
        try:
            yield
        finally:
            set_execution_state(continuous)
        return

    inhibitor = shutil.which("systemd-inhibit")
    if inhibitor is None:
        yield
        return

    command = [
        inhibitor,
        "--what=sleep",
        "--mode=block",
        f"--why={reason}",
        sys.executable,
        "-c",
        "import time; time.sleep(86400)",
    ]
    process = subprocess.Popen(
        command,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    try:
        time.sleep(0.1)
        if process.poll() is not None:
            raise RuntimeError("systemd-inhibit exited before acquiring the sleep lock")
        yield
    finally:
        if process.poll() is None:
            process.terminate()
            process.wait(timeout=5)


def run_with_keep_awake(command: Sequence[str]) -> int:
    """Run one argv command while requesting that the OS remain awake."""
    if not command:
        raise ValueError("a command is required after --")
    with keep_awake():
        return subprocess.run(command, check=False).returncode


def main(argv: Sequence[str] | None = None) -> int:
    """CLI wrapper for running a command while holding the stay-awake request."""
    arguments = list(sys.argv[1:] if argv is None else argv)
    if "--" not in arguments:
        raise SystemExit("usage: python -m scripts.keep_awake -- <command> [args ...]")
    separator = arguments.index("--")
    command = arguments[separator + 1 :]
    return run_with_keep_awake(command)


if __name__ == "__main__":
    raise SystemExit(main())
