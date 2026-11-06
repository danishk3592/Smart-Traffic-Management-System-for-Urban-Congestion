from __future__ import annotations

import csv
import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]

M1_VALUE_COLUMNS = (
    "aggregation", "scenario", "metric", "scope", "trip_basis", "controller",
    "mean", "std", "ci95_low", "ci95_high", "n_seeds", "n_trips_basis",
    "completion_rate_mean", "improvement_vs_fixed_pct", "improvement_vs_rule_pct",
    "target_met",
)


def _markdown_table_rows(section: str, heading: str) -> list[dict[str, str]]:
    """Read one pipe table by its immediately preceding Markdown heading."""
    lines = section.splitlines()
    try:
        heading_index = lines.index(heading)
    except ValueError:
        return []
    table_lines = [line.strip() for line in lines[heading_index + 1:] if line.strip()]
    if len(table_lines) < 3 or not table_lines[0].startswith("|"):
        return []

    def cells(line: str) -> list[str]:
        return [cell.strip() for cell in line.strip().strip("|").split("|")]

    headers = cells(table_lines[0])
    rows: list[dict[str, str]] = []
    for line in table_lines[2:]:
        if not line.startswith("|"):
            break
        values = cells(line)
        if len(values) != len(headers):
            raise AssertionError(f"Malformed Markdown row under {heading}: {line}")
        rows.append(dict(zip(headers, values, strict=True)))
    return rows


def test_m2_results_coverage_line_matches_final_summary() -> None:
    summary_path = ROOT / "results" / "summary" / "summary.csv"
    if not summary_path.is_file():
        return  # Final-seed artifacts are created only by the T4.9 acceptance run.
    with summary_path.open(encoding="utf-8", newline="") as stream:
        rows = [row for row in csv.DictReader(stream) if row.get("seed_set") == "final"]
    assert len(rows) == 1
    summary = rows[0]
    report = (ROOT / "docs" / "results.md").read_text(encoding="utf-8")
    match = re.search(r"^AI coverage: (\d+)/(\d+) \((full|partial|none)\)$", report, re.MULTILINE)
    assert match is not None
    assert match.groups() == (
        summary["n_tls_ai"], summary["n_tls_controlled"], summary["ai_coverage"],
    )
    if summary["ai_coverage"] != "full":
        assert "full network-wide AI control" not in report.lower()


def test_m1_report_travel_time_rows_match_final_comparison_csv() -> None:
    """Check every published M1 travel-time value against its exact source row."""
    comparison_path = ROOT / "results" / "summary" / "comparison.csv"
    if not comparison_path.is_file():
        pytest.skip("Final M1 comparison does not exist until T3.2 completes")
    with comparison_path.open(encoding="utf-8", newline="") as stream:
        source_rows = [
            row for row in csv.DictReader(stream)
            if row.get("milestone") == "M1"
            and row.get("seed_set") == "final"
            and row.get("metric") == "travel_time"
            and row.get("aggregation") in {"scenario", "headline", "primary", "low", "pooled"}
        ]
    if not source_rows:
        pytest.skip("Final M1 comparison rows do not exist until T3.2 completes")

    report = (ROOT / "docs" / "results.md").read_text(encoding="utf-8")
    section_match = re.search(
        r"^## Part 1 — M1 single-junction milestone(?P<section>.*?)(?=^## Part 2)",
        report,
        re.MULTILINE | re.DOTALL,
    )
    assert section_match is not None, "M1 results section is missing"
    section = section_match.group("section")
    assert "Pending T3.2" not in section
    assert "milestone, not the final result" in section.lower()
    assert "provisional until P1" in section

    table_rows = _markdown_table_rows(section, "### CSV-backed travel-time values")
    assert table_rows, "M1 CSV-backed travel-time table is missing"
    assert tuple(table_rows[0]) == M1_VALUE_COLUMNS
    actual_keys = [tuple(row[column] for column in M1_VALUE_COLUMNS[:6]) for row in table_rows]
    source_by_key = {
        tuple(row[column] for column in M1_VALUE_COLUMNS[:6]): row
        for row in source_rows
    }
    assert len(actual_keys) == len(set(actual_keys)), "M1 report contains duplicate source rows"
    assert set(actual_keys) == set(source_by_key), "M1 report omits or adds CSV travel-time rows"

    numeric_columns = (
        "mean", "std", "ci95_low", "ci95_high", "n_seeds", "n_trips_basis",
        "completion_rate_mean", "improvement_vs_fixed_pct", "improvement_vs_rule_pct",
    )
    for report_row in table_rows:
        key = tuple(report_row[column] for column in M1_VALUE_COLUMNS[:6])
        source = source_by_key[key]
        for column in numeric_columns:
            source_value = source.get(column, "")
            rendered = report_row[column]
            if source_value in {"", None}:
                assert rendered in {"", "—"}, f"Unexpected {column} for {key}: {rendered}"
            elif column in {"n_seeds", "n_trips_basis"}:
                assert rendered == str(int(float(source_value))), f"Mismatched {column} for {key}"
            else:
                assert rendered == f"{float(source_value):.3f}", f"Mismatched {column} for {key}"
        assert report_row["target_met"].lower() == source.get("target_met", "").lower()

    # Every scenario, including low, has common-trip and censored rows side by side.
    trip_basis_by_cell: dict[tuple[str, str, str, str], set[str]] = {}
    for row in table_rows:
        cell = (row["aggregation"], row["scenario"], row["scope"], row["controller"])
        trip_basis_by_cell.setdefault(cell, set()).add(row["trip_basis"])
    assert trip_basis_by_cell
    assert all(bases == {"common", "all"} for bases in trip_basis_by_cell.values())
    assert any(row["aggregation"] == "low" for row in table_rows)
    assert any(row["aggregation"] == "headline" for row in table_rows)
