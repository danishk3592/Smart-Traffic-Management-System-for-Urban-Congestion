"""Report whether SUMO processes are still running."""

from __future__ import annotations

from pathlib import Path

import psutil


def find_sumo_processes() -> list[tuple[int, str]]:
    """Return running SUMO and SUMO-GUI processes as (pid, executable name)."""
    processes: list[tuple[int, str]] = []
    for process in psutil.process_iter(["pid", "name"]):
        try:
            name = process.info.get("name") or ""
            if Path(name).stem.casefold() in {"sumo", "sumo-gui"}:
                processes.append((int(process.info["pid"]), name))
        except (psutil.NoSuchProcess, psutil.AccessDenied, TypeError, ValueError):
            continue
    return processes


def main() -> int:
    """Print a concise process check and return a shell exit status."""
    processes = find_sumo_processes()
    if processes:
        for pid, name in processes:
            print(f"SUMO process remains: pid={pid} name={name}")
        return 1

    print("No running sumo or sumo-gui processes detected.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())