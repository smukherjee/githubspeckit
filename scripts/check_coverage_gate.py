#!/usr/bin/env python3
"""Coverage Gate Script (Placeholder Phase 3 Extension)

Purpose:
  Enforce Constitution v1.5.1 coverage thresholds and critical path 100% rules.
  This placeholder adds awareness of upcoming persistence layer paths so that
  once implemented, they are immediately enforced without retrofitting.

Rules Implemented (current state limited by absence of actual code paths):
  - Overall coverage must be >= 85%
  - Domain (src/domain) must be >= 90%
  - Critical persistence paths (adapters/persistence, alembic/versions) are
    registered but ignored until Phase 3 tasks land (fail-open with warning).

Phase 3 TODO (IMPL-DB-13 follow-up):
  - Switch fail-open placeholders for persistence to hard fail (100%) once
    at least one Python file exists in those directories.
  - Emit machine-readable JSON summary for CI artifact collection.

Exit Codes:
  0 pass
  2 soft warning (placeholder paths missing) – treated as success now
  3 failure (threshold or critical path miss)
"""
from __future__ import annotations

import json
import os
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

# Thresholds (align with constitution v1.5.1)
OVERALL_MIN = 0.85
DOMAIN_MIN = 0.90
CRITICAL_PATHS = [
    Path("src/domain"),
    Path("adapters/persistence"),  # Phase 3
    Path("alembic/versions"),      # Phase 3
]

@dataclass
class PathCoverage:
    path: Path
    covered: int
    total: int

    @property
    def pct(self) -> float:
        return 0.0 if self.total == 0 else self.covered / self.total


def _load_coverage_json(path: Path) -> dict:
    try:
        with path.open("r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        print("ERROR: coverage JSON file not found. Run tests with coverage xml/json first.", file=sys.stderr)
        sys.exit(3)


def _gather_file_coverages(report: dict) -> dict[str, PathCoverage]:
    files = {}
    for file_rec in report.get("files", {}).values():
        filename = Path(file_rec["filename"]) if isinstance(file_rec, dict) else None
        if not filename:
            continue
        summary = file_rec.get("summary", {})
        files[str(filename)] = PathCoverage(
            path=filename,
            covered=summary.get("covered_lines", 0),
            total=summary.get("num_statements", 0),
        )
    return files


def _aggregate_namespace(files: Iterable[PathCoverage], namespace: Path) -> PathCoverage:
    total = 0
    covered = 0
    for pc in files:
        try:
            rel = pc.path.relative_to(namespace)
        except ValueError:
            continue
        total += pc.total
        covered += pc.covered
    return PathCoverage(namespace, covered, total)


def main() -> None:
    coverage_file = Path(os.environ.get("COVERAGE_JSON", "coverage.json"))
    report = _load_coverage_json(coverage_file)
    file_cov_map = _gather_file_coverages(report)

    overall_summary = report.get("totals", {})
    overall_pct = overall_summary.get("percent_covered", 0.0) / 100.0

    domain_cov = _aggregate_namespace(file_cov_map.values(), Path("src/domain"))

    critical_results: list[dict] = []
    hard_fail = False
    soft_warn = False

    for path in CRITICAL_PATHS:
        cov = _aggregate_namespace(file_cov_map.values(), path)
        if path.name in {"persistence", "versions"} and cov.total == 0:
            # Phase 3 not yet present – soft warn only
            soft_warn = True
            critical_results.append({
                "path": str(path),
                "status": "DEFERRED",
                "pct": None,
                "required": 1.0,
                "reason": "No files yet; Phase 3 pending (fail-open)"
            })
            continue
        pct = cov.pct
        ok = pct >= 1.0
        if not ok:
            hard_fail = True
        critical_results.append({
            "path": str(path),
            "status": "PASS" if ok else "FAIL",
            "pct": round(pct, 4),
            "required": 1.0,
        })

    result = {
        "overall_pct": round(overall_pct, 4),
        "overall_min": OVERALL_MIN,
        "domain_pct": round(domain_cov.pct, 4),
        "domain_min": DOMAIN_MIN,
        "critical_paths": critical_results,
    }

    print(json.dumps(result, indent=2))

    if overall_pct < OVERALL_MIN or domain_cov.pct < DOMAIN_MIN or hard_fail:
        sys.exit(3)
    if soft_warn:
        sys.exit(2)
    sys.exit(0)

if __name__ == "__main__":  # pragma: no cover
    main()
