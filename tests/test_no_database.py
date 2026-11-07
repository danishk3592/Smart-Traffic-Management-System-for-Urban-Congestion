"""Keep the local dashboard file-only without a database or web backend."""

import subprocess
from pathlib import Path

FORBIDDEN = (
    "sqlite3",
    "sqlalchemy",
    "psycopg2",
    "supabase",
    "alembic",
    "fastapi",
    "uvicorn",
    "websockets",
)


def test_dashboard_sources_and_requirements_have_no_backend_dependencies() -> None:
    tracked = subprocess.run(
        ["git", "ls-files"], check=True, capture_output=True, text=True
    ).stdout.splitlines()
    candidates = {
        Path(name)
        for name in tracked
        if Path(name).suffix.lower() in {".py", ".dart", ".yaml", ".yml", ".toml", ".txt"}
    }
    candidates.update(Path("dashboard_flutter").rglob("*.dart"))
    candidates.update(Path("dashboard_flutter").rglob("*.yaml"))
    violations = []
    for path in candidates:
        if not path.is_file() or path.name == "test_no_database.py":
            continue
        content = path.read_text(encoding="utf-8", errors="ignore").lower()
        if any(name in content for name in FORBIDDEN):
            violations.append(str(path))
    assert not violations, f"Backend/database dependencies referenced in: {violations}"


def test_tracked_database_files_and_dashboard_traci_imports_are_absent() -> None:
    tracked = subprocess.run(
        ["git", "ls-files"], check=True, capture_output=True, text=True
    ).stdout.splitlines()
    assert not [name for name in tracked if name.lower().endswith((".db", ".sqlite", ".sqlite3"))]
    dashboard = Path("dashboard_flutter")
    assert not [
        str(path)
        for path in dashboard.rglob("*.dart")
        if "traci" in path.read_text(encoding="utf-8").lower()
    ]
