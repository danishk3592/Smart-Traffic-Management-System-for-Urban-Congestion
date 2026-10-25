"""Check the local Windows STMS environment without changing files."""

from __future__ import annotations

import importlib
import importlib.metadata
import os
import re
import shutil
import subprocess
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

EXPECTED_SUMO_VERSION = "1.27.1"
SUPPORTED_PYTHON = (3, 14)
IMPORTS = {
    "gymnasium": "gymnasium",
    "numpy": "numpy",
    "psutil": "psutil",
    "PyYAML": "yaml",
    "stable-baselines3": "stable_baselines3",
    "sumolib": "sumolib",
    "torch": "torch",
    "traci": "traci",
    "pytest": "pytest",
    "pytest-cov": "pytest_cov",
    "pytest-timeout": "pytest_timeout",
    "ruff": "ruff",
}
DEPENDENCY_FILES = ("requirements.txt", "requirements-dev.txt")
REQUIRED_SCRIPTS = (
    "Ai/common/config.py",
    "Ai/common/run_episode.py",
    "Ai/rl/evaluate_ppo.py",
    "Ai/rl/train_ppo.py",
    "config/stms.yaml",
    "pyproject.toml",
    "requirements.lock.txt",
    "scripts/check_zombies.py",
    "scripts/make_scenarios.py",
    "scripts/setup_windows.ps1",
)
SUMO_BINARIES = ("sumo", "sumo-gui", "duarouter", "netconvert")


def report(ok: bool, message: str) -> bool:
    """Print one check result and return its success state."""
    print(f"[{'OK' if ok else 'FAIL'}] {message}")
    return ok


def check_sumo_config(repo_root: Path, config_file: Path) -> list[str]:
    """Return missing input and GUI configuration files referenced by SUMO."""
    tree = ET.parse(config_file)
    config_dir = config_file.parent
    missing: list[str] = []
    for element in tree.iter():
        if element.tag in {"net-file", "route-files", "additional-files", "gui-settings-file"}:
            value = element.get("value", "")
            for item in value.split(","):
                item = item.strip()
                if item and not (config_dir / item).is_file():
                    missing.append(str((config_dir / item).relative_to(repo_root)))
    return missing


def sumo_version(binary: str) -> str | None:
    """Read the installed SUMO version from a command-line binary."""
    path = shutil.which(binary)
    if path is None:
        return None
    completed = subprocess.run(
        [path, "--version"],
        check=False,
        capture_output=True,
        text=True,
        timeout=15,
    )
    match = re.search(
        r"\b(?:sumo|gui|duarouter|netconvert)\s+(\d+\.\d+\.\d+)\b",
        completed.stdout + completed.stderr,
        re.IGNORECASE,
    )
    return match.group(1) if completed.returncode == 0 and match else None


def expected_versions(repo_root: Path) -> dict[str, str]:
    """Read exact package pins from the runtime and development requirement files."""
    versions: dict[str, str] = {}
    for filename in DEPENDENCY_FILES:
        for raw_line in (repo_root / filename).read_text(encoding="utf-8").splitlines():
            line = raw_line.strip()
            if line and not line.startswith("#") and "==" in line:
                name, version = line.split("==", maxsplit=1)
                versions[name.strip().lower().replace("_", "-")] = version.strip()
    return versions


def main() -> int:
    """Run all environment checks and return a process exit code."""
    repo_root = Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(repo_root))
    failures = 0
    pins = expected_versions(repo_root)

    python_ok = sys.version_info[:2] == SUPPORTED_PYTHON
    if not report(python_ok, f"Python {sys.version.split()[0]} at {sys.executable} (setup target: 3.14.x)"):
        failures += 1

    for distribution, module_name in IMPORTS.items():
        try:
            version = importlib.metadata.version(distribution)
            importlib.import_module(module_name)
            normalized = distribution.lower().replace("_", "-")
            expected = pins.get(normalized)
            version_matches = expected is None or version.split("+", maxsplit=1)[0] == expected
            if not report(version_matches, f"{distribution} {version} imports" + (f" (pinned {expected})" if expected else "")):
                failures += 1
        except (importlib.metadata.PackageNotFoundError, ImportError, OSError) as error:
            failures += 1
            report(False, f"{distribution} is missing or cannot import: {error}")

    try:
        import torch

        cuda_status = "available" if torch.cuda.is_available() else "not available (CPU setup is supported)"
        print(f"[INFO] PyTorch {torch.__version__}; CUDA {cuda_status}")
    except (ImportError, OSError):
        pass

    sumo_home = os.environ.get("SUMO_HOME")
    if sumo_home:
        tools_dir = Path(sumo_home) / "tools"
        if not report(tools_dir.is_dir(), f"SUMO_HOME={sumo_home}; tools directory {'found' if tools_dir.is_dir() else 'missing'}"):
            failures += 1
    else:
        failures += 1
        report(False, "SUMO_HOME is not set; point it to the SUMO installation directory")

    for binary in SUMO_BINARIES:
        version = sumo_version(binary)
        valid = version == EXPECTED_SUMO_VERSION
        if not report(valid, f"{binary} version {version or 'not found'} (expected {EXPECTED_SUMO_VERSION})"):
            failures += 1

    try:
        from Ai.common.config import load_config

        config = load_config(repo_root / "config" / "stms.yaml")
        sumocfg = repo_root / config["sumo"]["config"]
        config_ok = sumocfg.is_file()
        if not report(config_ok, f"Project config loads; SUMO config {'found' if config_ok else 'missing'}: {sumocfg}"):
            failures += 1
        if config_ok:
            missing_refs = check_sumo_config(repo_root, sumocfg)
            refs_ok = not missing_refs
            if not report(refs_ok, "SUMO input and GUI configuration references exist" if refs_ok else f"Missing SUMO references: {', '.join(missing_refs)}"):
                failures += 1
    except (KeyError, OSError, ET.ParseError, TypeError, ValueError) as error:
        failures += 1
        report(False, f"Project/SUMO configuration check failed: {error}")

    missing_scripts = [
        relative_path
        for relative_path in REQUIRED_SCRIPTS
        if not (repo_root / relative_path).is_file()
    ]
    scripts_ok = not missing_scripts
    if not report(scripts_ok, "Required project scripts and configuration files exist" if scripts_ok else f"Missing project files: {', '.join(missing_scripts)}"):
        failures += 1

    if shutil.which("nvidia-smi"):
        print("[INFO] NVIDIA utility detected; GPU acceleration remains optional.")
    else:
        print("[INFO] nvidia-smi not found; CPU setup remains supported.")

    print(f"Environment check: {'PASS' if failures == 0 else f'FAIL ({failures} issue(s))'}")
    return 0 if failures == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
